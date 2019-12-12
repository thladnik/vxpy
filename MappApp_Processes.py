import cv2
import multiprocessing as mp
import multiprocessing.connection as mpconn
import numpy as np
import signal
import sys
import time

import devices.cameras.tisgrabber as IC

import MappApp_Definition as madef
from MappApp_Helper import rpc


class BaseProcess:

    _name = None

    _running = None
    _shutdown = None

    def __init__(self, _ctrlQueue: mp.Queue=None, _inPipe: mpconn.PipeConnection = None):
        self._ctrlQueue = _ctrlQueue
        self._inPipe = _inPipe

        # Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)


    def run(self):
        print('> Run %s' % self._name)
        self._running = True
        self._shutdown = False

        # Run event loop
        self.main()

        self._sendToCtrl(madef.Process.State.stopped)

    def main(self):
        """
        Event loop to be re-implemented in subclass
        :return:
        """
        pass

    def _start_shutdown(self):
        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def _queryPropertyFromCtrl(self, propName):
        self._sendToCtrl([madef.Process.Signal.query, propName])

    def _rpcToCtrl(self, function, *args, **kwargs):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._rpcToProcess(madef.Process.Controller, function, args, kwargs)

    def _sendToCtrl(self, data):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._sendToProcess(madef.Process.Controller, data)

    def _rpcToProcess(self, process, function, *args, **kwargs):
        self._sendToProcess(process, [madef.Process.Signal.rpc, function, args, kwargs])

    def _sendToProcess(self, process, data):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        :param process:
        :param data:
        :return: None
        """
        self._ctrlQueue.put([self._name, process.name, data])

    def _setProperty(self, propName, data):
        if hasattr(self, propName):
            print('Process <%s>: set property <%s> to value <%s>' % (self._name, propName, str(data)))
            setattr(self, propName, data)
            return
        print('Process <%s>: FAILED to set property <%s> to value <%s>' % (self._name, propName, str(data)))


    def _handlePipe(self, wait=False):

        # Poll pipe and (optionally) wait for a number of iterations
        t = time.perf_counter()
        while not(self._inPipe.poll()):
            if not(wait) or (time.perf_counter() >= t + 3.0):
                return

        obj = self._inPipe.recv()

        # RPC calls
        if obj[0] == madef.Process.Signal.rpc:
            rpc(self, obj[1:])

        # Set property
        elif obj[0] == madef.Process.Signal.setProperty:
            self._setProperty(*obj[1:])


    def _handleSIGINT(self, sig, frame):
        print('SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)



######
# Worker processes

class Display(BaseProcess):

    _name = madef.Process.Display.name

    def __init__(self, **kwargs):
        BaseProcess.__init__(self, **kwargs)

        self.run()

    def main(self):
        while self._isRunning():
            # Look in pipe for new data
            action = self._handlePipe()

            if action is not None:
                # Take further actions
                pass


            time.sleep(0.1)

    # RPC calls
    pass

class DataCruncher(BaseProcess):

    _name = madef.Process.DataCruncher.name

    def __init__(self, **kwargs):
        BaseProcess.__init__(self, **kwargs)

        self.run()

    def _add(self, *args):
        print(sum(args))

    def main(self):
        while self._isRunning():
            # Look in pipe for new data
            action = self._handlePipe()

            if action is not None:
                # Take further actions
                pass


import ctypes


class FrameGrabber(BaseProcess):

    _name = madef.Process.FrameGrabber.name

    _recordingVideo = False

    def __init__(self, _cameraBO, **kwargs):
        self._cameraBO = _cameraBO
        self._cameraBO.constructBuffers()
        BaseProcess.__init__(self, **kwargs)

        self.frameDims = self._cameraBO.frameDims
        self.fps = 100.

        # Set up camera
        self.camera = IC.TIS_CAM()
        self.camera.open(self._cameraBO.model)
        self.camera.SetVideoFormat(self._cameraBO.videoFormat)
        self.camera.SetPropertySwitch("Framerate","Auto",0)
        self.camera.SetPropertySwitch("Exposure","Auto",0)
        self.camera.SetPropertyAbsoluteValue("Exposure", "Value", 1./1000)
        self.camera.SetFrameRate(self.fps)
        self.camera.SetContinuousMode(0)
        self.camera.StartLive(0)

        self.run()

    def _startVideoRecording(self):

        if not(self._recordingVideo):

            # TODO: start an encoder-process which gets passed the _cameraBO object
            #   to avoid performance drain on frame acquisition

            # Count how many frame buffers should be written to file
            self.outFileFrameNum = 0
            for name in self._cameraBO.buffers():
                if self._cameraBO.buffers()[name]._recordBuffer: self.outFileFrameNum += 1

            startt = time.strftime('%Y-%m-%d-%H-%M-%S')
            print('Start video recording at time %s' % startt)
            # Define codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.videoRecord = cv2.VideoWriter(
                'output_%s.avi' % startt, fourcc, self.fps,
                (self.frameDims[1] * self.outFileFrameNum, self.frameDims[0]), isColor=0)
            self._recordingVideo = True

            return
        print('ERROR: could not start recording, because video is already being recorded. Please save last video first')

    def _writeFrame(self):

        if self._recordingVideo:
            frames = list()
            for i, name in enumerate(self._cameraBO.buffers()):
                if self._cameraBO.buffers()[name]._recordBuffer:
                    frames.append(self._cameraBO.readBuffer(name))
            self.videoRecord.write(np.hstack(frames))

    def _stopVideoRecording(self):

        if self._recordingVideo:
            print('Stop video recording')
            self.videoRecord.release()
            self._recordingVideo = False

            return
        print('ERROR: could not stop recording, because there is not active recording. Please start video recording first')


    def _toggleVideoRecording(self):
        if self._recordingVideo:
            self._stopVideoRecording()
        else:
            self._startVideoRecording()

    def _updateBufferEvalParams(self, name, **kwargs):
        self._cameraBO.updateBufferEvalParams(name, **kwargs)

    def main(self):

        self.t = time.perf_counter()
        while self._isRunning():
            # Look in pipe for new data
            action = self._handlePipe()

            if action is not None:
                # Take further actions
                pass

            # Fetch current frame and update camera buffers
            frame = self.camera.GetImage()[:,:,0]
            self._cameraBO.update(frame)
            # Write to file
            self._writeFrame()

            # Wait until next frame
            while time.perf_counter() < self.t + 1./self.fps:
                pass
            self.t = time.perf_counter()

    def _start_shutdown(self):
        if self._recordingVideo:
            self._stopVideoRecording()
        BaseProcess._start_shutdown(self)


class IO:

    pass



######
# GUI
