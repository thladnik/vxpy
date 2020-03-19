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

import h5py
import logging
import multiprocessing as mp
import numpy as np
import os
from time import perf_counter, time
from typing import Union

import Config
import Definition
import IPC
import Logging

################################
## Buffer Object

class BufferObject:
    """Buffer Object: wrapper for buffers
    """

    def __init__(self, name):
        self.name = name
        self.h5File = None
        self.vidFile = None

        self._buffers = dict()
        self._npBuffers = dict()


    def addBuffer(self, buffer, **kwargs):
        """To be called by controller (initialization of buffers has to happen in parent process)"""
        self._buffers[buffer.__name__] = buffer(self, **kwargs)

    def constructBuffers(self, _reconstruct=False):
        """Deprecated -> remove"""
        Logging.write(logging.WARNING, 'constructBuffer method for BufferObject is deprecated and will be removed.')

    def update(self, frame):
        for name in self._buffers:
            self._buffers[name].update(frame)
            self._buffers[name].streamToFile(self._openFile())

    def readAttribute(self, attrName, bufferName=None):
        """Read shared attribute from buffer.

        :param attrName: string name of attribute or string format <attrName>/<bufferName>
        :param bufferName: name of buffer; if None, then attrName has to be <attrName>/<bufferName>

        :return: value of the buffer
        """
        if bufferName is None:
            parts = attrName.split('/')
            attrName = parts[1]
            bufferName = parts[0]

        return self._buffers[bufferName].read(attrName)

    def buffers(self):
        return self._buffers

    def _openFile(self) -> Union[h5py.File, None]:
        """Method checks if application is currently recording.
        Opens and closes output file if necessary and returns either a file object or a None value.
        """

        ### If recording is running and file is open: return file object
        if Config.Recording[Definition.Recording.active] and not(self.h5File is None):
            return self.h5File

        ### If recording is running and file not open: open file and return file object
        elif Config.Recording[Definition.Recording.active] and self.h5File is None:
            ## If output folder is not set: log warning and return None
            if not(bool(Config.Recording[Definition.Recording.current_folder])):
                Logging.write(logging.WARNING, 'Recording has been started but output folder is not set.')
                return None

            ### If output folder is set: open file
            filepath = os.path.join(Definition.Path.Output,
                                    Config.Recording[Definition.Recording.current_folder],
                                    '{}.hdf5'.format(self.name))
            Logging.write(logging.DEBUG, 'Open new file {}'.format(filepath))
            self.h5File = h5py.File(filepath, 'w')

            return self.h5File

        ### If recording is not running, but file is still open: close file object
        elif not(Config.Recording[Definition.Recording.active]) and not(self.h5File is None):
            self.h5File.close()
            self.h5File = None

        return None


################################
## Abstract Buffer class

