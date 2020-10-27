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
        self.h5File = None
        self._routine_paths = dict()
        self._routines = dict()

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
        self._routines[routine_cls.__name__] = routine_cls(self, **kwargs)

    def get_buffer(self, routine_cls):
        if isinstance(routine_cls, str):
            routine_name = routine_cls
        else:
            routine_name = routine_cls.__name__

        assert routine_name in self._routines, f'Routine {routine_name} is not set'
        return self._routines[routine_name].buffer

    def update(self, *args, **kwargs):

        if not(bool(args)) and not(bool(kwargs)):
            return

        #t = time.time()
        for name in self._routines:
            # Advance buffer
            self._routines[name].buffer.next()
            # Set time for current iteration
            #last_idx, last_t = self._routines[name].buffer.time.read()
            #if last_t[0] is not None and last_t > t:
            #    print('AAAAAAAAH')
            #self._routines[name].buffer.time.write(self._routines[name].buffer.get_time())
            # Update the data in buffer
            self._routines[name].update(*args, **kwargs)
            # Stream new routine computation results to file (if active)
            self._routines[name].stream_to_file(self.handleFile())

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

    def handleFile(self) -> Union[h5py.File, None]:
        """Method checks if application is currently recording.
        Opens and closes output file if necessary and returns either a file object or a None value.
        """

        ### If recording is running and file is open: return file object
        if IPC.Control.Recording[Def.RecCtrl.active] and not(self.h5File is None):
            return self.h5File

        ### If recording is running and file not open: open file and return file object
        elif IPC.Control.Recording[Def.RecCtrl.active] and self.h5File is None:
            ## If output folder is not set: log warning and return None
            if not(bool(IPC.Control.Recording[Def.RecCtrl.folder])):
                Logging.write(Logging.WARNING, 'Recording has been started but output folder is not set.')
                return None

            ### If output folder is set: open file
            filepath = os.path.join(Config.Recording[Def.RecCfg.output_folder],
                                    IPC.Control.Recording[Def.RecCtrl.folder],
                                    '{}.hdf5'.format(self.name))

            Logging.write(Logging.DEBUG, 'Open new file {}'.format(filepath))
            self.h5File = h5py.File(filepath, 'w')

            return self.h5File

        ### Recording is not running at the moment
        else:

            ## If current recording folder is still set: recording is paused
            if bool(IPC.Control.Recording[Def.RecCtrl.folder]):
                ## Do nothing; return nothing
                return None

            ## If folder is not set anymore
            else:
                # Close open file (if open)
                if not(self.h5File is None):
                    self.h5File.close()
                    self.h5File = None
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
        self.buffer = RingBuffer()
        # Set time attribute by default on all buffers
        #self.buffer.time = ObjectAttribute()

        # Set time
        #self.currentTime = time.time()


    def _compute(self, *args, **kwargs):
        """Compute method is called on data updates (so in the producer process).
        Every buffer needs to implement this method."""
        raise NotImplementedError('_compute not implemented in {}'.format(self.__class__.__name__))

    def _out(self):
        """Method may be reimplemented. Can be used to alter the output to file.
        If this buffer is going to be used for recording data, this method HAS to be implemented.
        Implementations of this method should yield a tuple (attribute name, attribute value) to be written to file

        By default this returns the current attribute name -> attribute value pair.
        """
        raise NotImplemented('method _out not implemented in {}'.format(self.__class__.__name__))

    def read(self, attr_name, *args, **kwargs):
        return self.buffer.read(attr_name, *args, **kwargs)

    def update(self, *args, **kwargs):
        """Method is called on every iteration of the producer.

        :param data: input data to be updated
        """

        self._compute(*args, **kwargs)


    def _append_data(self, grp, key, value):

        ## Convert and determine dshape/dtype
        value = np.asarray(value) if isinstance(value, list) else value
        dshape = value.shape if isinstance(value, np.ndarray) else (1,)
        dtype = value.dtype if isinstance(value, np.ndarray) else type(value)

        ## Create dataset if it doesn't exist
        if not(key in grp):
            try:
                Logging.write(Logging.INFO, 'Create record dset "{}/{}"'.format(grp.name, key))
                grp.create_dataset(key,
                                   shape=(0, *dshape,),
                                   dtype=dtype,
                                   maxshape=(None, *dshape,),
                                   chunks=(1, *dshape,), )  # compression='lzf')
            except:
                Logging.write(Logging.WARNING, 'Failed to create record dset "{}/{}"'.format(grp.name, key))

            grp[key].attrs.create('Position', self.currentTime, dtype=np.float64)

        dset = grp[key]

        ## Resize dataset and append new value
        dset.resize((dset.shape[0] + 1, *dshape))
        dset[dset.shape[0] - 1] = value

    def stream_to_file(self, file: Union[h5py.File, None]):
        ### Set id of current buffer e.g. "Camera/FrameBuffer"
        bufferName = self.__class__.__name__

        ### If no file object was provided or this particular buffer is not supposed to stream to file: return
        if file is None or not('{}/{}'.format(self._bo.name, bufferName) in Config.Recording[Def.RecCfg.routines]):
            return None

        ## Each buffer writes to it's own group
        if not(bufferName in file):
            Logging.write(Logging.INFO, 'Create record group {}'.format(bufferName))
            file.create_group(bufferName)
        grp = file[bufferName]

        ## Iterate over data in group (buffer)
        for key, value in self._out():

            ## On datasets:
            ## TODO: handle changing dataset sizes (e.g. rect ROIs which are slightly altered during rec)
            ###
            # NOTE ON COMPRESSION FOR FUTURE:
            # GZIP: common, but slow
            # LZF: fast, but only natively implemented in python h5py (-> can't be read by HDF Viewer)
            ###

            self._append_data(grp, key, value)
            self._append_data(grp, '{}_time'.format(key), self.buffer.time)


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
        internal_idx = self._index % self._length
        start_idx = internal_idx-last
        return self._get_times(start_idx, internal_idx)

    def get(self, current_idx):
        self._index = current_idx
        return self

    def read(self, last=-1):
        raise NotImplementedError(f'Method read not implemented in {self.__class__}')

    def write(self, value):
        raise NotImplementedError(f'Method write not implemented in {self.__class__}')

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

    def read(self, last=1, use_lock=True) -> Tuple[List, List, Union[None,np.ndarray]]:
        assert last < self._length, 'Trying to read more values than stored in buffer'

        internal_idx = self._index % self._length

        if self._index <= last:
            return [-1], [-1], None

        start_idx = internal_idx - last

        # Read without lock
        return self._get_index_list(last), self.get_times(last), self._read(start_idx, internal_idx, use_lock)

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

    def read(self, last=1) -> Tuple[List, List, List]:
        internal_idx = self._index % self._length

        start_idx = internal_idx - last
        if start_idx >= 0:
            return self._get_index_list(last), self.get_times(last), self._data[start_idx:internal_idx]
        else:
            return self._get_index_list(last), self.get_times(last), self._data[start_idx:] + self._data[:internal_idx]

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

