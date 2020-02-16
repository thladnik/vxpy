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
import multiprocessing as mp
import numpy as np
from time import perf_counter

import Config
import Definition

################################
## Buffer Object

class BufferObject:
    """Buffer Object: wrapper for all individual buffers

    Consumers have to initially call constructBuffers() to be able to read data from a buffer.
    """

    def __init__(self):

        self._buffers = dict()
        self._npBuffers = dict()

    def addBuffer(self, buffer, **kwargs):
        self._buffers[buffer.__name__] = buffer(**kwargs)

    def constructBuffers(self, _reconstruct=False):
        if bool(self._npBuffers) and not _reconstruct:
            return
        for name in self._buffers:
            self._npBuffers[name] = self._buffers[name].constructBuffer()

    def update(self, frame):
        for name in self._buffers:
            self._buffers[name].update(frame)

    def readBuffer(self, name):
        return self._buffers[name].readBuffer()

    def updateBufferEvalParams(self, name, **kwargs):
        if name in self._buffers:
            self._buffers[name].evalParamUpdate(**kwargs)

    def buffers(self):
        return self._buffers


################################
## Frame Buffer

class FrameBuffer:

    def __init__(self, _useLock = True, _recordBuffer=True):
        self._useLock = _useLock
        self._recordBuffer = _recordBuffer

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

    def evalParamUpdate(self, **kwargs):
        """Re-implement in subclass

        :param kwargs:
        :return:
        """
        pass

    def _format(self, frame):
        return np.rot90(frame, 2)

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
            newframe[:40,:200,:] = 0.
            newframe = cv2.putText(newframe, 'FPS %.2f' % fps, (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)#.get()

        return newframe

    def update(self, frame):
        """Method to be called by producer (FramGrabber).
        Automatically calls the _compute method and passes the result to _out.

        Ususally this method will be called implicitly by calling the Camera Buffer Object's update method.

        :param frame: new frame to be processed and written to buffer
        :return: None
        """
        self._out(self._compute(frame))



