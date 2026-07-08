"""Attribute module for data acquisition and inter-process data synchronization.

Defines classes and functions for managing shared ring-buffer attributes that are
written by producer processes and read by consumer processes in vxPy.
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


def init(attrs: Union[Dict[str, 'Attribute'], None]) -> None:
    """Initialize attributes registry and build all attributes.

    Parameters
    ----------
    attrs : Union[Dict[str, 'Attribute'], None]
        Dictionary of attribute names to Attribute instances to register, or None.
    """

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')

    if attrs is not None:
        Attribute.all.update(attrs)

    for attr in Attribute.all.values():
        attr.build()


def read_attribute(attr_name: str, *args, **kwargs) -> Union[Tuple[np.ndarray, np.ndarray, Iterable], None]:
    """Read data from a registered attribute by name.

    Parameters
    ----------
    attr_name : str
        Name of the attribute to read from.
    *args : Any
        Additional positional arguments passed to the attribute's read method.
    **kwargs : Any
        Additional keyword arguments passed to the attribute's read method.

    Returns
    -------
    Union[Tuple[np.ndarray, np.ndarray, Iterable], None]
        Tuple of (indices, timestamps, data) or None if attribute not found.
    """

    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name].read(*args, **kwargs)


def write_attribute(attr_name: str, *args, **kwargs) -> None:
    """Write data to a registered attribute by name.

    Parameters
    ----------
    attr_name : str
        Name of the attribute to write to.
    *args : Any
        Additional positional arguments passed to the attribute's write method.
    **kwargs : Any
        Additional keyword arguments passed to the attribute's write method.
    """
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].write(*args, **kwargs)
    raise AttributeError(f'Attribute {attr_name} not found.')


def match_to_record_attributes(attr_name: str) -> Tuple[bool, bool, Dict]:
    """Match attribute name against recording templates and return recording operations.

    Parameters
    ----------
    attr_name : str
        Name of the attribute to match against templates.

    Returns
    -------
    Tuple[bool, bool, Dict]
        Tuple of (found, include, record_ops) where found indicates if a template matched,
        include indicates if the attribute should be recorded, and record_ops contains recording operations.
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
    """Register an attribute to be written to file from a process or routine.

    Parameters
    ----------
    instance : Union[vxprocess.AbstractProcess, vxroutine.Routine]
        The process or routine instance that will write the attribute to file.
    attr_name : str
        Name of the attribute to write to file.
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
    """Get list of all registered attribute names.

    Returns
    -------
    List[str]
        List of attribute names registered in the global Attribute registry.
    """
    return [n for n in Attribute.all.keys()]


def get_attribute_list() -> List[Tuple[str, 'Attribute']]:
    """Get list of all registered attributes as (name, attribute) tuples.

    Returns
    -------
    List[Tuple[str, 'Attribute']]
        List of (attribute_name, Attribute_instance) tuples for all registered attributes.
    """
    return [(k, v) for k, v in Attribute.all.items()]


def get_attribute(attr_name: str) -> Union['Attribute', None]:
    """Get a registered attribute by name.

    Parameters
    ----------
    attr_name : str
        Name of the attribute to retrieve.

    Returns
    -------
    Union['Attribute', None]
        The Attribute instance if found, None otherwise.
    """
    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name]


def get_permanent_attributes(process_name: str = None) -> List[Tuple['Attribute', Dict]]:
    """Get list of attributes registered to be written to file for a process.

    Parameters
    ----------
    process_name : str
        Name of the process. If None, uses the current LocalProcess name.

    Returns
    -------
    List[Tuple['Attribute', Dict]]
        List of (Attribute_instance, record_ops) tuples for the specified process.
    """
    if process_name is None:
        process_name = vxipc.LocalProcess.name

    if process_name not in Attribute.to_file:
        return []

    return Attribute.to_file[process_name]


def get_permanent_data(process_name: str = None) -> Iterator[Tuple['Attribute', Dict]]:
    """Yield attributes with new data entries for writing to file from a process.

    Parameters
    ----------
    process_name : str
        Name of the process. If None, uses the current LocalProcess name.

    Returns
    -------
    Iterator[Tuple['Attribute', Dict]]
        Iterator yielding (Attribute_instance, record_ops) tuples for attributes with new data.
    """
    for attribute, record_ops in get_permanent_attributes(process_name):
        if attribute.has_new_entry():
            # Yield attribute
            yield attribute, record_ops

            # Reset "new" flag
            attribute.reset_new_counter()


class Attribute(ABC):
    """Attribute class."""

    all: Dict[str, 'Attribute'] = {}
    to_file: Dict[str, List[Tuple['Attribute', Dict]]] = {}
    _instance: 'ArrayAttribute' = None

    def __init__(self, name: str, length: int = None):
        """Initialize an Attribute with a name and optional buffer length.

        Parameters
        ----------
        name : str
            Unique name identifier for this attribute.
        length : int
            Maximum number of entries to store in the ring buffer. If None, defaults are applied.
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
        """  repr  .
        """
        return f'{self.__class__.__name__}(\'{self.name}\')'

    @property
    def length(self):
        """Return attribute buffer length
        """
        return self._length

    def _make_times(self):
        """Create shared time array with length of attribute buffer length
        """
        self._times_raw = mp.Array(ctypes.c_double, self.length)

    def _make_indices(self):
        """Create shared index array with length of attribute buffer length
        """
        self._indices_raw = mp.Array(ctypes.c_int64, self.length)

    def _next(self):
        """Increment internal buffer index
        """
        self._index.value += 1

    @property
    def index(self):
        """Return internal buffer index
        """
        return self._index.value

    def _build(self):
        """Build the attribute buffer. This method should be implemented by subclasses to initialize
         their specific data structures and any additional resources needed for the attribute.
        """
        pass

    def build(self):
        """Initiale numpy arrays from shared index and time arrays in subprocess
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
        """Retrieve timestamps for the specified indices.

        Parameters
        ----------
        indices : List[int]
            List of internal buffer indices to retrieve timestamps for.

        Returns
        -------
        np.ndarray
            Array of timestamps corresponding to the requested indices.
        """

        return self._times[indices]

    def _get_indices(self, indices: List[int]) -> np.ndarray:
        """Retrieve internal indices for the specified relative indices.
        
        Parameters
        ----------
        indices : List[int]
            List of internal buffer indices to retrieve global indices for.

        Returns
        -------
        np.ndarray
            Array of global indices corresponding to the requested buffer positions.
        """
        return self._indices[indices]

    def get_times(self, last) -> np.ndarray:
        """Get timestamps for the last N entries in the buffer.

        Parameters
        ----------
        last : Any
            Number of recent entries to retrieve timestamps for.

        Returns
        -------
        np.ndarray
            Array of timestamps for the requested entries.
        """
        return self._get_times(*self._get_range(last))

    def has_new_entry(self) -> bool:
        """Check if the attribute has new data entries since last read.

        Returns
        -------
        bool
            True if there are new data entries, False otherwise.
        """
        return bool(self._new_data_num.value)

    def _added_new(self) -> None:
        """ added new.
        """
        self._new_data_num.value = self._new_data_num.value + 1

    def reset_new_counter(self) -> None:
        """Reset new counter.
        """
        self._new_data_num.value = 0

    def add_to_file(self):
        """Add to file.
        """
        write_to_file(vxipc.LocalProcess, self.name)

    @abstractmethod
    def _get_data(self, indices: List[int]) -> Iterable:
        """Retrieve data from the buffer at the specified indices.

        Parameters
        ----------
        indices : List[int]
            List of internal buffer indices to retrieve data for.

        Returns
        -------
        Iterable
            Data values corresponding to the requested indices.
        """
        pass

    @abstractmethod
    def _read_empty_return(self) -> Tuple[List[int], List[float], Any]:
        """Return empty data structure when no data is available.

        Returns
        -------
        Tuple[List[int], List[float], Any]
            Tuple of (empty_indices, empty_times, empty_data) for the attribute type.
        """
        pass

    def read(self, last: int = None, from_idx: int = None):
        """Read data from the attribute buffer.

        Parameters
        ----------
        last : int
            Read the last N entries from the buffer.
        from_idx : int
            Read all entries from the given index to the current end.
        """
        if last is not None:
            return self[-last:]
        elif from_idx is not None:
            return self[from_idx:]
        else:
            return self[-1]

    def __getitem__(self, item):
        """Index into the attribute buffer using integer or slice notation.

        Parameters
        ----------
        item : Any
            Integer index or slice to retrieve from the buffer.
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
        """Subclass write implementation

        Parameters
        ----------
        internal_idx : int
            Internal buffer index where the value should be written.
        value : Any
            The data value to write to the buffer.
        """
        pass

    def write(self, value: Any) -> None:
        """Write a value to the attribute buffer at the current index.

        Parameters
        ----------
        value : Any
            The data value to write to the buffer.
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
        """Calculate the internal buffer index range for reading the last N entries.

        Parameters
        ----------
        last : int
            Number of recent entries to read.

        Returns
        -------
        Tuple[int, int]
            Tuple of (start_index, end_index) for the internal buffer.
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
    """ArrayType class."""

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
        """Retrieve a data type pair (ctypes type, numpy type) by string name.

        Parameters
        ----------
        name : str
            String identifier of the data type (e.g., 'float32', 'int64', 'uint8').

        Returns
        -------
        Tuple[ctypes.py_object, np.number]
            Tuple of (ctypes_type, numpy_type) for the specified data type.
        """
        return getattr(cls, name)


