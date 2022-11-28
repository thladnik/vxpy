"""
vxPy ./core/attribute.py
Copyright (C) 2022 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
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


def init(attrs: Dict[str, Attribute]) -> None:
    """Calls the build function of all specified attributes"""
    if attrs is None:
        return

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')

    Attribute.all.update(attrs)
    for attr in Attribute.all.values():
        attr.build()


def read_attribute(attr_name: str, *args, **kwargs) -> Union[Tuple[List, List, Union[List, np.ndarray]], None]:
    """Convenience method for calling an attribute's read function via its name"""
    if attr_name not in Attribute.all:
        return

    return Attribute.all[attr_name].read(*args, **kwargs)


def write_attribute(attr_name: str, *args, **kwargs) -> None:
    """Convenience method for calling an attribute's write function via its name"""
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].write(*args, **kwargs)


def match_to_record_attributes(attr_name: str) -> Tuple[int, bool]:
    """Method matches a given attribute name to a list of attribute name templates to determine whether
     the attribute should be included for recording to file"""
    attribute_filters = config.CONF_REC_ATTRIBUTES

    matched = False
    for filt_string in attribute_filters:

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

        # Return if negative match result was found
        if match and neg:
            return -1, False

        # Update
        matched = matched or match

    # No matches
    return 1, matched


def write_to_file(instance: Union[vxprocess.AbstractProcess, vxroutine.Routine], attr_name: str) -> None:
    process_name = instance.name

    # If provided process name is not listed in attribute's to-file dictionary, create the associated list
    if process_name not in Attribute.to_file:
        Attribute.to_file[process_name] = []

    # If attribute does not exist, it cannot be added to the to-file list
    if attr_name not in Attribute.all:
        msg = 'Attribute does not exist.'
    else:
        # Check attribute name against templates
        found, included = match_to_record_attributes(attr_name)

        # If attribute name is included by template list, append to the to_file list
        if included:
            log.info(f'Set attribute "{attr_name}" to be written to file. ')
            Attribute.to_file[process_name].append(Attribute.all[attr_name])
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


def get_permanent_attributes(process_name: str = None) -> List[Attribute]:
    """Method returns a list of all attributes that are marked to be saved to file
    """
    if process_name is None:
        process_name = vxipc.LocalProcess.name

    if process_name not in Attribute.to_file:
        return []

    return Attribute.to_file[process_name]


def get_permanent_data(process_name: str = None) -> Iterator[Attribute]:
    """Returns all newly added attribute data to be written to file
    for the specified process.

    :param process_name: Name of process for which to return data
    :type process_name: str, optional

    :return A
    :rtype Iterator[Tuple[str, Any]
    """
    for attribute in get_permanent_attributes(process_name):
        if attribute.has_new_entry():
            # Yield attribute
            yield attribute

            # Reset "new" flag
            attribute.set_new(False)


