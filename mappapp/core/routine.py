"""
MappApp ./process.py - Routine wrapper, abstract routine and ring buffer implementations.
Copyright (C) 2020 Tim Hladnik

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
import ctypes
import multiprocessing as mp
import numpy as np
import time

from mappapp import Logging,IPC,Def
from mappapp.gui.core import Plotter

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any,List, Type


class AbstractRoutine:
    """AbstractRoutine to be subclassed by all implementations of routines.
    """

    process_name: str = None


    def __init__(self):

        self._triggers = dict()

        self._trigger_callbacks = dict()

        # List of methods open to rpc calls
        self.exposed = []

        # List of required device names
        self.required = list()

        # Attributes to be written to file
        self.file_attrs = list()

        # Default ring buffer instance for routine
        self.buffer: RingBuffer = RingBuffer()

    def initialize(self):
        """Called in forked process"""
        pass

    def execute(self, *args, **kwargs):
        """Method is called on every iteration of the producer.

        Compute method is called on data updates (in the producer process).
        Every buffer needs to implement this method and it's used to set all buffer attributes"""
        raise NotImplementedError(f'_compute not implemented in {self.__class__.__name__}')

    def add_file_attribute(self, attr_name):
        if attr_name in self.file_attrs:
            Logging.write(Logging.WARNING,f'Attribute "{attr_name}" already set to be written to file')
            return

        self.file_attrs.append(attr_name)

    def register_with_ui_plotter(self, routine_cls: Type[AbstractRoutine], attr_name: str, start_idx: int, *args, **kwargs):
        IPC.rpc(Def.Process.Gui, Plotter.add_buffer_attribute,
                routine_cls,attr_name,start_idx,*args,**kwargs)

    def to_file(self) -> (str, float, Any):
        """Method may be reimplemented. Can be used to alter the output to file.

        Implementations of this method should yield a tuple
        with (attr_name: str, time: float, attr_data: Any)
        """
        for attr_name in self.file_attrs:
            idcs, t, data = getattr(self.buffer, attr_name).read(0)

            if data[0] is None:
                continue

            yield attr_name, t[0], data[0]

    def read(self, attr_name: str, *args, **kwargs):
        """Pass-through to buffer read method for convenience"""
        return self.buffer.read(attr_name, *args, **kwargs)

    def add_trigger(self, trigger_name):
        self._triggers[trigger_name] = Trigger(self)

    def connect_to_trigger(self, trigger_name, routine, callback):
        self.exposed.append(callback)

        if routine.process_name not in self._trigger_callbacks:
            self._trigger_callbacks[routine.process_name] = dict()

        if routine.__qualname__ not in self._trigger_callbacks[routine.process_name]:
            self._trigger_callbacks[routine.process_name][routine.__qualname__] = dict()

        self._trigger_callbacks[routine.process_name][routine.__qualname__][trigger_name] = callback

    def connect_triggers(self, _routines):
        for process_name, routines in self._trigger_callbacks.items():
            for routine_name, callbacks in routines.items():
                for trigger_name, callback in callbacks.items():
                    _routines[process_name][routine_name]._triggers[trigger_name].add_callback(self.process_name, callback)


class Trigger:
    _registered = []
    def __init__(self, routine):
        self.routine = routine

    def add_callback(self, process_name, callback):
        self._registered.append((process_name, callback))

    def emit(self):
        for process_name, callback in self._registered:
            IPC.rpc(process_name,callback)


class CameraRoutine(AbstractRoutine):

    process_name = Def.Process.Camera

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)


class DisplayRoutine(AbstractRoutine):

    process_name = Def.Process.Display

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)


class IoRoutine(AbstractRoutine):

    process_name = Def.Process.Io

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)


class DummyLockContext:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class BufferAttribute:

    def __init__(self, length=100):
        self._length = length
        self._data = None
        self._index = None
        self._time = IPC.Manager.list([None] * self._length)
        self._buffer: RingBuffer

    def build(self):
        pass

    def set_buffer(self, buffer):
        assert isinstance(buffer, RingBuffer), f'Buffer needs to be {RingBuffer.__name__}'
        self._buffer = buffer

    def _get_times(self, start_idx, end_idx):
        if start_idx >= 0:
            return self._time[start_idx:end_idx]
        else:
            return self._time[start_idx:] + self._time[:end_idx]

    def get_times(self, last):
        return self._get_times(*self._get_range(last))

    def get(self, current_idx):
        self._index = current_idx
        return self

    def _read(self, start_idx, end_idx, use_lock):
        raise NotImplementedError(f'_read not implemented in {self.__class__.__name__}')

    def read(self, last=1, use_lock=True, from_idx=None):
        if from_idx is not None:
            last = self._index - from_idx
            # If this turns up 0, return nothing, as by default read(last=0)
            # would be used in producer to read current value (which consumers should never do)
            if last <= 0:
                # TODO: it's not a given that "datsets" would be a list, this may cause issues
                #  while reading ArrayAttributes for example
                return [], [], []
        # Return indices, times, datasets
        return self._get_index_list(last), self.get_times(last), self._read(*self._get_range(last), use_lock)

    def write(self, value):
        raise NotImplementedError(f'Method write not implemented in {self.__class__}')

    def _get_range(self, last):
        assert last < self._length, 'Trying to read more values than stored in buffer'
        assert last >= 0, 'Trying to read negative number of entries from buffer'

        # Regular read: fetch some number of entries from buffer
        if last > 0:
            internal_idx = self._index % self._length
            start_idx = internal_idx - last
        # Read current entry from buffer
        # (Should only be done in producer! In consumer the result is unpredictable)
        else:
            internal_idx = (self._index + 1) % self._length
            start_idx = internal_idx - 1

        return start_idx, internal_idx

    def _get_index_list(self, last) -> List:
        return list(range(self._index - last, self._index))


