"""
MappApp ./Buffer.py - Buffer-objects which are used for inter-process-communication and save-to-file operations
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
from time import perf_counter, time
from typing import Union, Iterable

import Config
import Def
import IPC
import Logging

################################
## Buffer Object

class Routines:
    """Buffer Object: wrapper for routines
    """

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
        for name, routine in self._routines.items():
            for method in routine.exposed:
                fun_path = method.__qualname__.split('.')
                fun_str = '_'.join(fun_path)
                if not(hasattr(instance, fun_str)):
                    # This is probably my weirdest programming construct yet...
                    setattr(instance, fun_str, lambda *args, **kwargs: method(routine, *args, **kwargs))
                else:
                    print('Oh no, routine method already set. NOT GOOD!')

    def addBuffer(self, routine, **kwargs):
        """To be called by controller (initialization of routines has to happen in parent process)"""
        self._routines[routine.__name__] = routine(self, **kwargs)

    def update(self, frame):
        for name in self._routines:
            self._routines[name].update(frame)
            self._routines[name].streamToFile(self._openFile())

    def readAttribute(self, attr_name, routine_name=None):
        """Read shared attribute from buffer.

        :param attr_name: string name of attribute or string format <attrName>/<bufferName>
        :param routine_name: name of buffer; if None, then attrName has to be <attrName>/<bufferName>

        :return: value of the buffer
        """
        if routine_name is None:
            parts = attr_name.split('/')
            attr_name = parts[1]
            routine_name = parts[0]

        return self._routines[routine_name].read(attr_name)

    def routines(self):
        return self._routines

    def _openFile(self) -> Union[h5py.File, None]:
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
            filepath = os.path.join(Def.Path.Output,
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
## Abstract Buffer class

class AbstractRoutine:

    def __init__(self, _bo):
        self._bo = _bo

        self.exposed = list()
        self.buffer = RingBuffer()
        self.currentTime = time()

    def _compute(self, data):
        """Compute method is called on data updates (so in the producer process).
        Every buffer needs to reimplement this method."""
        raise NotImplementedError('_compute not implemented in {}'.format(self.__class__.__name__))

    def _out(self):
        """Method may be reimplemented. Can be used to alter the output to file.
        If this buffer is going to be used for recording data, this method HAS to be implemented.
        Implementations of this method should yield a tuple (attribute name, attribute value) to be written to file

        By default this returns the current attribute name -> attribute value pair.
        """
        raise NotImplemented('method _out not implemented in {}'.format(self.__class__.__name__))

    def read(self, attr_name):
        ### Return
        return self.buffer.read(attr_name)

    def update(self, data):
        """Method is called on every iteration of the producer.

        :param data: input data to be updated
        """

        ### Call compute method
        self._compute(data.copy())  # Copy to avoid detrimental pythonic side effects
        self.buffer.next()

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
        if file is None or not('{}/{}'.format(self._bo.name, bufferName) in Config.Recording[Def.RecCfg.buffers]):
            return None

        ## Each buffer writes to it's own group
        if not(bufferName in file):
            Logging.write(logging.INFO, 'Create record group {}'.format(bufferName))
            file.create_group(bufferName)
        grp = file[bufferName]

        ### Current time for entry
        self.currentTime = time()

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
            self._appendData(grp, '{}_time'.format(key), self.currentTime)

class RingBuffer:

    def __init__(self, buffer_length=1000):
        self.__dict__['_bufferLength'] = buffer_length

        self.__dict__['_attributeList'] = list()
        ### Index that points to the record which is currently being updated
        self.__dict__['_currentIdx'] = IPC.Manager.Value(ctypes.c_int64, 0)

    def next(self):
        self.__dict__['_currentIdx'].value += 1

    def index(self):
        return self.__dict__['_currentIdx'].value

    def length(self):
        return self.__dict__['_bufferLength']

    def read(self, name):
        """Read **by consumer**: return last complete record (_currentIdx-1)"""
        return self.__dict__['_data_{}'.format(name)][(self.index()-1) % self.length()]

    def __setattr__(self, name, value):
        if not('_data_{}'.format(name) in self.__dict__):
            self.__dict__['_attributeList'].append(name)
            self.__dict__['_data_{}'.format(name)] = IPC.Manager.list(self.length() * [None])
            self.__dict__['_info_{}'.format(name)] = value
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