class AbstractBuffer:

    def __init__(self, _bo):
        self._bo = _bo
        self.fileStruct = dict()

        self._built = False
        self._sharedAttributes = dict()

    def _compute(self, data):
        """Compute method is called on data updates (so in the producer process).
        Every buffer needs to reimplement this method."""
        NotImplementedError('_compute not implemented in {}'.format(self))

    def _out(self):
        """Method can be reimplemented. Can be used to alter the output to file.
        Implementations of this method should yield a tuple (attribute name, attribute value) to be written to file

        By default this returns the current attribute name -> attribute value pair.
        """

        for attrName in self._sharedAttributes:
            if hasattr(self.read(attrName), 'value'):
                yield self.read(attrName).value
            else:
                yield self.read(attrName)

    def read(self, attrName):
        ### Call build function
        self._build()

        ### Return
        return getattr(self, attrName)

    def update(self, data):
        """Method is called on every iteration of the producer.

        :param data: input data to be updated
        """

        ### Call compute method
        self._compute(data.copy())  # Copy to avoid detrimental pythonic side effects

        ### Call buffer objects save-to-file method
        #self._bo._streamToFile(self)

    def sharedAttribute(self, attrName, attrType, *args, **kwargs):
        ### Create shared attribute
        if not(attrName in self._sharedAttributes):
            self._sharedAttributes[attrName] = dict(type=attrType)

            if attrType == 'Array':
                dtype = args[0]
                dshape = args[1]
                self._sharedAttributes[attrName]['dtype'] = dtype
                self._sharedAttributes[attrName]['dshape'] = dshape
                self._sharedAttributes[attrName]['cArr'] = mp.Array(dtype, int(np.prod(dshape)))

            else:
                ### Create shared attribute object
                self._sharedAttributes[attrName]['obj'] = getattr(IPC.Manager, attrType)(*args, **kwargs)


    def _build(self):
        """Build function which should be called at the start of every function in a Buffer implementation.
        Can be used to handle build events which must take place in the child processes of the Controller.

        Sets every shared attribute to the instance for access via self.<shared attribute>

        E.g. Ctype shared arrays of the multiprocessing module (type == 'Array') may be bound to numpy arrays
        for convenient and fast integration into the code.

        !!! This method is only executed ONCE per child process
        and it may under NO circumstances be executed in the Controller !!!
        "Build in Controller" == "Buffer not working"
        """

        ### Check if function has been called before in this process
        if self._built:
            return

        ### Iterate through all attributes
        for attrName, attrData in self._sharedAttributes.items():
            if attrData['type'] == 'Array':
                self._sharedAttributes[attrName]['obj'] = np.ctypeslib.as_array(self._sharedAttributes[attrName]['cArr'].get_obj())
                self._sharedAttributes[attrName]['obj'] = self._sharedAttributes[attrName]['obj'].reshape(self._sharedAttributes[attrName]['dshape'])

            ### Set shared attribute for instance (so it may be accessed conveniently through self.<attrName>)
            setattr(self, attrName, self._sharedAttributes[attrName]['obj'])

        ### Mark buffer for this instance as built
        self._built = True


    def streamToFile(self, file: Union[h5py.File, None]):
        ### Set id of current buffer e.g. "Camera/FrameBuffer"
        bufferName = self.__class__.__name__

        ### If no file object was provided or this particular buffer is not supposed to stream to file: return
        if file is None or not('{}/{}'.format(self._bo.name, bufferName) in Config.Recording[Definition.Recording.buffers]):
            return None

        ## Each buffer writes to it's own group
        if not(bufferName in file):
            Logging.write(logging.INFO, 'Create record group {}'.format(bufferName))
            file.create_group(bufferName)
        grp = file[bufferName]

        ### Set time
        if not('time' in grp):
            try:
                Logging.write(logging.INFO, 'Create record dset "{}/time"'.format(bufferName))
                grp.create_dataset('time', shape=(0, 1), dtype=np.float64, maxshape=(None, 1))
            except:
                Logging.write(logging.WARNING, 'Failed to create record dset "{}/time"'.format(bufferName))

        dset = grp['time']
        ## Resize dataset and append new time
        dset.resize((dset.shape[0]+1, 1))
        currTime = time()
        dset[dset.shape[0]-1] = currTime

        ## Iterate over data in group (buffer)
        for key, value in self._out():

            ## Convert and determine dshape/dtype
            value = np.asarray(value) if isinstance(value, list) else value
            dshape = value.shape if isinstance(value, np.ndarray) else (1,)
            dtype = value.dtype if isinstance(value, np.ndarray) else type(value)

            ## On datasets:
            ## TODO: handle changing dataset sizes (e.g. rect ROIs which are slightly altered during rec)
            ###
            # NOTE ON COMPRESSION FOR FUTURE:
            # GZIP: common, but slow
            # LZF: fast, but only natively implemented in python h5py (-> can't be read by HDF Viewer)
            # TODO: write export tool for datasets
            ###

            ## Create dataset if it doesn't exist
            if not(key in grp):
                try:
                    Logging.write(logging.INFO, 'Create record dset "{}/{}"'.format(bufferName, key))
                    grp.create_dataset(key,
                                       shape=(0, *dshape,),
                                       dtype=dtype,
                                       maxshape=(None, *dshape,),
                                       chunks=(1, *dshape,),)#compression='lzf')
                except:
                    Logging.write(logging.WARNING, 'Failed to create record dset "{}/{}"'.format(bufferName, key))
            dset = grp[key]
            dset.attrs.create('Position', currTime, dtype=np.float64)

            ## Resize dataset and append new value
            dset.resize((dset.shape[0]+1, *dshape))
            dset[dset.shape[0]-1] = value
