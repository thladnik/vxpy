from __future__ import annotations
from abc import ABC, abstractmethod
import ctypes
import multiprocessing as mp
import numpy as np
import typing

from mappapp import Config
from mappapp import Def
from mappapp import IPC
from mappapp import Logging


def read_attribute(attr_name, *args, **kwargs):
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].read(*args, **kwargs)


def write_attribute(attr_name, *args, **kwargs):
    if attr_name in Attribute.all:
        return Attribute.all[attr_name].write(*args, **kwargs)


def build_attributes(attrs):
    if attrs is None:
        return

    Attribute.all.update(attrs)
    for attr in Attribute.all.values():
        attr.build()


def match_to_record_attributes(attr_name: str):
    attribute_filters = Config.Recording[Def.RecCfg.attributes]

    for string in attribute_filters:
        if '*' not in string:
            if string == attr_name:
                return True
        elif string.startswith('*') and string.endswith('*'):
            if string in attr_name:
                return True
        elif string.startswith('*'):
            if attr_name.endswith(string.strip('*')):
                return True
        elif string.endswith('*'):
            if attr_name.startswith(string.strip('*')):
                return True

    return False


def write_to_file(instance, attr_name):
    process_name = instance.name

    if process_name not in Attribute.to_file:
        Attribute.to_file[process_name] = []

    if attr_name not in Attribute.all:
        Logging.write(Logging.WARNING, f'Trying to write non-existent attribute {attr_name} to file')
        return

    if match_to_record_attributes(attr_name):
        Attribute.to_file[process_name].append(Attribute.all[attr_name])


def get_attribute(attr_name):
    if attr_name not in Attribute.all:
        return None

    return Attribute.all[attr_name]


def get_permanent_attributes(process_name=None):
    if process_name is None:
        process_name = IPC.Process.name

    return Attribute.to_file[process_name]


def get_permanent_data(process_name=None):
    if process_name is None:
        process_name = IPC.Process.name

    if process_name not in Attribute.to_file:
        return None

    for attribute in get_permanent_attributes(process_name):
        yield attribute.name, *[v[0] for v in attribute.read()]


class Attribute(ABC):

    all: typing.Dict[str, Attribute] = {}
    to_file: typing.Dict[str, typing.List[Attribute]] = {}

    def __init__(self, name: str, _length: int =100):
        assert name not in self.all, f'Duplicate attribute {name}'
        self.name = name
        Attribute.all[name] = self

        self._length = 100
        self._data = None
        self._index = mp.Value(ctypes.c_uint64)
        self._time = IPC.Manager.list([None] * self._length)

    def _next(self):
        self._index.value += 1

    @property
    def index(self):
        return self._index.value

    def build(self):
        pass

    def _get_times(self, start_idx, end_idx):
        if start_idx >= 0:
            return self._time[start_idx:end_idx]
        else:
            return self._time[start_idx:] + self._time[:end_idx]

    def get_times(self, last):
        return self._get_times(*self._get_range(last))

    def carry(self):
        self.write(self._read(*self._get_range(last=1), use_lock=True))

    @abstractmethod
    def _read(self, start_idx, end_idx, use_lock):
        pass

    def read(self, last=1, use_lock=True, from_idx=None):
        if from_idx is not None:
            last = self.index - from_idx
            # If this turns up 0, return nothing, as by default read(last=0)
            # would be used in producer to read current value (which consumers should never do)
            if last <= 0:
                # TODO: it's not a given that "datsets" would be a list, this may cause issues
                #  while reading ArrayAttributes for example
                return [], [], []
        # Return indices, times, datasets
        return self._get_index_list(last), self.get_times(last), self._read(*self._get_range(last), use_lock)

    @abstractmethod
    def write(self, value):
        pass

    def _get_range(self, last):
        assert last < self._length, 'Trying to read more values than stored in buffer'
        assert last >= 0, 'Trying to read negative number of entries from buffer'

        # Regular read: fetch some number of entries from buffer
        if last > 0:
            internal_idx = self.index % self._length
            start_idx = internal_idx - last
        # Read current entry from buffer
        # (Should only be done in producer! In consumer the result is unpredictable)
        else:
            internal_idx = (self.index + 1) % self._length
            start_idx = internal_idx - 1

        return start_idx, internal_idx

    def _get_index_list(self, last) -> typing.List:
        return list(range(self.index - last, self.index))


