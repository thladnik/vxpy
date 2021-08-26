"""
MappApp .devices/camera.py
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
import re
import time

from mappapp import Def
from mappapp import Logging

if False:
    ### Import camera APIs
    # Add application's DLL path on Windows
    if platform == 'win32':
        os.environ['PATH'] += ';{}'.format(os.path.join(os.getcwd(), Def.Path.Libdll))
    # MAC OS
    elif platform == 'darwin':
        IC = None
    # Assume it's Linux
    else:
        IC = None

class AbstractCamera:

    def __init__(self, model: str, format_: str):
        self.model = model
        self.format = format_

    @staticmethod
    def get_models():
        raise NotImplementedError('')

    @staticmethod
    def get_formats(model):
        raise NotImplementedError('')

    def set_exposure(self, value: float):
        raise NotImplementedError('')

    def set_gain(self, value: float):
        raise NotImplementedError('')

    def snap_image(self):
        raise NotImplementedError('')

    def get_image(self):
        raise NotImplementedError('')

    def stop(self):
        pass


class VirtualCamera(AbstractCamera):

    _models = ['Multi_Fish_Eyes_Cam@20fps',
               'Single_Fish_Eyes_Cam@20fps',
               'Single_Fish_Spontaneous_1@115fps',
               'Single_Fish_Spontaneous_2@115fps',
               'Single_Fish_Spontaneous_3@115fps',
               'Single_Fish_Spontaneous_4@115fps',
               'Single_Fish_Spontaneous_1@30fps',
               'Single_Fish_Free_Swim_Dot_Chased@50fps',
               'Single_Fish_Free_Swim_On_random_motion@100fps',
               'Single_Fish_OKR_embedded@30fps']

    _formats = {'Multi_Fish_Eyes_Cam@20fps': ['RGB8 (752x480)', 'Y800 (752x480)', 'RGB8 (640x480)', 'Y800 (640x480)', 'RGB8 (480x480)', 'Y800 (480x480)'],
                'Single_Fish_Eyes_Cam@20fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
                'Single_Fish_Spontaneous_1@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
                'Single_Fish_Spontaneous_2@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
                'Single_Fish_Spontaneous_3@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
                'Single_Fish_Spontaneous_4@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
                'Single_Fish_Spontaneous_1@30fps': ['RGB8 (640x480)', 'Y800 (600x380)', ],
                'Single_Fish_Free_Swim_Dot_Chased@50fps': ['RGB8 (640x480)', 'Y800 (600x380)', ],
                'Single_Fish_Free_Swim_On_random_motion@100fps': ['RGB8 (640x480)', 'Y800 (600x380)', ],
                'Single_Fish_OKR_embedded@30fps': ['RGB8 (640x480)', 'Y800 (600x380)', ]}

    _sampleFile = {'Multi_Fish_Eyes_Cam@20fps': 'Fish_eyes_multiple_fish_30s.avi',
                   'Single_Fish_Eyes_Cam@20fps': 'Fish_eyes_spontaneous_saccades_40s.avi',
                   'Single_Fish_Spontaneous_1@115fps': 'single_zebrafish_eyes.avi',
                   'Single_Fish_Spontaneous_2@115fps': 'single_zebrafish_eyes0001.avi',
                   'Single_Fish_Spontaneous_3@115fps': 'single_zebrafish_eyes0002.avi',
                   'Single_Fish_Spontaneous_4@115fps': 'single_zebrafish_eyes0003.avi',
                   'Single_Fish_Spontaneous_1@30fps': 'OKR_2020-12-08_multi_phases.avi',
                   'Single_Fish_Free_Swim_Dot_Chased@50fps': 'fish_free_swimming_chased_by_dot.avi',
                   'Single_Fish_Free_Swim_On_random_motion@100fps': 'Freely_swimming_on_CMN01.avi',
                    'Single_Fish_OKR_embedded@30fps': 'OKR_2020-12-08_multi_phases.avi'}

    def __init__(self, *args):
        AbstractCamera.__init__(self, *args)

        self._device = cv2.VideoCapture(os.path.join(Def.package, Def.Path.Sample,self._sampleFile[self.model]))
        self._fps = self._device.get(cv2.CAP_PROP_FPS)
        self._data = []


        self.t_start = time.perf_counter()
        self.t_last = time.perf_counter()
        self.i_last = -1
        self.f_last = None

        # Extract resolution from format
        s = re.search('\((.*?)x(.*?)\)', self.format)
        self.res_x = int(s.group(1))
        self.res_y = int(s.group(2))

        self._preload_file = False
        if self._preload_file:
            self.index = 0
            while True:
                ret, frame = self._device.read()
                if ret:
                    self._data.append(frame[:self.res_y,:self.res_x,0])
                else:
                    break
            self._data = np.array(self._data)

    @staticmethod
    def get_models():
        return VirtualCamera._models

    @staticmethod
    def get_formats(model):
        if model in VirtualCamera._formats:
            return VirtualCamera._formats[model]
        return []

    def set_exposure(self, value: float):
        pass

    def set_gain(self, value: float):
        pass

    def snap_image(self):
        pass

    def get_image(self):
        if self._preload_file:
            self.index += 1
            if self._data.shape[0] <= self.index:
                self.index = 0

            return self._data[self.index]

        ret, frame = self._device.read()
        if ret:
            return frame[:self.res_y,:self.res_x]
        else:
            self._device.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.get_image()


class TISCamera(AbstractCamera):

    def __init__(self, *args):
        AbstractCamera.__init__(self, *args)
        from mappapp.lib.pyapi import tisgrabber

        self._device = tisgrabber.TIS_CAM()
        self._device.open(self.model)
        self._device.SetVideoFormat(self.format)

        ### Disable auto setting of gain and exposure
        self._device.SetPropertySwitch('Gain', 'Auto', 0)
        self._device.enableCameraAutoProperty(4, 0)  # Disable auto exposure (for REAL)

        ### Enable frame acquisition
        self._device.StartLive(0)

    def set_exposure(self, value: float):
        curr_exposure = [0.]
        self._device.GetPropertyAbsoluteValue('Exposure', 'Value', curr_exposure)

        if not(np.isclose(value, curr_exposure[0] * 1000, atol=0.001)):
            Logging.write(logging.DEBUG,'Set exposure from {} to {} ms'.format(curr_exposure[0] * 1000,value))
            self._device.SetPropertyAbsoluteValue('Exposure', 'Value', float(value) / 1000)

    def set_gain(self, value: float):
        curr_gain = [0.]
        self._device.GetPropertyAbsoluteValue('Gain', 'Value', curr_gain)

        if not(np.isclose(value, curr_gain[0], atol=0.001)):
            Logging.write(logging.DEBUG,'Set gain from {} to {}'.format(curr_gain[0],value))
            self._device.SetPropertyAbsoluteValue('Gain', 'Value', float(value))

    @staticmethod
    def get_models():
        from mappapp.lib.pyapi import tisgrabber

        cam = tisgrabber.TIS_CAM()
        return [s.decode() for s in cam.GetDevices()]

    @staticmethod
    def get_formats(model):
        from mappapp.lib.pyapi import tisgrabber

        device = tisgrabber.TIS_CAM()
        device.open(model)
        return [s.decode() for s in device.GetVideoFormats()]

    def snap_image(self):
        self._device.SnapImage()

    def get_image(self):
        return self._device.GetImage()

    def stop(self):
        self._device.StopLive()
