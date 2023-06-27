# -*- coding: utf-8 -*-
"""Attribute module for data acquisition and inter-process data synchronization


"""
from __future__ import annotations

from abc import ABC, abstractmethod
import ctypes
import multiprocessing as mp
import numpy as np
from typing import Any, Dict, Iterable, Iterator, List, Tuple, Union

from vxpy.definitions import *
from vxpy import config
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.process as vxprocess
import vxpy.core.routine as vxroutine

log = vxlogger.getLogger(__name__)


def init(attrs: Union[Dict[str, Attribute], None]) -> None:
    """Calls the build function of all specified attributes"""

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')

    if attrs is not None:
        Attribute.all.update(attrs)

    for attr in Attribute.all.values():
        attr.build()


def read_attribute(attr_name: str, *args, **kwargs) -> Union[Tuple[np.ndarray, np.ndarray, Iterable], None]:
    """Convenience method for calling an attribute's read function via its name"""
    if attr_name not in Attribute.all:
        return

    return Attribute.all[attr_name].read(*args, **kwargs)


def write_attribute(attr_name: str, *args, **kwargs) -> None:
    """Convenience method for calling an attribute's write function via its name"""
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].write(*args, **kwargs)


def match_to_record_attributes(attr_name: str) -> Tuple[bool, bool, Dict]:
    """Method matches a given attribute name to a list of attribute name templates to determine whether
     the attribute should be included for recording to file"""
    attribute_filters = config.REC_ATTRIBUTES

    # matched = False
    for filt_string, record_ops in attribute_filters.items():

        # Check if filter is negated
        neg = False
        if filt_string.startswith('~'):
            filt_string = filt_string[1:]
            neg = True

        # Check if substring is matched
        match = False
        if '*' not in filt_string:
            if filt_string == attr_name:
                match = True
        elif filt_string.startswith('*') and filt_string.endswith('*'):
            if filt_string in attr_name:
                match = True
        elif filt_string.startswith('*'):
            if attr_name.endswith(filt_string.strip('*')):
                match = True
        elif filt_string.endswith('*'):
            if attr_name.startswith(filt_string.strip('*')):
                match = True

        # Return if match was found
        if match:
            if neg:
                return True, False, {}
            return True, True, record_ops

    #     # Update
    #     matched = matched or match
    #
    # No matches
    return True, False, {}


def write_to_file(instance: Union[vxprocess.AbstractProcess, vxroutine.Routine], attr_name: str) -> None:
    if isinstance(instance, vxprocess.AbstractProcess):
        process_name = instance.name
    elif isinstance(instance, vxroutine.Routine):
        process_name = instance.process_name
    else:
        log.error(f'Could not find corresponding process for attribute {attr_name}. Will not save attribute.')
        return

    # If provided process name is not listed in attribute's to-file dictionary, create the associated list
    if process_name not in Attribute.to_file:
        Attribute.to_file[process_name] = []

    # If attribute does not exist, it cannot be added to the to-file list
    if attr_name not in Attribute.all:
        msg = 'Attribute does not exist.'
    else:
        # Check attribute name against templates
        found, include, record_ops = match_to_record_attributes(attr_name)

        # If attribute name is included by template list, append to the to_file list
        if include:
            log.info(f'Set attribute "{attr_name}" to be written to file. ')
            Attribute.to_file[process_name].append((Attribute.all[attr_name], record_ops))
            return

        # If not included: is it actively exluded by list or not in template list at all
        if found:
            msg = 'Excluded by template list.'
        else:
            msg = 'Not in template list.'

    log.warning(f'Attribute "{attr_name}" is not written to file. {msg}')


def get_attribute_names() -> List[str]:
    """Method returns a list of all attribute names"""
    return [n for n in Attribute.all.keys()]


def get_attribute_list() -> List[Tuple[str, Attribute]]:
    """Method returns a list of tuples containing (attribute name, attribute object)"""
    return [(k, v) for k, v in Attribute.all.items()]


def get_attribute(attr_name: str) -> Union[Attribute, None]:
    """Method returns an attribute with the given name or None if attribute does not exist
    """
    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name]


def get_permanent_attributes(process_name: str = None) -> List[Tuple[Attribute, Dict]]:
    """Method returns a list of all attributes that are marked to be saved to file
    """
    if process_name is None:
        process_name = vxipc.LocalProcess.name

    if process_name not in Attribute.to_file:
        return []

    return Attribute.to_file[process_name]


