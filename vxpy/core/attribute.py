"""Attribute module for data acquisition and inter-process data synchronization.
Defines classes and functions for managing shared data buffers and attributes in vxPy.
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
    """
    Initialize and build all specified attributes.

    Args:
        attrs (dict or None): Dictionary of attribute name to Attribute instance.
    """

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')

    if attrs is not None:
        Attribute.all.update(attrs)

    for attr in Attribute.all.values():
        attr.build()


def read_attribute(attr_name: str, *args, **kwargs) -> Union[Tuple[np.ndarray, np.ndarray, Iterable], None]:
    """
    Read data from an attribute by name.

    Args:
        attr_name (str): Name of the attribute.
        *args, **kwargs: Arguments passed to the attribute's read method.

    Returns:
        tuple or None: Data read from the attribute, or None if not found.
    """

    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name].read(*args, **kwargs)


def write_attribute(attr_name: str, *args, **kwargs) -> None:
    """
    Write data to an attribute by name.

    Args:
        attr_name (str): Name of the attribute.
        *args, **kwargs: Arguments passed to the attribute's write method.

    Raises:
        AttributeError: If the attribute is not found.
    """
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].write(*args, **kwargs)
    raise AttributeError(f'Attribute {attr_name} not found.')


def match_to_record_attributes(attr_name: str) -> Tuple[bool, bool, Dict]:
    """
    Match an attribute name to recording templates.

    Args:
        attr_name (str): Name of the attribute.

    Returns:
        tuple: (found, include, record_ops) where found is True if matched,
               include is True if included, and record_ops is the recording options.
    """
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

    # No matches
    return True, False, {}


def write_to_file(instance: Union[vxprocess.AbstractProcess, vxroutine.Routine], attr_name: str) -> None:
    """
    Mark an attribute to be written to file for a given process or routine.

    Args:
        instance (AbstractProcess or Routine): The process or routine instance.
        attr_name (str): Name of the attribute.
    """
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
    """
    Get a list of all attribute names.

    Returns:
        list: List of attribute names.
    """
    return [n for n in Attribute.all.keys()]


def get_attribute_list() -> List[Tuple[str, Attribute]]:
    """
    Get a list of tuples containing attribute names and objects.

    Returns:
        list: List of (name, Attribute) tuples.
    """
    return [(k, v) for k, v in Attribute.all.items()]


def get_attribute(attr_name: str) -> Union[Attribute, None]:
    """
    Get an attribute by name.

    Args:
        attr_name (str): Name of the attribute.

    Returns:
        Attribute or None: The attribute instance, or None if not found.
    """
    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name]


def get_permanent_attributes(process_name: str = None) -> List[Tuple[Attribute, Dict]]:
    """
    Get attributes marked to be saved to file for a process.

    Args:
        process_name (str, optional): Name of the process.

    Returns:
        list: List of (Attribute, record_ops) tuples.
    """
    if process_name is None:
        process_name = vxipc.LocalProcess.name

    if process_name not in Attribute.to_file:
        return []

    return Attribute.to_file[process_name]


def get_permanent_data(process_name: str = None) -> Iterator[Tuple[Attribute, Dict]]:
    """
    Yield newly added attribute data to be written to file for a process.

    Args:
        process_name (str, optional): Name of the process.

    Yields:
        tuple: (Attribute, record_ops) for attributes with new data.
    """
    for attribute, record_ops in get_permanent_attributes(process_name):
        if attribute.has_new_entry():
            # Yield attribute
            yield attribute, record_ops

            # Reset "new" flag
            attribute.reset_new_counter()


class Attribute(ABC):
    """
    Abstract base class for vxPy's data management attributes.

    Attributes act as ring buffers and are shared and synchronized
    across modules. Written by a producer, read by consumers.

    Args:
        name (str): Unique name of the attribute.
        length (int, optional): Length of the ring buffer.
    """

    all: Dict[str, Attribute] = {}
    to_file: Dict[str, List[Tuple[Attribute, Dict]]] = {}
    _instance: ArrayAttribute = None

    def __init__(self, name: str, length: int = None):
        """
        Initialize the attribute.

        Args:
            name (str): Unique name.
            length (int, optional): Buffer length.
        """
        assert name not in self.all, f'Duplicate attribute {name}'
        self.name = name
        Attribute.all[name] = self

        self.shape: tuple = ()
        self._length = length
        self._index = mp.Value(ctypes.c_uint64)
        self._last_time = np.inf
        self._new_data_num: mp.Value = mp.Value(ctypes.c_int64, 0)

        self._times: np.ndarray = np.array([])
        self._indices: np.ndarray = np.array([])

    def __repr__(self):
        """Return string representation of the attribute."""
        return f'{self.__class__.__name__}(\'{self.name}\')'

    @property
    def length(self):
        """Get the buffer length."""
        return self._length

    def _make_times(self):
        """Generate the shared list of times for buffer entries."""
        self._times_raw = mp.Array(ctypes.c_double, self.length)

    def _make_indices(self):
        """Generate the shared list of indices for buffer entries."""
        self._indices_raw = mp.Array(ctypes.c_int64, self.length)

    def _next(self):
        """Increment the shared current index value."""
        self._index.value += 1

    @property
    def index(self):
        """Get the current index value."""
        return self._index.value

    def _build(self):
        """
        Optional method called after subprocess fork for fork-specific setup.
        """
        pass

    def build(self):
        """
        Build the attribute's internal buffers and call subclass build.
        """
        indices = np.frombuffer(self._indices_raw.get_obj(), ctypes.c_int64)
        self._indices = indices.reshape((self.length,))
        self._indices[:] = -1

        times = np.frombuffer(self._times_raw.get_obj(), ctypes.c_double)
        self._times = times.reshape((self.length,))
        self._times[:] = np.nan

        # Call subclass build implementations
        self._build()

    def _get_times(self, indices: List[int]) -> np.ndarray:
        """
        Get time points for specified buffer indices.

        Args:
            indices (list): List of buffer indices.

        Returns:
            np.ndarray: Array of time points.
        """

        return self._times[indices]

    def _get_indices(self, indices: List[int]) -> np.ndarray:
        """
        Get buffer indices for specified indices.

        Args:
            indices (list): List of buffer indices.

        Returns:
            np.ndarray: Array of indices.
        """
        return self._indices[indices]

    def get_times(self, last) -> np.ndarray:
        """
        Get time points for the last N written entries.

        Args:
            last (int): Number of entries.

        Returns:
            np.ndarray: Array of time points.
        """
        return self._get_times(*self._get_range(last))

    def has_new_entry(self) -> bool:
        """
        Check if new data has been added.

        Returns:
            bool: True if new data exists.
        """
        return bool(self._new_data_num.value)

    def _added_new(self) -> None:
        """Increment the new data counter."""
        self._new_data_num.value = self._new_data_num.value + 1

    def reset_new_counter(self) -> None:
        """Reset the new data counter."""
        self._new_data_num.value = 0

    def add_to_file(self):
        """Convenience method for calling write_to_file method on this attribute"""
        write_to_file(vxipc.LocalProcess, self.name)

    @abstractmethod
    def _get_data(self, indices: List[int]) -> Iterable:
        """
        Get data for specified buffer indices.

        Args:
            indices (list): List of buffer indices.

        Returns:
            Iterable: Data for the indices.
        """
        pass

    @abstractmethod
    def _read_empty_return(self) -> Tuple[List[int], List[float], Any]:
        """
        Return empty data for read operations.

        Returns:
            tuple: Empty indices, times, and data.
        """
        pass

    def read(self, last: int = None, from_idx: int = None):
        """
        Read data from the buffer.

        Args:
            last (int, optional): Number of last entries to read.
            from_idx (int, optional): Start index to read from.

        Returns:
            tuple: Indices, times, and data.
        """
        if last is not None:
            return self[-last:]
        elif from_idx is not None:
            return self[from_idx:]
        else:
            return self[-1]

    def __getitem__(self, item):
        """
        Get data by index or slice.

        Args:
            item (int or slice): Index or slice.

        Returns:
            tuple: Indices, times, and data.

        Raises:
            KeyError: If the index is invalid.
        """
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
        """
        Write data to the buffer at the specified index.

        Args:
            internal_idx (int): Internal buffer index.
            value (Any): Value to write.
        """
        pass

    def write(self, value: Any) -> None:
        """
        Write a datapoint to the buffer.

        Args:
            value (Any): Value to write.
        """

        internal_idx = self.index % self.length

        # Set time for this entry
        self._times[internal_idx] = vxipc.get_time()

        # Set time for this entry
        self._indices[internal_idx] = self.index

        # Write data
        self._write(internal_idx, value)

        # Set "new" flag
        self._added_new()

        # Update last time
        self._last_time = vxipc.get_time()

        # Advance buffer
        self._next()

    def _get_range(self, last: int) -> Tuple[int, int]:
        """
        Get the internal index range for the last N entries.

        Args:
            last (int): Number of entries.

        Returns:
            tuple: (start_idx, internal_idx)
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

    @classmethod
    def get_type_by_str(cls, name: str) -> Tuple[ctypes.py_object, np.number]:
        return getattr(cls, name)


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

    def __init__(self, name, shape, dtype: Tuple[ctypes.py_object, np.number], **kwargs):
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
        attr_el_size = np.prod(self.shape)  # number of elements

        # Significantly reduce max attribute buffer size in case element size is < 1KB
        if (itemsize * attr_el_size) < 10 ** 3:
            max_multiplier = 0.01

        self._length = int((max_multiplier * DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE) // (attr_el_size * itemsize))

        init = int(np.prod((self.length,) + self.shape))
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