class ArrayAttribute(Attribute):
    """ArrayAttribute class."""

    # TODO: chunked and un-chunked data structures can be unified (un-chunked attributes are chunked with chunk_num 1)

    def __init__(self, name, shape, dtype: Tuple[ctypes.py_object, np.number], **kwargs):
        """Initialize an array-based attribute with shape and data type.

        Parameters
        ----------
        name : Any
            Unique name identifier for this array attribute.
        shape : Any
            Tuple specifying the shape of each array entry in the buffer.
        dtype : Tuple[ctypes.py_object, np.number]
            Tuple of (ctypes_type, numpy_type) specifying the data type of array elements.
        **kwargs : Any
            Additional keyword arguments passed to parent Attribute constructor.
        """
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
        """  repr  .
        """
        return f"{ArrayAttribute.__name__}('{self.name}', {self.shape}, {self.dtype})"

    @property
    def dtype(self):
        """Dtype.
        """
        return self._dtype

    @property
    def numpytype(self):
        """Numpytype.
        """
        return self._dtype[1]

    @property
    def ctype(self):
        """Ctype.
        """
        return self._dtype[0]

    def _build_array(self, raw: mp.Array, length: int) -> np.ndarray:
        """Construct a numpy array view from a raw multiprocessing array.

        Parameters
        ----------
        raw : mp.Array
            Raw multiprocessing array to create a view from.
        length : int
            Number of entries in the buffer.

        Returns
        -------
        np.ndarray
            Reshaped numpy array view with shape (length,) + self.shape.
        """
        np_array = np.frombuffer(raw.get_obj(), self._dtype[1])
        return np_array.reshape((length,) + self.shape)

    def _get_lock(self, use_lock: bool) -> mp.Lock:
        """Get a lock context manager for thread-safe access to the buffer.

        Parameters
        ----------
        use_lock : bool
            If True, return an actual multiprocessing Lock. If False, return a dummy context.

        Returns
        -------
        mp.Lock
            Lock context manager or dummy context depending on use_lock parameter.
        """
        if not use_lock:
            return DummyLockContext()

        lock = self._raw.get_lock

        return lock()

    def _build(self) -> None:
        """ build.
        """
        self._data = self._build_array(self._raw, self.length)

    def _get_data(self, indices: List[int]) -> np.ndarray:
        """Retrieve array data from buffer at specified indices with thread-safe locking.

        Parameters
        ----------
        indices : List[int]
            List of internal buffer indices to retrieve data for.

        Returns
        -------
        np.ndarray
            Copy of the data arrays at the requested indices.
        """

        with self._get_lock(True):
            data = np.copy(self._data[indices])

        return data

    def _read_empty_return(self) -> Tuple[List[int], List[float], np.ndarray]:
        """Return empty data structure when no array data is available.

        Returns
        -------
        Tuple[List[int], List[float], np.ndarray]
            Tuple of (empty_indices_list, empty_times_list, empty_numpy_array).
        """
        return [], [], np.array([])

    def _write(self, internal_idx: int, value: np.number) -> None:
        """Write an array value to the buffer at the specified internal index with locking.

        Parameters
        ----------
        internal_idx : int
            Internal buffer index where the array should be written.
        value : np.number
            The array data to write to the buffer.
        """

        with self._get_lock(True):
            self._data[internal_idx] = value


