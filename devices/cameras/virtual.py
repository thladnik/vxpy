import cv2
import numpy as np
import os

import Definition

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class VirtualCamera:

    def __init__(self):
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Demo_Fish_capture_high_fps.avi'))
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_spontaneous_saccades_40s.avi'))
        self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_multiple_fish_30s.avi'))
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_mid_quality_60s.avi'))

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

    def setVideoFormat(self, format, x, y):
        self._format = format
        self._x = x
        self._y = y
