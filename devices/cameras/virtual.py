import cv2
import numpy as np
import os

import Definition

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class VirtualCamera:

    def __init__(self):
        self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Demo_Fish_capture_high_fps.avi'))

        self._image = np.sin(0.1 * np.arange(3000))
        self._image = np.repeat(self._image.reshape((-1,1)), 3000, axis=-1)
        self._image = (self._image > 0.).astype(float)
        self._image = np.repeat(self._image[:,:,np.newaxis], 3, axis=-1)

    @staticmethod
    def getModels():
        return ['cam01']

    def getFormats(self):
        return ['RGB8 (600x400)', 'Mono8 (600x400)']

    def GetImage(self):
        ret, frame = self.vid.read()
        if ret:
            return frame[:self._x,:self._y]
        else:
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.GetImage()

        #return self.image[:self._x, :self._y,:]

    def setVideoFormat(self, format, x, y):
        self._format = format
        #if self._format.startswith('RGB8') or self._format.startswith('Mono8'):
        imin = self._image.min()
        imax = self._image.max()
        self.image = ((self._image-imin) / (imax-imin) * 2**8).astype(np.uint8)
        self._x = x
        self._y = y
