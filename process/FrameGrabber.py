import cv2
from time import perf_counter, strftime


from process.Base import BaseProcess
import MappApp_Definition as madef

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
        # TODO: in furture check _cameraBO.manufacturer and model
        #  to allow different types of camera. For now, however, this only uses
        #  cameras from TheImagingSource
        import devices.cameras.tisgrabber as IC
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

            startt = strftime('%Y-%m-%d-%H-%M-%S')
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

        self.t = perf_counter()
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
            while perf_counter() < self.t + 1./self.fps:
                pass
            self.t = perf_counter()

    def _start_shutdown(self):
        if self._recordingVideo:
            self._stopVideoRecording()
        BaseProcess._start_shutdown(self)
