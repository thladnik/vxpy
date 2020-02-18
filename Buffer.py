"""
MappApp ./Buffer.py - Buffer-objects for inter-process-communication
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
import cv2
import h5py
import logging
import multiprocessing as mp
import numpy as np
import os
from time import perf_counter, time

import Config
import Definition
import Logging

################################
## Buffer Object

class BufferObject:
    """Buffer Object: wrapper for buffers
    """

    def __init__(self, name):
        self.name = name
        self.recording = False
        self.h5File = None
        self.vidFile = None

        self._buffers = dict()
        self._npBuffers = dict()

    def addBuffer(self, buffer, **kwargs):
        """To be called by controller (initialization of buffers has to happen in parent process)"""
        self._buffers[buffer.__name__] = buffer(self, **kwargs)

    def constructBuffers(self, _reconstruct=False):
        if bool(self._npBuffers) and not _reconstruct:
            return
        for bufferName in self._buffers:
            self._npBuffers[bufferName] = self._buffers[bufferName].constructBuffer()

    def update(self, frame):
        for name in self._buffers:
            self._buffers[name].update(frame)

    def readBuffer(self, name):
        return self._buffers[name].readBuffer()

    def buffers(self):
        return self._buffers

    def _streamToFile(self, buffer):
        bufferName = buffer.__class__.__name__
        bufferId = '{}/{}'.format(self.name, bufferName)

        ### Is this particular buffer supposed to stream to file?
        if bufferId not in Config.Recording[Definition.Recording.buffers]:
            return

        if not(self.recording):
            ### Is recording mode activated and an output folder set?
            if not(Config.Recording[Definition.Recording.active]) or not(bool(Config.Recording[Definition.Recording.current_folder])):
                return

            if self.h5File is None:
                print('OPEN FILE')
                filepath = os.path.join(Definition.Path.Output,
                                        Config.Recording[Definition.Recording.current_folder])
                self.h5File = h5py.File(os.path.join(filepath, '{}.hdf5'.format(self.name)), 'w')
            self.recording = True

        ### Has current recording been paused or stopped? -> Pause recording
        if not(Config.Recording[Definition.Recording.active]):
            self.recording = False
            ### Has it been stopped? -> close current file
            if not(bool(Config.Recording[Definition.Recording.current_folder])):
                self.h5File.close()
                self.h5File = None
                buffer.fileStruct = dict()
                buffer.saveIdx = 0
            return

        ### If recording is running, unpaused and the file is opened -> write new data to file
        ## Each buffer writes to it's own group
        if bufferId not in buffer.fileStruct:
            buffer.fileStruct[bufferId] = dict(grp=self.h5File.require_group(bufferName))
        grp = buffer.fileStruct[bufferId]['grp']
        ## Iterate over datasets in group (buffer)
        for key, value in buffer._toFile():
            ## Convert and determine dshape/dtype
            value = np.asarray(value) if isinstance(value, list) else value
            dshape = value.shape if isinstance(value, np.ndarray) else (1,)
            dtype = value.dtype if isinstance(value, np.ndarray) else type(value)

            ## Get dataset
            ## TODO: handle changing dataset sizes (e.g. rect ROIs which are slightly altered during rec)
            ## Create dataset if it doesn't exist
            if key not in buffer.fileStruct[bufferId]:
                buffer.fileStruct[bufferId][key] = grp.create_dataset(key,
                                                                      shape=(0, *dshape,),
                                                                      dtype=dtype,
                                                                      maxshape=(None, *dshape,),
                                                                      chunks=(1, *dshape,))
            dset = buffer.fileStruct[bufferId][key]


            ## Resize dataset and set new value
            t = perf_counter()
            dset.resize((dset.shape[0]+1, *dshape))
            dset[dset.shape[0]-1] = value
            #dset.resize((buffer.saveIdx+2, *dshape))
            print(buffer.saveIdx, dtype, dshape, perf_counter()-t)

            # TODO: THE SOLUTION IS IN HERE: CHUNKS
            """
            import h5py
            import numpy as np
            import time

            f = h5py.File('test17.hdf5', 'w')
            f.require_dataset('test', dtype=np.uint8, shape=(20,480,720,3), maxshape=(None, 480, 720, 3), chunks=(20, 480, 720, 3))
            times = list()
            
            for i in range(300):
                b = np.random.randint(255, size=(480,720,3), dtype=np.uint8)
                d = f['test']
                t = time.perf_counter()
                if i >= d.shape[0]:
                    d.resize((d.shape[0]+20, *d.shape[1:]))
                d[i] = b[i]
                f.flush()
                times.append(time.perf_counter()-t)
                print(times[-1])
                d = None
            print('Mean', np.mean(times))
            f.close()
            """

            #except Exception as exc:
            #    Logging.write(logging.ERROR, 'Unable to write data "{}" to file for buffer "{}" / Exception: {}'
            #                  .format(key, bufferId, exc))
        buffer.saveIdx += 1


            


################################
## Abstract Buffer

class AbstractBuffer:


    def __init__(self, _bo):
        self._bo = _bo
        self.warned_once = False
        self.saveIdx = 0
        self.fileStruct = dict()


    def _toFile(self):
        if not(self.warned_once):
            Logging.write(logging.WARNING, 'Buffer "{}/{} toFile() method not implemented"'
                          .format(self._bo.name, self.__class__.__name__))
            self.warned_once = True
        return [(None, None)]

################################
## Frame Buffer

class FrameBuffer(AbstractBuffer):

    def __init__(self, *args, _useLock = True):
        AbstractBuffer.__init__(self, *args)
        self._useLock = _useLock

        # Set up lock
        self._lock = None
        if self._useLock:
            self._lock = mp.Lock()

        # Set up shared array (in parent/controller process)
        self.frameDims = (int(Config.Camera[Definition.Camera.res_y]),
                          int(Config.Camera[Definition.Camera.res_x]))
        self._cBuffer = mp.Array(ctypes.c_uint8, self.frameDims[0] * self.frameDims[1] * 3, lock=self._useLock)
        self._npBuffer = None

        self.frametimes = list()
        self.t = perf_counter()

    def constructBuffer(self):
        """Construct the numpy buffer from the cArray pointer object

        :return: numpy buffer object to be used in child process instances
        """
        if self._npBuffer is None:
            if not(self._useLock):
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer)
            else:
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer.get_obj())
            self._npBuffer = self._npBuffer.reshape((*self.frameDims, 3))

        return self._npBuffer

    def readBuffer(self):
        if self._lock is not None:
            self._lock.acquire()
        buffer = self._npBuffer.copy()
        if self._lock is not None:
            self._lock.release()
        return buffer

    def _out(self, newframe):
        """Write contents of newframe to the numpy buffer

        :param newframe:
        :return:
        """
        if self._lock is not None:
            self._lock.acquire()
        self._npBuffer[:,:,:] = newframe
        if self._lock is not None:
            self._lock.release()

    def _compute(self, frame):
        """Re-implement in subclass
        :param frame: AxB frame image data
        :return: new frame
        """

        newframe = frame.copy()
        if self.__class__.__name__ == 'FrameBuffer':
            # Add FPS counter
            self.frametimes.append(perf_counter() - self.t)
            self.t = perf_counter()
            fps = 1. / np.mean(self.frametimes[-20:])
            newframe = cv2.putText(newframe, 'FPS %.2f' % fps, (0, newframe.shape[0]//20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)

        return newframe

    def update(self, frame):
        """Method to be called only by producer.
        Automatically calls the _compute method and passes the result to _out.

        Ususally this method is called implicitly by calling the Camera Buffer Object's update method.

        :param frame: new frame to be processed and written to buffer
        :return: None
        """
        self._out(self._compute(frame))
        self._bo._streamToFile(self)

    def _toFile(self) -> dict:
        yield 'frames', self.readBuffer()