class ArrayDType:
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


class ArrayAttribute(BufferAttribute):
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

    def __init__(self, shape, dtype, chunked=False, chunk_size=None, **kwargs):
        BufferAttribute.__init__(self, **kwargs)

        assert isinstance(shape, tuple), 'size must be tuple with dimension sizes'
        assert isinstance(dtype, tuple), 'dtype must be tuple with (ctype,np-type)'
        assert isinstance(chunked, bool), 'chunked has to be bool'
        assert isinstance(chunk_size, int) or chunk_size is None, 'chunk_size must be int or None'

        self._shape = shape
        self._dtype = dtype
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
            init = int(np.product((self._chunk_size,) + self._shape))
            self._raw: List[mp.Array] = list()
            for i in range(self._chunk_num):
                self._raw.append(mp.Array(self._dtype[0], init))
            self._data: List[np.ndarray] = list()
        else:
            init = int(np.product((self._length,) + self._shape))
            self._raw: mp.Array = mp.Array(self._dtype[0], init)
            self._data: np.ndarray = None

    def _build_array(self, raw, length):
        np_array = np.frombuffer(raw.get_obj(), self._dtype[1])
        return np_array.reshape((length,) + self._shape)

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
        internal_idx = self._index % self._length

        # Set time for this entry
        self._time[internal_idx] = self._buffer.get_time()

        # Set data
        if self._chunked:
            chunk_idx = internal_idx // self._chunk_size
            idx = internal_idx % self._chunk_size

            with self._get_lock(chunk_idx, True):
                self._data[chunk_idx][idx] = value
        else:
            with self._get_lock(None, True):
                self._data[internal_idx] = value

    def __setitem__(self, key, value):
        self._data[key % self._length] = value


class ObjectAttribute(BufferAttribute):
    def __init__(self, **kwargs):
        BufferAttribute.__init__(self, **kwargs)

        self._data = IPC.Manager.list([None] * self._length)

    def _read(self, start_idx, end_idx, use_lock):
        """use_lock not used, because manager handles locking"""
        if start_idx >= 0:
            return self._data[start_idx:end_idx]
        else:
            return self._data[start_idx:] + self._data[:end_idx]

    def write(self, value):
        internal_idx = self._index % self._length

        # Set time for this entry
        self._time[internal_idx] = self._buffer.get_time()

        # Set data
        self._data[internal_idx] = value

    def __setitem__(self, key, value):
        self._data[key % self._length] = value


class RingBuffer:

    attr_prefix = '_attr_'

    def __init__(self):
        self.__dict__['current_idx'] = mp.Value(ctypes.c_uint64)

    def build(self):
        for attr_name, obj in self.__dict__.items():
            if not (attr_name.startswith('_attr_')):
                continue

            obj.build()

    def list_attributes(self):
        return [attr_name.replace(self.attr_prefix, '') for attr_name
                in self.__dict__ if attr_name.startswith(self.attr_prefix)]

    def set_time(self, time):
        self.__dict__['current_time'] = time

    def get_time(self):
        return self.__dict__['current_time']

    def set_index(self, new_idx):
        self.__dict__['current_idx'].value = new_idx

    def get_index(self):
        return self.__dict__['current_idx'].value

    def read(self, attr_name, *args, **kwargs):
        return getattr(self, attr_name).read(*args, **kwargs)

    def __setattr__(self, key, value):
        assert issubclass(value.__class__, BufferAttribute), f'{key} must be BufferAttribute'
        value.set_buffer(self)
        self.__dict__[f'{self.attr_prefix}{key}'] = value

    def __getattr__(self, item) -> BufferAttribute:
        # Return
        try:
            return self.__dict__[f'_attr_{item}'].get(self.get_index())
        except:
            # Fallback for serialization
            self.__getattribute__(item)

    def next(self):
        self.set_time(time.time())
        self.set_index(self.get_index() + 1)