def get_permanent_data(process_name: str = None) -> Iterator[Tuple[Attribute, Dict]]:
    """Returns all newly added attribute data to be written to file
    for the specified process.

    :param process_name: Name of process for which to return data
    :type process_name: str, optional

    :return A
    :rtype Iterator[Tuple[str, Any]
    """
    for attribute, record_ops in get_permanent_attributes(process_name):
        if attribute.has_new_entry():
            # Yield attribute
            yield attribute, record_ops

            # Reset "new" flag
            attribute.set_new(False)


class Attribute(ABC):
    """Attribute class at the core of vxPy's data management structure.

    Attributes act as ring buffers and are shared and synchronized
    across all different modules.
    They are written to by one particular module (producer module)
    and can be read by all modules (consumer modules, including producer).

    :param name: Name of the attribute. Must be unique in the
        current instance of vxPy
    :type name: str
    :param length: Length of the ring buffer
    :type length: int, optional
    """

    all: Dict[str, Attribute] = {}
    to_file: Dict[str, List[Tuple[Attribute, Dict]]] = {}
    _instance: ArrayAttribute = None

    def __init__(self, name: str, length: int = None):
        assert name not in self.all, f'Duplicate attribute {name}'
        self.name = name
        Attribute.all[name] = self

        self.shape: tuple = ()
        self._length = length
        self._index = mp.Value(ctypes.c_uint64)
        self._last_time = np.inf
        self._new_data_flag: mp.Value = mp.Value(ctypes.c_bool, False)

        self._times: np.ndarray = np.array([])
        self._indices: np.ndarray = np.array([])

    def __repr__(self):
        return f'{self.__class__.__name__}(\'{self.name}\')'

    @property
    def length(self):
        return self._length

    def _make_times(self):
        """Generate the shared list of times corresponding to individual datapoints in the buffer"""
        # self._times = vxipc.Manager.list([None] * self.length)
        self._times_raw = mp.Array(ctypes.c_double, self.length)

    def _make_indices(self):
        """Generate the shared list of times corresponding to individual datapoints in the buffer"""
        # self._indices = vxipc.Manager.list([None] * self.length)
        self._indices_raw = mp.Array(ctypes.c_int64, self.length)

    def _next(self):
        """Increment the (shared) current index value by one (only happens once per write operation)"""
        self._index.value += 1

    @property
    def index(self):
        """Return the (shared) current index value"""
        return self._index.value

    def _build(self):
        """(Optional) method which is called after subprocess fork and which can be used to set up
        fork-specific parts of the attribute"""
        pass

    def build(self):

        indices = np.frombuffer(self._indices_raw.get_obj(), ctypes.c_int64)
        self._indices = indices.reshape((self.length,))
        self._indices[:] = -1

        times = np.frombuffer(self._times_raw.get_obj(), ctypes.c_double)
        self._times = times.reshape((self.length,))
        self._times[:] = np.nan

        # Call subclass build implementations
        self._build()

    def _get_times(self, indices: List[int]) -> np.ndarray:
        """Returns the list of time points corresponding to the indices in the interval [start_idx, end_idx)
        of datapoints written to the attribute """

        return self._times[indices]

    def _get_indices(self, indices: List[int]) -> np.ndarray:
        """Return list of indices, based on the 'last' number of datapoints specified"""

        return self._indices[indices]

    def get_times(self, last) -> np.ndarray:
        """Returns the list of time points corresponding to the <last> number of datapoints written to the attribute """
        return self._get_times(*self._get_range(last))

    def has_new_entry(self) -> bool:
        return self._new_data_flag.value

    def set_new(self, state: bool) -> None:
        """Set _new_data state of this attribute. This usually happens when attribute is written to
        or when the last attribute data is written to file"""
        self._new_data_flag.value = state

    def add_to_file(self):
        """Convenience method for calling write_to_file method on this attribute"""
        write_to_file(vxipc.LocalProcess, self.name)

    @abstractmethod
    def _get_data(self, indices: List[int]) -> Iterable:
        """Method that is called by read() method. Should return some kind of iterable"""
        pass

    @abstractmethod
    def _read_empty_return(self) -> Tuple[List[int], List[float], Any]:
        """Method to be called when read() method determines that result should be empty.
        This method should return an empty version of the same types as _read()"""
        pass

    def read(self, last: int = None, from_idx: int = None):
        if last is not None:
            return self[-last:]
        elif from_idx is not None:
            return self[from_idx:]
        else:
            return self[-1]

    def __getitem__(self, item):
        # Determine what the index_list should be for the selected subset
        #  Note that index_list should ultimately be a list of relative indices within the ring buffer
        if isinstance(item, int):

            # Positive/zero index: this can only be an absolute index
            if item >= 0:
                index = item % self.length

            # Negative index
            else:
                index = (self.index + item) % self.length

            index_list = [index]

        elif isinstance(item, slice):
            start, stop, step = item.start, item.stop, item.step

            if stop is not None or step is not None:
                raise KeyError('Stop and step are not supported right now')

            # Get all indices from start to currently active (written to) index

            # Positive/zero index start: can only be absolute index
            if start >= 0:
                indices = range(start, self.index)

            # Negative index
            else:
                indices = range(self.index + start, self.index)

            # Calculate relative indices
            index_list = [i % self.length for i in indices]

        else:
            raise KeyError

        return self._get_indices(index_list), self._get_times(index_list), self._get_data(index_list)

    @abstractmethod
    def _write(self, internal_idx: int, value: Any):
        """Method that is called by write() method. Should handle the actual writing of the attribute datapoint
        at the given 'internal_idx' position in the buffer."""
        pass

    def write(self, value: Any) -> None:
        """Write datapoint to the buffer."""

        # Check time difference between last and current write operation and print a warning if it's too low
        #  Individual occurrences may be caused by a temporary hiccups of the system
        #  Regular occurrences may indicate an underlying issue with the timing precision of the system
        #  or repeated erreneous calls to the write function of the attribute during a
        #  single event loop iteration of the corresponding producer module
        if np.isclose(self._last_time, vxipc.get_time(), rtol=0., atol=vxipc.LocalProcess.interval / 4.):
            log.warning(f'Trying to repeatedly write to attribute "{self.name}" '
                        f'in process {vxipc.LocalProcess.name} during same iteration. '
                        f'Last={self._last_time} / Current={vxipc.LocalProcess.global_t}')

        internal_idx = self.index % self.length

        # Set time for this entry
        self._times[internal_idx] = vxipc.get_time()

        # Set time for this entry
        self._indices[internal_idx] = self.index

        # Write data
        self._write(internal_idx, value)

        # Set "new" flag
        self.set_new(True)

        # Update last time
        self._last_time = vxipc.get_time()

        # Advance buffer
        self._next()

    def _get_range(self, last: int) -> Tuple[int, int]:
        """Return the internal index range based on the specified 'last' number of datapoints in the attribute buffer


        """

        # Make sure nothing weird is happening
        assert last < self.length, 'Trying to read more values than stored in buffer'
        assert last >= 0, 'Trying to read negative number of entries from buffer'

        # Regular read: fetch some number of entries from buffer
        if last > 0:
            internal_idx = self.index % self.length
            start_idx = internal_idx - last
        # Read current entry from buffer
        # (Should only be done in producer! In consumer the result is unpredictable)
        else:
            internal_idx = (self.index + 1) % self.length
            start_idx = internal_idx - 1

        # Return start and end of index range
        return start_idx, internal_idx


