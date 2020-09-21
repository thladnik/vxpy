"""
MappApp .devices/DefaultCameraRoutines.py - Camera device abstraction layer. New camera types may be added here.
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
import cv2
import logging
import numpy as np
import os
import platform

import Config
import Def
import Logging

### Import camera APIs
# Add application's DLL path on Windows
if platform == 'win32':
    os.environ['PATH'] += ';{}'.format(os.path.join(os.getcwd(), Def.Path.Libdll))

    from lib.pyapi import tisgrabber as IC
# MAC OS
elif platform == 'darwin':
    IC = None
# Assume it's Linux
else:
    IC = None

if Def.Env == Def.EnvTypes.Dev:
    from IPython import embed


# TODO: add abstract CAM class

class CAM_Virtual:

    _models = ['Multi_Fish_Eyes_Cam',
                'Single_Fish_Eyes_Cam']

    _formats = {'Multi_Fish_Eyes_Cam' : ['RGB8 (752x480)'],
                'Single_Fish_Eyes_Cam' : ['RGB8 (640x480)']}

    _sampleFile = {'Multi_Fish_Eyes_Cam' : 'Fish_eyes_multiple_fish_30s.avi',
                   'Single_Fish_Eyes_Cam' : 'Fish_eyes_spontaneous_saccades_40s.avi'}

    def __init__(self, model, format):
        self._model = model
        self._format = format
        self.vid = cv2.VideoCapture(os.path.join(Def.Path.Sample, self._sampleFile[self._model]))

    @classmethod
    def getModels(cls):
        return cls._models

    def updateProperty(self, propName, value):
        pass

    def getFormats(self):
        return self.__class__._formats[self._model]

    def snapImage(self):
        pass

    def getImage(self):
        ret, frame = self.vid.read()
        if ret:
            return frame
        else:
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.getImage()

class CAM_TIS:

    def __init__(self, model, format):
        from lib.pyapi import tisgrabber as IC
        self._device = IC.TIS_CAM()

        self._device.open(model)#Config.Camera[Def.CameraCfg.model])
        self._device.SetVideoFormat(format)#Config.Camera[Def.CameraCfg.format])

        ### TODO: maybe something here is involved in potential screen-tearing issues?
        #self._device.SetFrameRate(Config.Camera[Definition.Camera.fps])
        #self._device.SetContinuousMode(0)

        ### Disable auto settings
        self._device.SetPropertySwitch('Gain', 'Auto', 0)
        self._device.enableCameraAutoProperty(4, 0)  # Disable auto exposure (for REAL)

        ### Enable frame acquisition
        self._device.StartLive(0)

    def updateProperty(self, propName, value):
        ### Fetch current exposure
        currExposure = [0.]
        self._device.GetPropertyAbsoluteValue('Exposure', 'Value', currExposure)
        currGain = [0.]
        self._device.GetPropertyAbsoluteValue('Gain', 'Value', currGain)

        if propName == Def.CameraCfg.exposure and not(np.isclose(value, currExposure[0] * 1000, atol=0.001)):
            Logging.write(logging.DEBUG, 'Set exposure from {} to {} ms'.format(currExposure[0] * 1000, value))
            self._device.SetPropertyAbsoluteValue('Exposure', 'Value', float(value)/1000)

        elif propName == Def.CameraCfg.gain and not (np.isclose(value, currGain[0], atol=0.001)):
            Logging.write(logging.DEBUG, 'Set gain from {} to {}'.format(currGain[0], value))
            self._device.SetPropertyAbsoluteValue('Gain', 'Value', float(value))



    @staticmethod
    def getModels():
        return IC.TIS_CAM().GetDevices()

    def getFormats(self, model):
        device = IC.TIS_CAM()
        device.open(model)
        return device.GetVideoFormats()

    def snapImage(self):
        self._device.SnapImage()

    def getImage(self):
        #self._device.SnapImage()
        return self._device.GetImage()