class Attribute(ABC):
    """Abstract Attribute class at the core of vxPy's data management structure.
    Attributes act as ring buffers and are, by default, shared and synchronized
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
    to_file: Dict[str, List[Attribute]] = {}
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

    @property
    def length(self):
        return self._length

    def _make_time(self):
        """Generate the shared list of times corresponding to individual datapoints in the buffer"""
        self._time: List[Union[float, None]] = vxipc.Manager.list([None] * self.length)

    def _next(self):
        """Increment the (shared) current index value by one (only happens once per write operation)"""
        self._index.value += 1

    @property
    def index(self):
        """Return the (shared) current index value"""
        return self._index.value

    def build(self):
        """(Optional) method which is called after subprocess fork and which can be used to set up
        fork-specific parts of the attribute"""
        pass

    def _get_times(self, start_idx, end_idx):
        """Returns the list of time points corresponding to the indices in the interval [start_idx, end_idx)
        of datapoints written to the attribute """
        if start_idx >= 0:
            return self._time[start_idx:end_idx]
        else:
            return self._time[start_idx:] + self._time[:end_idx]

    def get_times(self, last):
        """Returns the list of time points corresponding to the <last> number of datapoints written to the attribute """
        return self._get_times(*self._get_range(last))

    def has_new_entry(self):
        return self._new_data_flag.value

    def set_new(self, state: bool) -> None:
        """Set _new_data state of this attribute. This usually happens when attribute is written to
        or when the last attribute data is written to file"""
        self._new_data_flag.value = state

    def add_to_file(self):
        """Convenience method for calling write_to_file method on this attribute"""
        write_to_file(vxipc.LocalProcess, self.name)

    @abstractmethod
    def _read(self, start_idx, end_idx, use_lock) -> Iterable:
        """Method that is called by read() method. Should return some kind of iterable"""
        pass

    @abstractmethod
    def _read_empty_return(self) -> Tuple[List[int], List[float], Any]:
        """Method to be called when read() method determines that result should be empty.
        This method should return an empty version of the same types as _read()"""
        pass

    def read(self, last: int = None, use_lock: bool = True, from_idx: int = None) -> Tuple[List[int], List[float], Any]:
        """Read datapoints from the buffer.
        By default, this returns the last written datapoint from the attribute buffer.
        If from_idx is not None and a scalar integer value, this will return
        all datapoints from (but not including) from_idx. """
        if last is None:
            # By default, set last to 1 if from_idx is not specified
            if from_idx is None:
                last = 1

            # Otherwise calculate number of elements to be read based on from_idx
            else:
                last = self.index - from_idx
                # If this turns up 0, return nothing, as by default read(last=0)
                # would be used in producer to read current value (which consumers should never do)
                if last <= 0:
                    return self._read_empty_return()

        # Return indices, times, datasets
        indices = self._get_index_list(last)
        return indices, self.get_times(last), self._read(*self._get_range(last), use_lock)

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
        self._time[internal_idx] = vxipc.get_time()

        # Write data
        self._write(internal_idx, value)

        # Set "new" flag
        self.set_new(True)

        # Update last time
        self._last_time = vxipc.get_time()

        # Advance buffer
        self._next()

    def _get_range(self, last: int) -> Tuple[int, int]:
        """Return the internal index range based on the specified 'last' number of datapoints in the attribute buffer"""

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

    def _get_index_list(self, last: int) -> List[int]:
        """Return list of indices, based on the 'last' number of datapoints specified"""
        return list(range(self.index - last, self.index))


class ArrayType:
    """Corresponding ctype and numpy array datatypes for array attributes"""

    bool = (ctypes.c_bool, np.bool)

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
    """Array buffer attribute for synchronization of large datasets.
    Uses a shared array for fast read and write of large amounts of data.

    Optionally supports chunking of buffer into independent segments. This is
    particularly useful when long read operations are expected (e.g. when
    reading multiple frames of RGB video data), as these tend to block writing
    by producer when use_lock=True is set

    :param shape: Tuple of dimension size of the buffered array
    :type shape: tuple
    :param dtype: Datatype of ArrayAttribute
    :type dtype: class.`vxpy.core.attribute.ArrayType`
    :param chunked: Flag to indicate whether chunking should be used
    :type chunked: bool, optional
    :param chunk_size: Length of chunks if chunked=True. If chunk_size is not
        set, but chunked=True, chunk_size will be determined based on
        dtype and length
    :type chunk_size: int, optional
    """

    # TODO: chunked and un-chunked data structures can be unified (un-chunked attributes are chunked with chunk_num 1)

    def __init__(self, name, shape, dtype: Tuple[object, np.number], chunked=False, chunk_size=None, **kwargs):
        Attribute.__init__(self, name, **kwargs)

        assert isinstance(shape, tuple), 'size must be tuple with dimension sizes'
        assert isinstance(dtype, tuple), 'dtype must be tuple with (ctype,np-type)'
        assert isinstance(chunked, bool), 'chunked has to be bool'
        assert isinstance(chunk_size, int) or chunk_size is None, 'chunk_size must be int or None'

        self._raw: List[mp.Array] = []
        self._data: List[np.ndarray] = []
        self.shape = shape
        self._dtype = dtype
        self._chunked = chunked
        self._chunk_size = chunk_size
        self._rising_edge_trigger_callbacks = vxipc.Manager.list([])

        # By default, calculate length based on dtype, shape and DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE
        max_multiplier = 1.
        itemsize = np.dtype(self._dtype[1]).itemsize
        attr_el_size = np.product(self.shape)

        # Significantly reduce max attribute buffer size in case element size is < 1KB
        if (itemsize * attr_el_size) < 10 ** 3:
            max_multiplier = 0.01

        self._length = int((max_multiplier * DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE) // (attr_el_size * itemsize))

        if self._chunked and self._chunk_size is not None:
            assert self.length % self._chunk_size == 0, 'Chunk size of buffer does not match its length'

        # Disable for short lengths
        if self._chunked and self.length < 10:
            self._chunked = False
            log.warning('Automatic chunking disabled (auto)', 'Buffer length too small.')

        if self._chunked and self._chunk_size is None:
            for s in range(self.length // 10, self.length):
                if self.length % s == 0:
                    self._chunk_size = s
                    break

            if self._chunk_size is None:
                self._chunk_size = self.length // 10
                self._length = 10 * self._chunk_size
                log.warning('Unable to find suitable chunk size.',
                            f'Resize buffer to match closest length. {self._chunk_size}/{self.length}')

        self._chunk_num = None
        if self._chunked:
            # This should be int
            self._chunk_num = self.length // self._chunk_size

        # Init data structures
        if self._chunked:
            init = int(np.product((self._chunk_size,) + self.shape))
            self._raw = []
            for i in range(self._chunk_num):
                self._raw.append(mp.Array(self._dtype[0], init))
            self._data = []
        else:
            init = int(np.product((self.length,) + self.shape))
            self._raw = mp.Array(self._dtype[0], init)
            self._data = []

        # Create list with time points
        self._make_time()

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

    def _get_lock(self, chunk_idx: int, use_lock: bool) -> mp.Lock:
        """Return lock to array object that corresponds"""
        if not use_lock:
            return DummyLockContext()

        if chunk_idx is None:
            lock = self._raw.get_lock
        else:
            lock = self._raw[chunk_idx].get_lock

        return lock()

    def build(self) -> None:
        """Build method that is called upon initialization in the subprocess fork.
        """
        if self._chunked:
            for raw in self._raw:
                self._data.append(self._build_array(raw, self._chunk_size))
        else:
            self._data = self._build_array(self._raw, self.length)

    def _read(self, start_idx, end_idx, use_lock) -> np.ndarray:
        """Read method of ArrayAttribute.
        Returns a numpy array with the datapoints in the interval [start_idx, end_idx)"""

        if self._chunked:
            start_chunk = start_idx // self._chunk_size
            chunk_start_idx = start_idx % self._chunk_size
            end_chunk = end_idx // self._chunk_size
            chunk_end_idx = end_idx % self._chunk_size

            # Read within one chunk
            if start_chunk == end_chunk:
                with self._get_lock(start_chunk, use_lock):
                    return self._data[start_chunk][chunk_start_idx:chunk_end_idx]

            # Read across multiple chunks
            np_arrays = list()
            with self._get_lock(start_chunk, use_lock):
                np_arrays.append(self._data[start_chunk][chunk_start_idx:])
            for ci in range(start_chunk + 1, end_chunk):
                with self._get_lock(ci, use_lock):
                    np_arrays.append(self._data[ci][:])
            with self._get_lock(end_chunk, use_lock):
                np_arrays.append(self._data[end_chunk][:chunk_end_idx])

            return np.concatenate(np_arrays)

        else:
            with self._get_lock(None, use_lock):
                if start_idx >= 0:
                    return self._data[start_idx:end_idx].copy()
                else:
                    ar1 = self._data[start_idx:]
                    ar2 = self._data[:end_idx]
                    return np.concatenate((ar1, ar2))

    def _read_empty_return(self) -> Tuple[List[int], List[float], np.ndarray]:
        """Method to be called when read() method determines that result should be empty.
        This method should return an empty version of the same types as _read()"""
        return [], [], np.array([])

    def _write(self, internal_idx: int, value: np.number) -> None:
        """Method that is called by write() method. Should handle the actual writing of the attribute datapoint
        at the given 'internal_idx' position in the buffer."""

        # Set data
        if self._chunked:
            chunk_idx = internal_idx // self._chunk_size
            idx = internal_idx % self._chunk_size

            with self._get_lock(chunk_idx, True):
                self._data[chunk_idx][idx] = value
        else:
            with self._get_lock(None, True):
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
        self._make_time()

    def _read(self, start_idx: int, end_idx: int, use_lock: int) -> List[Any]:
        """use_lock not used, because manager handles locking"""
        if start_idx >= 0:
            return self._data[start_idx:end_idx]
        else:
            return self._data[start_idx:] + self._data[:end_idx]

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