class ArrayType:
    """Corresponding ctype and numpy array datatypes for array attributes"""

    bool = (ctypes.c_bool, bool)

    int8 = (ctypes.c_int8, np.int8)
    int16 = (ctypes.c_int16, np.int16)
    int32 = (ctypes.c_int32, np.int32)
    int64 = (ctypes.c_int64, np.int64)

    uint8 = (ctypes.c_uint8, np.uint8)
    uint16 = (ctypes.c_uint16, np.uint16)
    uint32 = (ctypes.c_uint32, np.uint32)
    uint64 = (ctypes.c_uint64, np.uint64)

    float32 = (ctypes.c_float, np.float32)
    float64 = (ctypes.c_double, np.float64)


class ArrayAttribute(Attribute):
    """Array buffer attribute for synchronization of datasets.

    Uses a shared array for fast read and write of large amounts of data
    or strictly numeric data that can be mapped to a C array.

    Parameters
    ----------
    shape: tuple of int
        size of the dataset to be mapped to the array buffered array
    dtype: `vxpy.core.attribute.ArrayType`
        Datatype of the attribute
    """

    # TODO: chunked and un-chunked data structures can be unified (un-chunked attributes are chunked with chunk_num 1)

    def __init__(self, name, shape, dtype: Tuple[object, np.number], **kwargs):
        Attribute.__init__(self, name, **kwargs)

        assert isinstance(shape, tuple), 'size must be tuple with dimension sizes'
        assert isinstance(dtype, tuple), 'dtype must be tuple with (ctype,np-type)'

        self._raw: List[mp.Array] = []
        self._data: List[np.ndarray] = []
        self.shape = shape
        self._dtype = dtype

        # By default, calculate length based on dtype, shape and DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE
        max_multiplier = 1.
        itemsize = np.dtype(self._dtype[1]).itemsize  # number of bytes for datatype
        attr_el_size = np.product(self.shape)  # number of elements

        # Significantly reduce max attribute buffer size in case element size is < 1KB
        if (itemsize * attr_el_size) < 10 ** 3:
            max_multiplier = 0.01

        self._length = int((max_multiplier * DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE) // (attr_el_size * itemsize))

        init = int(np.product((self.length,) + self.shape))
        self._raw = mp.Array(self._dtype[0], init)
        self._data = np.array([])

        # Create list with time points
        self._make_times()
        self._make_indices()

    def __repr__(self):
        return f"{ArrayAttribute.__name__}('{self.name}', {self.shape}, {self.dtype})"

    @property
    def dtype(self):
        return self._dtype

    @property
    def numpytype(self):
        return self._dtype[1]

    @property
    def ctype(self):
        return self._dtype[0]

    def _build_array(self, raw: mp.Array, length: int) -> np.ndarray:
        """Create the numpy array from the ctype array object and reshape to fit"""
        np_array = np.frombuffer(raw.get_obj(), self._dtype[1])
        return np_array.reshape((length,) + self.shape)

    def _get_lock(self, use_lock: bool) -> mp.Lock:
        """Return lock to array object that corresponds"""
        if not use_lock:
            return DummyLockContext()

        lock = self._raw.get_lock

        return lock()

    def _build(self) -> None:
        """Build method that is called upon initialization in the subprocess fork.
        """
        self._data = self._build_array(self._raw, self.length)

    def _get_data(self, indices: List[int]) -> np.ndarray:
        """Read method of ArrayAttribute.
        Returns a numpy array with the datapoints in the interval [start_idx, end_idx)"""

        with self._get_lock(True):
            data = np.copy(self._data[indices])

        return data

    def _read_empty_return(self) -> Tuple[List[int], List[float], np.ndarray]:
        """Method to be called when read() method determines that result should be empty.
        This method should return an empty version of the same types as _read()"""
        return [], [], np.array([])

    def _write(self, internal_idx: int, value: np.number) -> None:
        """Method that is called by write() method. Should handle the actual writing of the attribute datapoint
        at the given 'internal_idx' position in the buffer."""

        with self._get_lock(True):
            self._data[internal_idx] = value


class ObjectAttribute(Attribute):
    """Object attribute, which can be used to store and synchronize Python objects."""

    def __init__(self, name, **kwargs):
        Attribute.__init__(self, name, **kwargs)

        # Define detault length
        self._length = 1000

        # Set default shape to 1
        self.shape = (None,)

        # Create shared list
        self._data = vxipc.Manager.list([None] * self.length)

        # Create list with time points
        self._make_times()

        # Create list with indices
        self._make_indices()

    def _get_data(self, indices: List[int]) -> List[Any]:
        """use_lock not used, because manager handles locking"""
        return [self._data[i] for i in indices]

    def _read_empty_return(self) -> Tuple[List, List, List]:
        """Method to be called when read() method determines that result should be empty.
        This method should return an empty version of the same types as _read()"""
        return [], [], []

    def _write(self, internal_idx: int, value: Any) -> None:
        """Method that is called by write() method. Should handle the actual writing of the attribute datapoint
        at the given 'internal_idx' position in the buffer."""
        # Set data
        self._data[internal_idx] = value


class DummyLockContext:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