class BufferDTypes:
    ### Unsigned integers
    uint8 = (ctypes.c_uint8, np.uint8)
    uint16 = (ctypes.c_uint16, np.uint16)
    uint32 = (ctypes.c_uint32, np.uint32)
    uint64 = (ctypes.c_uint64, np.uint64)
    ### Signed integers
    int8 = (ctypes.c_int8, np.int8)
    int16 = (ctypes.c_int16, np.int16)
    int32 = (ctypes.c_int32, np.int32)
    int64 = (ctypes.c_int64, np.int64)
    ### Floating point numbers
    float32 = (ctypes.c_float, np.float32)
    float64 = (ctypes.c_double, np.float64)
    ### Misc types
    dictionary = (dict, )


class RingBufferMEEEEH:
    """A simple ring buffer model. """

    def __init__(self, buffer_length=1000):
        self.__dict__['_bufferLength'] = buffer_length

        self.__dict__['_attributeList'] = list()
        ### Index that points to the record which is currently being updated
        self.__dict__['_currentIdx'] = IPC.Manager.Value(ctypes.c_int64, 0)

    def initialize(self):
        for attr_name in self.__dict__['_attributeList']:
            shape = self.__dict__['_shape_{}'.format(attr_name)]
            if shape is None or shape == (1,):
                continue

            data = np.frombuffer(self.__dict__['_dbase_{}'.format(attr_name)], self.__dict__['_dtype_{}'.format(attr_name)][1]).reshape((self.length(), *shape))
            self.__dict__['_data_{}'.format(attr_name)] = data

    def next(self):
        self.__dict__['_currentIdx'].value += 1

    def index(self):
        return self.__dict__['_currentIdx'].value

    def length(self):
        return self.__dict__['_bufferLength']

    def read(self, attr_name, last=1, last_idx=None):
        """Read **by consumer**: return last complete record(s) (_currentIdx-1)
        Returns a tuple of (index, record_dataset)
                        or (indices, record_datasets)
        """
        if not(last_idx is None):
            last = self.index()-last_idx

        ### Set index relative to buffer length
        list_idx = (self.index()) % self.length()

        ### One record
        if last == 1:
            idx_start = list_idx-1
            idx_end = None
            idcs = self.index()-1

        ### Multiple record
        elif last > 1:
            if last > self.length():

                raise Exception('Trying to read more records than stored in buffer. '
                                'Attribute \'{}\''.format(attr_name))

            idx_start = list_idx-last
            idx_end = list_idx

            idcs = list(range(self.index()-last, self.index()))

        ### No entry: raise exception
        else:
            Logging.write(Logging.WARNING, 'Cannot read {} from buffer. Argument last = {}'.format(attr_name, last))
            return None, None
            #raise Exception('Smallest possible record set size is 1')

        if isinstance(attr_name, str):
            return idcs, self._read(attr_name, idx_start, idx_end)
        else:
            return idcs, {n: self._read(n, idx_start, idx_end) for n in attr_name}

    def _createAttribute(self, attr_name, dtype, shape=None):
        self.__dict__['_attributeList'].append(attr_name)
        if shape is None or shape == (1,):
            self.__dict__['_data_{}'.format(attr_name)] = IPC.Manager.list(self.length() * [None])
        else:
            ### *Note to future self*
            # ALWAYS try to use shared arrays instead of managed lists, etc for stuff like this
            # Performance GAIN in the particular example of the Camera process pushing
            # 720x750x3 uint8 images through the buffer is close to _100%_ (DOUBLING of performance)\\ TH 2020-07-16
            self.__dict__['_dbase_{}'.format(attr_name)] = mp.RawArray(dtype[0], int(np.prod([self.length(), *shape])))
            self.__dict__['_data_{}'.format(attr_name)] = None
        self.__dict__['_dtype_{}'.format(attr_name)] = dtype
        self.__dict__['_shape_{}'.format(attr_name)] = shape

    def _read(self, name, idx_start, idx_end):

        ### Return single record
        if idx_end is None:
            return self.__dict__['_data_{}'.format(name)][idx_start]

        ### Return multiple records
        if idx_start >= 0:
            return self.__dict__['_data_{}'.format(name)][idx_start:idx_end]
        else:
            # TODO: not possible to handle slices of shared arrays with this!
            return self.__dict__['_data_{}'.format(name)][idx_start:] \
                   + self.__dict__['_data_{}'.format(name)][:idx_end]

    def __setattr__(self, name, value):
        if not('_data_{}'.format(name) in self.__dict__):
            if isinstance(value, tuple):
                self._createAttribute(name, *value)
            else:
                raise TypeError('Class {} needs to be provided a tuple '
                                'for initialization of new attribute'.format(self.__class__.__name__))
        else:
            # TODO: add checks?
            self.__dict__['_data_{}'.format(name)][self.index() % self.length()] = value

    def __getattr__(self, name):
        """Get current record"""
        try:
            return self.__dict__['_data_{}'.format(name)][(self.index()) % self.length()]
        except:
            ### Fallback to parent is essential for pickling!
            super().__getattribute__(name)