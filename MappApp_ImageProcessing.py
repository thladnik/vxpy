import ctypes
import cv2
import multiprocessing as mp
import numpy as np
from time import perf_counter

################################
## Camera Buffer Object

class CameraBO:
    """Camera Buffer Object: wrapper for individual buffers between FrameGrabber (producer)
    and any number of consumers.
    """

    def __init__(self, cameraConfig):
        self.manufacturer = cameraConfig['manufacturer']
        self.model = cameraConfig['model']
        self.videoFormat = cameraConfig['format']

        self.frameDims = (int(cameraConfig['resolution_x']), int(cameraConfig['resolution_y']))


        self._buffers = dict()
        self._npBuffers = dict()

    def addBuffer(self, name, **kwargs):
        if name == 'frame':
            self._buffers[name] = FrameBuffer(frameDims=self.frameDims, **kwargs)
        elif name == 'edge_detector':
            self._buffers[name] = EdgeDetector(frameDims=self.frameDims, **kwargs)
        elif name == 'ellipse_fitter':
            self._buffers[name] = EllipseFit(**kwargs)


    def constructBuffers(self):
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
## Frame Buffers

## Basic Frame Buffer
class FrameBuffer:

    def __init__(self, frameDims, _useLock = True, _recordBuffer=True):
        self._recordBuffer = _recordBuffer

        # Set up lock
        self._useLock = _useLock
        self._lock = None
        if self._useLock:
            self._lock = mp.Lock()

        # Set up shared array (in parent process)
        self.frameDims = frameDims
        self._cBuffer = mp.Array(ctypes.c_uint8, frameDims[0] * frameDims[1], lock=self._useLock)
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
            self._npBuffer = self._npBuffer.reshape(self.frameDims)

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

    def _formatFrame(self, frame):
        return np.rot90(frame, 2)

    def _out(self, newframe):
        """Write contents of newframe to the numpy buffer

        :param newframe:
        :return:
        """
        if self._lock is not None:
            self._lock.acquire()
        self._npBuffer[:, :] = newframe
        if self._lock is not None:
            self._lock.release()

    def _compute(self, frame):
        """Re-implement in subclass
        :param frame: AxB frame image data
        :return: new frame
        """

        # Add FPS counter
        self.frametimes.append(perf_counter() - self.t)
        self.t = perf_counter()
        # Add FPS
        fps = 1. / np.mean(self.frametimes[-20:])
        #newframe = np.rot90(frame, 2)
        newframe = cv2.putText(frame, 'FPS %.2f' % fps, (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2).get()
        #print('Frametime: %.10f' % self.frametimes[-1])

        return newframe

    def update(self, frame):
        """Method to be called from producer (FramGrabber, etc...).
        Automatically calls the _compute method and passes the result to _out.

        Ususally this method will be called implicitly by calling the Camera Buffer Object's update method.

        :param frame: new frame to be processed and written to buffer
        :return: None
        """
        self._out(self._compute(self._formatFrame(frame)))


################
## Custom Frame Buffers

class EdgeDetector(FrameBuffer):
    """Example of a FrameBuffer which detects the edges in a frame.

    This is an example of a GOOD implementation of a FrameBuffer, because it is an efficient way to communicate
    and store edge data, as there is no sensible parametric way of describing the result.

    """
    def __init__(self, *args, **kwargs):
        FrameBuffer.__init__(self, *args, **kwargs)

        self.thresh1 = 100
        self.thresh2 = 150

    def _compute(self, frame):
        newframe = cv2.Canny(frame, self.thresh1, self.thresh2)

        return newframe

    def evalParamUpdate(self, thresh1=None, thresh2=None):
        """Re-implement in subclass

        :param kwargs:
        :return:
        """
        if thresh1 is not None:
            self.thresh1 = thresh1
        if thresh2 is not None:
            self.thresh2 = thresh2

class EllipseFitter(FrameBuffer):
    """Example of a FrameBuffer which thresholds the original frame, extract the contours of particles
    and draws ellipses around the particles. Returns a complete frame with ellipses drawn on top.

    This is an example of a BAD IMPLEMENTATION of a FrameBuffer. Parameters for ellipses COULD be
    written to an ObjectBuffer instead. This would save memory, potentially save storage and
    make ellipse parameters available in other processes for further evaluation.
    """
    def __init__(self, *args, **kwargs):
        FrameBuffer.__init__(self, *args, **kwargs)

    def _compute(self, frame):

        ret, binaryFrame = cv2.threshold(frame, 100, 200, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(binaryFrame, 1, 2)
        newframe = frame.copy()
        for cnt in contours:
            if len(cnt) >= 100:  # at least 5 points for ellipse
                ellipse = cv2.fitEllipse(cnt)
                newframe = cv2.ellipse(newframe, ellipse, (0, 255, 0), 2)

        return newframe


################################
## Basic Object Buffer

class ObjectBuffer:
    def __init__(self, _bufferLength, _objectLength, _object_cType, _object_npType, _useLock = True, _recordBuffer=False):
        self._bufferLength = _bufferLength
        self._objectLength = _objectLength
        self._object_cType = _object_cType
        self._object_npType = _object_npType
        self._useLock = _useLock
        self._recordBuffer = _recordBuffer

        # Set up lock
        self._lock = None
        if self._useLock:
            self._lock = mp.Lock()

        # Set up shared array (in parent process)
        self._cBuffer = mp.Array(self._object_cType, self._bufferLength * self._objectLength, lock=self._useLock)
        self._npBuffer = None

    def constructBuffer(self):
        """Construct the numpy buffer from the cArray pointer object

        :return: numpy buffer object to be used in child process instances
        """
        if self._npBuffer is None:
            if not (self._useLock):
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer)
            else:
                self._npBuffer = np.ctypeslib.as_array(self._cBuffer.get_obj())
            self._npBuffer = self._npBuffer.reshape((self._bufferLength, self._objectLength))

        return self._npBuffer

    def evalParamUpdate(self, **kwargs):
        """Re-implement in subclass

        :param kwargs:
        :return:
        """
        pass

    def _out(self, data):
        """Write contents of newframe to the numpy buffer

        :param newframe:
        :return:
        """
        if self._lock is not None:
            self._lock.acquire()
        self._npBuffer[:, :] = 0.
        if len(data) > 0:
            self._npBuffer[:, :] = self._inparse(data)
        if self._lock is not None:
            self._lock.release()

    def _inparse(self, data):
        """Transformation of data for WRITING TO numpy buffer
        """
        rawBuffer = data
        return rawBuffer

    def _outparse(self, rawBuffer):
        """Transformation of data for READING FROM numpy buffer
        """
        buffer = rawBuffer
        return buffer

    def _compute(self, frame):
        """Re-implement in subclass
        :param frame: AxB frame image data
        :return: new frame
        """

        return np.array([])

    def update(self, frame):
        """Method to be called from producer (e.g. FrameGrabber).
        Automatically calls the _compute method and passes the result to _out.

        Usually this method will be called implicitly by calling the Camera Buffer Object's update method.

        :param frame: new frame to be processed and written to buffer
        :return: None
        """
        self._out(self._compute(frame))

    def readBuffer(self):
        if self._lock is not None:
            self._lock.acquire()
        buffer = self._outparse(self._npBuffer)
        if self._lock is not None:
            self._lock.release()
        return buffer

################
## Custom Object Buffers

class EllipseFit(ObjectBuffer):
    """Example of an ObjectBuffer which thresholds the original frame, extracts the contours of particles
    and fits an ellipse around the particles. Returns a list of ellipse parameters.

    This is an example of a BETTER IMPLEMENTATION of the EllipseFitter(FrameBuffer) class.
    Parameters for ellipses ARE written directly to the buffer.
    """
    def __init__(self, *args, **kwargs):
        ObjectBuffer.__init__(self, 100, 5, ctypes.c_float, np.float, *args, **kwargs)

    def _inparse(self, data):
        newdata = np.nan * np.ones((self._bufferLength, self._objectLength), dtype=self._object_npType)
        for i, d in enumerate(data):
            newdata[i,:] = np.array([*d[0], *d[1], d[2]])
        return newdata

    def _outparse(self, rawBuffer):
        data = list()
        for i in range(rawBuffer[np.isfinite(rawBuffer[:,0]),:].shape[0]):
            data.append(((*rawBuffer[i,:2], ), (*rawBuffer[i,2:4], ), rawBuffer[i,4]))
        return data

    def _compute(self, frame):

        ret, binaryFrame = cv2.threshold(frame, 124, 200, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(binaryFrame, 1, 2)

        ellipses = list()
        for cnt in contours:
            if len(cnt) >= 100:  # at least 5 points for ellipse
                ellipses.append(cv2.fitEllipse(cnt))

        return ellipses