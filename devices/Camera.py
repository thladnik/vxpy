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

    def updateProperty(self, propName, value):
        pass

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
        #import IPython
        #IPython.embed()
        self._device.open(Config.Camera[Definition.Camera.model])
        self._device.SetVideoFormat(Config.Camera[Definition.Camera.format])

        ### Disable automatic settings
        #self._device.SetFrameRate(Config.Camera[Definition.Camera.fps])
        #self._device.SetContinuousMode(0)

        self._device.SetPropertySwitch("Exposure","Auto", 0)
        self._device.SetPropertyAbsoluteValue("Exposure", "Value", 1./1000)  # 1ms
        self._device.SetPropertySwitch("Gain","Auto", 0)
        self._device.SetPropertyAbsoluteValue("Gain", "Value", 5)


        self.exposureAuto = [0]
        #self._device.GetPropertySwitch("AutoExposure", "Auto", self.exposureAuto)  # wrong auto exposure
        self.gainAuto = [0]
        self._device.GetPropertySwitch("Gain", "Auto", self.gainAuto)
        self._device.enableCameraAutoProperty(4,0) # Disable auto exposure (for REAL)
        self._device.StartLive(0)

    def updateProperty(self, propName, value):
        ### Fetch current exposure
        currExposure = [0.]
        self._device.GetPropertyAbsoluteValue('Exposure', 'Value', currExposure)
        currGain = [0.]
        self._device.GetPropertyAbsoluteValue('Gain', 'Value', currGain)
        #print('Exposure [{}]:'.format(self.exposureAuto[0]), currExposure[0], '// Gain [{}]:'.format(self.gainAuto[0]), currGain[0])

        if propName == Definition.Camera.exposure and not(np.isclose(value, currExposure[0] * 1000, atol=0.001)):
            print('Set exposure from', currExposure[0] * 1000, 'to', value)
            self._device.SetPropertyAbsoluteValue('Exposure', 'Value', float(value)/1000)




    @staticmethod
    def getModels():
        return IC.TIS_CAM().GetDevices()

    def getFormats(self, model):
        device = IC.TIS_CAM()
        device.open(model)
        return device.GetVideoFormats()

    def getImage(self):
        self._device.SnapImage()
        return self._device.GetImage()