class ArrayType:
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

    Optionally supports chunking of buffer into independent segments. This is especially
    useful when long read operations are expected (e.g. when reading multiple frames of RGB video data),
    as these tend to block writing by producer when use_lock=True is set.
    :: size tuple of dimension size of the buffered array
    :: dtype tuple with datatypes in c and numpy (ctype, np-type)
    :: chunked bool which indicated whether chunking should be used
    :: chunk_size (optional) int which specifies chunk size if chunked=True
    """

    def __init__(self, name, shape, dtype, chunked=False, chunk_size=None, **kwargs):
        Attribute.__init__(self, name, **kwargs)

        assert isinstance(shape, tuple), 'size must be tuple with dimension sizes'
        assert isinstance(dtype, tuple), 'dtype must be tuple with (ctype,np-type)'
        assert isinstance(chunked, bool), 'chunked has to be bool'
        assert isinstance(chunk_size, int) or chunk_size is None, 'chunk_size must be int or None'

        self.shape = shape
        self.dtype = dtype
        self._chunked = chunked
        self._chunk_size = chunk_size

        if self._chunked and self._chunk_size is not None:
            assert self._length % self._chunk_size == 0, 'Chunk size of buffer does not match its length'

        # Automatically determine chunk_size
        if self._chunked and self._length < 10:
            self._chunked = False
            print('WARNING', 'Automatic chunking disabled (auto)', 'Buffer length too small.')

        if self._chunked and self._chunk_size is None:
            for s in range(self._length // 10, self._length):
                if self._length % s == 0:
                    self._chunk_size = s
                    break

            if self._chunk_size is None:
                self._chunk_size = self._length // 10
                self._length = 10 * self._chunk_size
                print('WARNING', 'Unable to find suitable chunk size.',
                      f'Resize buffer to match closest length. {self._chunk_size}/{self._length}')

        self._chunk_num = None
        if self._chunked:
            # This should be int
            self._chunk_num = self._length // self._chunk_size

        # Init data structures
        if self._chunked:
            init = int(np.product((self._chunk_size,) + self.shape))
            self._raw: typing.List[mp.Array] = list()
            for i in range(self._chunk_num):
                self._raw.append(mp.Array(self.dtype[0], init))
            self._data: typing.List[np.ndarray] = list()
        else:
            init = int(np.product((self._length,) + self.shape))
            self._raw: mp.Array = mp.Array(self.dtype[0], init)
            self._data: np.ndarray = None

    def _build_array(self, raw, length):
        np_array = np.frombuffer(raw.get_obj(), self.dtype[1])
        return np_array.reshape((length,) + self.shape)

    def _get_lock(self, chunk_idx, use_lock):
        if not(use_lock):
            return DummyLockContext()

        if chunk_idx is None:
            lock = self._raw.get_lock
        else:
            lock = self._raw[chunk_idx].get_lock

        return lock()

    def build(self) -> None:
        if self._chunked:
            for raw in self._raw:
                self._data.append(self._build_array(raw, self._chunk_size))
        else:
            self._data = self._build_array(self._raw, self._length)

    def _read(self, start_idx, end_idx, use_lock) -> np.ndarray:
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
            for ci in range(start_chunk+1, end_chunk):
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

    def write(self, value):
        # Index in buffer
        internal_idx = self.index % self._length

        # Set time for this entry
        self._time[internal_idx] = IPC.Process.global_t

        # Set data
        if self._chunked:
            chunk_idx = internal_idx // self._chunk_size
            idx = internal_idx % self._chunk_size

            with self._get_lock(chunk_idx, True):
                self._data[chunk_idx][idx] = value
        else:
            with self._get_lock(None, True):
                self._data[internal_idx] = value

        # Advance buffer
        self._next()

    def __setitem__(self, key, value):
        self._data[key % self._length] = value


class ObjectAttribute(Attribute):
    def __init__(self, name, **kwargs):
        Attribute.__init__(self, name, **kwargs)

        self._data = IPC.Manager.list([None] * self._length)

    def _read(self, start_idx, end_idx, use_lock):
        """use_lock not used, because manager handles locking"""
        if start_idx >= 0:
            return self._data[start_idx:end_idx]
        else:
            return self._data[start_idx:] + self._data[:end_idx]

    def write(self, value):
        internal_idx = self.index % self._length

        # Set time for this entry
        self._time[internal_idx] = IPC.Process.global_t

        # Set data
        self._data[internal_idx] = value

        # Advance buffer
        self._next()

    def __setitem__(self, key, value):
        self._data[key % self._length] = value


class DummyLockContext:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass