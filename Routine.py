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
import logging
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

    process : Process.AbstractProcess = None

    def __init__(self, name):
        self.name = name
        self.h5File = None
        self.vidFile = None

        self._routines = dict()

    def createHooks(self, instance):
        """Method is called by process immediately after initialization.
        For each method listed in the routines 'exposed' attribute, it
        sets a reference on the process instance to said routine method,
        thus making it accessible via RPC calls.
        Attribute reference: <Buffer name>_<Buffer method name>

        :arg instance: instance object of the current process
        """
        self.process = instance

        for name, routine in self._routines.items():
            for method in routine.exposed:
                fun_path = method.__qualname__.split('.')
                fun_str = '_'.join(fun_path)
                if not(hasattr(instance, fun_str)):
                    # This is probably my weirdest programming construct yet...
                    setattr(instance, fun_str, lambda *args, **kwargs: method(routine, *args, **kwargs))
                else:
                    print('Oh no, routine method already set. NOT GOOD!')

    def initializeBuffers(self):
        for name, routine in self._routines.items():
            routine.buffer.initialize()

    def addRoutine(self, routine, **kwargs):
        """To be called by controller (initialization of routines has to happen in parent process)"""
        self._routines[routine.__name__] = routine(self, **kwargs)

    def update(self, data):
        t = time.time()#perf_counter() - self.process.process_sync_time
        for name in self._routines:
            ### Set time for current iteration
            self._routines[name].buffer.time = t
            ### Update the data in buffer
            self._routines[name].update(data)
            ### Stream new routine computation results to file (if active)
            self._routines[name].streamToFile(self.handleFile())
            # Advance the associated buffer
            self._routines[name].buffer.next()

    def readAttribute(self, attr_name, routine_name=None, **kwargs):
        """Read shared attribute from buffer.

        :param attr_name: string name of attribute or string format <attrName>/<bufferName>
        :param routine_name: name of buffer; if None, then attrName has to be <attrName>/<bufferName>
                                routine_name can be either str or list[str]

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
                Logging.write(logging.WARNING, 'Recording has been started but output folder is not set.')
                return None

            ### If output folder is set: open file
            filepath = os.path.join(Config.Recording[Def.RecCfg.output_folder],
                                    IPC.Control.Recording[Def.RecCtrl.folder],
                                    '{}.hdf5'.format(self.name))

            Logging.write(logging.DEBUG, 'Open new file {}'.format(filepath))
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
## Abstract Routine class

class AbstractRoutine:

    def __init__(self, _bo):
        self._bo = _bo

        self.exposed = list()
        self.buffer = RingBuffer()
        self.currentTime = time.time()

        ### Set time attribute by default on all buffers
        self.buffer.time = (BufferDTypes.float64, )

    def _compute(self, data):
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

    def update(self, data):
        """Method is called on every iteration of the producer.

        :param data: input data to be updated
        """

        ### Set time for current iteration
        #self.buffer.time = time()
        ### Call compute method
        #self._compute(data.copy())  # Copy to avoid detrimental pythonic side effects
        #                            (TODO: I don't think this copying works as intended, yet)
        if data is None:
            return

        self._compute(data)


    def _appendData(self, grp, key, value):

        ## Convert and determine dshape/dtype
        value = np.asarray(value) if isinstance(value, list) else value
        dshape = value.shape if isinstance(value, np.ndarray) else (1,)
        dtype = value.dtype if isinstance(value, np.ndarray) else type(value)

        ## Create dataset if it doesn't exist
        if not(key in grp):
            try:
                Logging.write(logging.INFO, 'Create record dset "{}/{}"'.format(grp.name, key))
                grp.create_dataset(key,
                                   shape=(0, *dshape,),
                                   dtype=dtype,
                                   maxshape=(None, *dshape,),
                                   chunks=(1, *dshape,), )  # compression='lzf')
            except:
                Logging.write(logging.WARNING, 'Failed to create record dset "{}/{}"'.format(grp.name, key))

            grp[key].attrs.create('Position', self.currentTime, dtype=np.float64)

        dset = grp[key]

        ## Resize dataset and append new value
        dset.resize((dset.shape[0] + 1, *dshape))
        dset[dset.shape[0] - 1] = value

    def streamToFile(self, file: Union[h5py.File, None]):
        ### Set id of current buffer e.g. "Camera/FrameBuffer"
        bufferName = self.__class__.__name__

        ### If no file object was provided or this particular buffer is not supposed to stream to file: return
        if file is None or not('{}/{}'.format(self._bo.name, bufferName) in Config.Recording[Def.RecCfg.routines]):
            return None

        ## Each buffer writes to it's own group
        if not(bufferName in file):
            Logging.write(logging.INFO, 'Create record group {}'.format(bufferName))
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

            self._appendData(grp, key, value)
            self._appendData(grp, '{}_time'.format(key), self.buffer.time)


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


class RingBuffer:
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

    def read(self, name, last=1, last_idx=None):
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
                                'Attribute \'{}\''.format(name))

            idx_start = list_idx-last
            idx_end = list_idx

            idcs = list(range(self.index()-last, self.index()))

        ### No entry: raise exception
        else:
            raise Exception('Smallest possible record set size is 1')

        if isinstance(name, str):
            return idcs, self._read(name, idx_start, idx_end)
        else:
            return idcs, {n: self._read(n, idx_start, idx_end) for n in name}

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
            return self.__dict__['_data_{}'.format(name)][idx_start:] \
                   + self.__dict__['_data_{}'.format(name)][:idx_end]

    def __setattr__(self, name, value):
        if not('_data_{}'.format(name) in self.__dict__):
            self._createAttribute(name, *value)
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