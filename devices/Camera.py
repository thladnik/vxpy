import cv2
import numpy as np
import os

import Config
import Definition

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

def GetCamera():
    if Config.Camera[Definition.Camera.manufacturer] == 'TIS':
        return TIS()
    elif Config.Camera[Definition.Camera.manufacturer] == 'virtual':
        return Virtual()

class Virtual:

    def __init__(self):
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Demo_Fish_capture_high_fps.avi'))
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_spontaneous_saccades_40s.avi'))
        self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_multiple_fish_30s.avi'))
        #self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, 'Fish_eyes_mid_quality_60s.avi'))
        self.setVideoFormat(Config.Camera[Definition.Camera.format],
                                   Config.Camera[Definition.Camera.res_y],
                                   Config.Camera[Definition.Camera.res_x])

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


class TIS:

    def __init__(self):
        from lib.pyapi import tisgrabber as IC
        self._device = IC.TIS_CAM()
        self._device.open(Config.Camera[Definition.Camera.model])
        self._device.SetVideoFormat(Config.Camera[Definition.Camera.format])
        self._device.SetPropertySwitch("Framerate","Auto",0)
        self._device.SetPropertySwitch("Exposure","Auto",0)
        self._device.SetPropertyAbsoluteValue("Exposure", "Value", 1./1000)
        self._device.SetFrameRate(Config.Camera[Definition.Camera.fps])
        self._device.SetContinuousMode(0)
        self._device.StartLive(0)


    @staticmethod
    def getModels():
        from lib.pyapi import tisgrabber as IC
        return IC.TIS_CAM().GetDevices()

    def getFormats(self):
        self._device.GetVideoFormats()

    def GetImage(self):
        self._device.GetImage()


    def setVideoFormat(self, format, x, y):
        self._format = format
        self._x = x
        self._y = y