class ObjectAttribute(Attribute):
    """ObjectAttribute class."""

    def __init__(self, name, **kwargs):
        """Initialize an object-based attribute for storing arbitrary Python objects.

        Parameters
        ----------
        name : Any
            Unique name identifier for this object attribute.
        **kwargs : Any
            Additional keyword arguments passed to parent Attribute constructor.
        """
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
        """Retrieve object data from buffer at specified indices.

        Parameters
        ----------
        indices : List[int]
            List of internal buffer indices to retrieve objects for.

        Returns
        -------
        List[Any]
            List of objects stored at the requested indices.
        """
        return [self._data[i] for i in indices]

    def _read_empty_return(self) -> Tuple[List, List, List]:
        """Return empty data structure when no object data is available.

        Returns
        -------
        Tuple[List, List, List]
            Tuple of (empty_indices_list, empty_times_list, empty_objects_list).
        """
        return [], [], []

    def _write(self, internal_idx: int, value: Any) -> None:
        """Write an object value to the buffer at the specified internal index.

        Parameters
        ----------
        internal_idx : int
            Internal buffer index where the object should be written.
        value : Any
            The object to write to the buffer.
        """
        # Set data
        self._data[internal_idx] = value


class DummyLockContext:
    """DummyLockContext class."""

    def __enter__(self):
        """  enter  .
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager without performing any locking operations.

        Parameters
        ----------
        exc_type : Any
            Exception type if an exception occurred in the context.
        exc_val : Any
            Exception value if an exception occurred in the context.
        exc_tb : Any
            Exception traceback if an exception occurred in the context.
        """
        pass
