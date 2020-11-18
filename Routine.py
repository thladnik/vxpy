"""
MappApp ./Routine.py - Routine wrapper, abstract routine and ring buffer implementations.
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
import ctypes
import h5py
import multiprocessing as mp
import numpy as np
import os
import time
from typing import Union, Iterable

import Config
import Def
import IPC
import Logging
import Process

################################
## Routine wrapper class

class Routines:
    """Wrapper class for routines
    """
    # TODO: Routines class may be moved into Process.AbstractProcess in future?

    process: Process.AbstractProcess = None

    def __init__(self, name, routines=None):
        self.name = name
        self._routine_paths = dict()
        self._routines = dict()
        self.h5_file: h5py.File = None
        self.current_group: h5py.Group = None
        self.compression_args: dict = None

        ### Automatically add routines, if provided
        if not(routines is None) and isinstance(routines, dict):
            for routine_file, routine_list in routines.items():
                module = __import__('{}.{}.{}'.format(Def.Path.Routines,
                                                      self.name.lower(),
                                                      routine_file),
                                    fromlist=routine_list)
                for routine_name in routine_list:
                    self.add_routine(getattr(module, routine_name))


    def create_hooks(self, process):
        """Provide process instance with callback signatures for RPC.

        Method is called by process immediately after initialization on fork.
        For each method listed in the routines 'exposed' attribute,
        a callback reference is provided to the process instance.
        This makes routine methods accessible via RPC.

        :arg process: instance object of the current process
        """

        self.process = process

        for name, routine in self._routines.items():
            for fun in routine.exposed:
                fun_str = fun.__qualname__
                self.process.register_rpc_callback(routine, fun_str, fun)

    def initialize_buffers(self):
        """Initialize each buffer after subprocess fork.

        This call the RingBuffer.initialize method in each routine which can
        be used for operations that have to happen
        after forking the process (e.g. ctype mapped numpy arrays)
        """

        for name, routine in self._routines.items():
            routine.buffer.build()

    def add_routine(self, routine_cls, **kwargs):
        """To be called by Controller.

        Creates an instance of the provided routine class (which
        has to happen before subprocess fork).

        :arg routine_cls: class object of routine
        :**kwargs: keyword arguments to be passed upon initialization of routine
        """

        if routine_cls.__name__ in self._routine_paths:
            raise Exception(
                f'Routine \"{routine_cls.__name__}\" exists already'
                f' for path \"{self._routine_paths[routine_cls.__name__]}\"'
                f'Unable to add routine of same name from path \"{routine_cls.__module__}\"')

        self._routine_paths[routine_cls.__name__] = routine_cls.__module__
        self._routines[routine_cls.__name__]: AbstractRoutine = routine_cls(self, **kwargs)

    def get_buffer(self, routine_cls):
        if isinstance(routine_cls, str):
            routine_name = routine_cls
        else:
            routine_name = routine_cls.__name__

        assert routine_name in self._routines, f'Routine {routine_name} is not set in {self.name}'

        return self._routines[routine_name].buffer

    def update(self, *args, **kwargs):

        if not(bool(args)) and not(bool(kwargs)):
            return

        for name in self._routines:
            # Advance buffer
            self._routines[name].buffer.next()
            # Update the data in buffer
            self._routines[name].update(*args, **kwargs)
            # Stream new routine computation results to file (if active)
            self._routines[name].stream_to_file(self.get_container())

    def set_record_group(self, group_name):
        if self.h5_file is None:
            return#, 'Unable to create record group outside of h5 file context'

        self.current_group = self.h5_file.require_group(group_name)

    def read(self, attr_name, routine_name=None, **kwargs):
        """Read shared attribute from buffer.

        :param attr_name: string name of attribute or string format <attrName>/<bufferName>
        :param routine_name: name of buffer; if None, then attrName has to be <attrName>/<bufferName>

        :return: value of the buffer
        """

        if routine_name is None:
            parts = attr_name.split('/')
            attr_name = parts[1]
            routine_name = parts[0]

        return self._routines[routine_name].read(attr_name, **kwargs)

    def routines(self):
        return self._routines

    def get_container(self) -> Union[h5py.File, None]:
        """Method checks if application is currently recording.
        Opens and closes output file if necessary and returns either a file/group object or a None.
        """

        # If recording is running and file is open: return file object
        if IPC.Control.Recording[Def.RecCtrl.active] and not(self.h5_file is None):
            if self.current_group is None:
                return self.h5_file
            else:
                return self.current_group

        # If recording is running and file not open: open file and return file object
        elif IPC.Control.Recording[Def.RecCtrl.active] and self.h5_file is None:
            # If output folder is not set: log warning and return None
            if not(bool(IPC.Control.Recording[Def.RecCtrl.folder])):
                Logging.write(Logging.WARNING, 'Recording has been started but output folder is not set.')
                return None

            # If output folder is set: open file
            filepath = os.path.join(Config.Recording[Def.RecCfg.output_folder],
                                    IPC.Control.Recording[Def.RecCtrl.folder],
                                    '{}.hdf5'.format(self.name))

            # Open new file
            Logging.write(Logging.DEBUG, 'Open new file {}'.format(filepath))
            self.h5_file = h5py.File(filepath, 'w')

            # Set compression
            compr_method = IPC.Control.Recording[Def.RecCtrl.compression_method]
            compr_opts = IPC.Control.Recording[Def.RecCtrl.compression_opts]

            self.compression_args = dict()
            if compr_method is not None:
                self.compression_args = {'compression': compr_method, **compr_opts}

            return self.h5_file

        # Recording is not running at the moment
        else:

            # If current recording folder is still set: recording is paused
            if bool(IPC.Control.Recording[Def.RecCtrl.folder]):
                # Do nothing; return nothing
                return None

            # If folder is not set anymore
            else:
                # Close open file (if open)
                if not(self.h5_file is None):
                    self.h5_file.close()
                    self.h5_file = None
                    self.current_group = None
                # Return nothing
                return None


################################
# Abstract Routine class

class AbstractRoutine:

    def __init__(self, _bo):
        self._bo = _bo

        # List of methods open to rpc calls
        self.exposed = list()

        # List of required device names
        self.required = list()

        # Default ring buffer instance for routine
        self.buffer: RingBuffer = RingBuffer()

    def _compute(self, *args, **kwargs):
        """Compute method is called on data updates (in the producer process).
        Every buffer needs to implement this method."""
        raise NotImplementedError('_compute not implemented in {}'.format(self.__class__.__name__))

    def _out(self):
        """Method may be reimplemented. Can be used to alter the output to file.
        If this buffer is going to be used for recording data, this method HAS to be implemented.
        Implementations of this method should yield a tuple
        with (attribute name, time, attribute value)
        """
        # TODO: add default behavior instead of raising exception?
        raise NotImplementedError('method _out not implemented in {}'.format(self.__class__.__name__))

    def read(self, attr_name, *args, **kwargs):
        return self.buffer.read(attr_name, *args, **kwargs)

    def update(self, *args, **kwargs):
        """Method is called on every iteration of the producer.

        :param data: input data to be updated
        """

        self._compute(*args, **kwargs)

    def _append_data(self, grp, key, value):

        # Convert and determine dshape/dtype
        value = np.asarray(value) if isinstance(value, (list, tuple)) else value
        dshape = value.shape if isinstance(value, np.ndarray) else (1,)
        dtype = value.dtype if isinstance(value, np.ndarray) else type(value)

        # Create dataset if it doesn't exist
        if not(key in grp):
            try:
                Logging.write(Logging.INFO, 'Create record dset "{}/{}"'.format(grp.name, key))
                grp.create_dataset(key,
                                   shape=(0, *dshape,),
                                   dtype=dtype,
                                   maxshape=(None, *dshape,),
                                   chunks=(1, *dshape,),
                                   **self._bo.compression_args)
                # TODO: add compression option to recording controls + GUI
            except Exception as exc:
                import traceback
                Logging.write(Logging.WARNING,
                              f'Failed to create record dset "{grp.name}/{key}"')
                traceback.print_exc()

        dset = grp[key]

        # Resize dataset and append new value
        dset.resize((dset.shape[0] + 1, *dshape))
        dset[dset.shape[0] - 1] = value

    def stream_to_file(self, container: Union[h5py.File, h5py.Group, None]):
        # Set id of current buffer e.g. "Camera/FrameBuffer"
        bufferName = self.__class__.__name__

        # If no file object was provided or this particular buffer is not supposed to stream to file: return
        if container is None or not('{}/{}'.format(self._bo.name, bufferName) in Config.Recording[Def.RecCfg.routines]):
            return None

        # Each buffer writes to it's own group
        if not(bufferName in container):
            Logging.write(Logging.INFO, 'Create record group {}'.format(bufferName))
            container.create_group(bufferName)
        grp = container[bufferName]

        # Iterate over data in group (buffer)
        for key, time, value in self._out():

            # On datasets:
            ## TODO: handle changing dataset sizes (e.g. rect ROIs which are slightly altered during rec)
            ###
            # NOTE ON COMPRESSION FOR FUTURE:
            # GZIP: common, but slow
            # LZF: fast, but only natively implemented in python h5py (-> can't be read by HDF Viewer)
            ###
            self._append_data(grp, key, value)
            self._append_data(grp, '{}_time'.format(key), time)


import ctypes
import time
from typing import List, Tuple, Union

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

    def __init__(self, size, dtype, chunked=False, chunk_size=None, **kwargs):
        BufferAttribute.__init__(self, **kwargs)

        assert isinstance(size, tuple), 'size must be tuple with dimension sizes'
        assert isinstance(dtype, tuple), 'dtype must be tuple with (ctype,np-type)'
        assert isinstance(chunked, bool), 'chunked has to be bool'
        assert isinstance(chunk_size, int) or chunk_size is None, 'chunk_size must be int or None'

        self._size = size
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
            init = int(np.product((self._chunk_size,) + self._size))
            self._raw: List[mp.Array] = list()
            for i in range(self._chunk_num):
                self._raw.append(mp.Array(self._dtype[0], init))
            self._data: List[np.ndarray] = list()
        else:
            init = int(np.product((self._length,) + self._size))
            self._raw: mp.Array = mp.Array(self._dtype[0], init)
            self._data: np.ndarray = None

    def _build_array(self, raw, length):
        np_array = np.frombuffer(raw.get_obj(), self._dtype[1])
        return np_array.reshape((length,) + self._size)

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
