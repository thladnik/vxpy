import cv2
import numpy as np
import os

import Config
import Definition
from lib.pyapi import tisgrabber as IC

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

def GetCamera(id):
    # TODO: id switches between different cameras for future multi camera use in one session.
    #       This also needs to be reflected in the configuration
    if Config.Camera[Definition.Camera.manufacturer] == 'TIS':
        return CAM_TIS()
    elif Config.Camera[Definition.Camera.manufacturer] == 'virtual':
        return CAM_Virtual()

class CAM_Virtual:

    _models = ['Multi_Fish_Eyes_Cam',
                'Single_Fish_Eyes_Cam']

    _formats = {'Multi_Fish_Eyes_Cam' : ['RGB8 (752x480)'],
                'Single_Fish_Eyes_Cam' : ['RGB8 (640x480)']}

    _sampleFile = {'Multi_Fish_Eyes_Cam' : 'Fish_eyes_multiple_fish_30s.avi',
                   'Single_Fish_Eyes_Cam' : 'Fish_eyes_spontaneous_saccades_40s.avi'}

    def __init__(self):
        self._model = Config.Camera[Definition.Camera.model]
        self._format = Config.Camera[Definition.Camera.format]
        self.vid = cv2.VideoCapture(os.path.join(Definition.Path.Sample, self._sampleFile[self._model]))

    @classmethod
    def getModels(cls):
        return cls._models

    def getFormats(self):
        return self.__class__._formats[self._model]

    def getImage(self):
        ret, frame = self.vid.read()
        if ret:
            return frame
        else:
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.getImage()

class CAM_TIS:

    def __init__(self):
        from lib.pyapi import tisgrabber as IC
        self._device = IC.TIS_CAM()
        self._device.open(self._device.GetDevices()[0].decode())#Config.Camera[Definition.Camera.model])
        self._device.SetVideoFormat(Config.Camera[Definition.Camera.format])
        ### Disable automatic settings
        self._device.SetPropertySwitch("Framerate","Auto",0)
        self._device.SetPropertySwitch("Exposure","Auto",0)

        #self._device.SetPropertyAbsoluteValue("Exposure", "Value", 1./1000)
        #self._device.SetFrameRate(Config.Camera[Definition.Camera.fps])
        self._device.SetContinuousMode(0)
        self._device.StartLive(0)

    def updateProperty(self, propName, value):
        ### Fetch current exposure
        currExposure = [0.]
        self._device.GetPropertyAbsoluteValue('Exposure', 'Value', currExposure)

        if propName == Definition.Camera.exposure and not(np.isclose(value, currExposure[0] * 1000)):
            self._device.SetPropertyAbsoluteValue('Exposure', 'Value', float(value)/1000)
        #elif propName == Definition.Camera.fps and
        #    self._device.SetPropertyAbsoluteValue('Framrate', 'Value', )



    @staticmethod
    def getModels():
        return IC.TIS_CAM().GetDevices()

    def getFormats(self, model):
        device = IC.TIS_CAM()
        device.open(model)
        return device.GetVideoFormats()

    def getImage(self):
        return self._device.GetImage()
