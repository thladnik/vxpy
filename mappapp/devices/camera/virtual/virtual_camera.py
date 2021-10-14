import cv2
import numpy as np
import os
import time
from typing import Dict

from mappapp.core.camera import AbstractCameraDevice, Format
from mappapp import Def

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

_formats = {'Multi_Fish_Eyes_Cam@20fps': ['RGB8 (752x480)', 'Y800 (752x480)', 'RGB8 (640x480)', 'Y800 (640x480)',
                                          'RGB8 (480x480)', 'Y800 (480x480)'],
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


def get_connected_devices():
    devices: Dict[str, CameraDevice] = {}

    for sn in range(len(_models)):
        devices[str(sn)] = CameraDevice(serial=sn, model=_models[sn])

    return devices


class CameraDevice(AbstractCameraDevice):

    def __init__(self, *args, **kwargs):
        super(CameraDevice, self).__init__(*args, **kwargs)
        self.t_start = None
        self.t_last = None
        self.i_last = None
        self.f_last = None
        self._preload_file = False
        self.res_x = None
        self.res_y = None
        self._data = None
        self._cap = None
        self._fps = None
        self.index = None

    def open(self):
        return os.path.exists(os.path.join(Def.package, Def.Path.Sample, _sampleFile[_models[self.serial]]))

    def start_stream(self):
        self._cap = cv2.VideoCapture(os.path.join(Def.package, Def.Path.Sample, _sampleFile[_models[self.serial]]))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._data = []

        self.t_start = time.perf_counter()
        self.t_last = time.perf_counter()
        self.i_last = -1
        self.f_last = None

        # Extract resolution from format
        # s = re.search('\((.*?)x(.*?)\)', self.format)
        # self.res_x = int(s.group(1))
        # self.res_y = int(s.group(2))
        self.res_x, self.res_y = self._fmt.width, self._fmt.height

        if self._preload_file:
            self.index = 0
            while True:
                ret, frame = self._cap.read()
                if ret:
                    self._data.append(frame[:self.res_y,:self.res_x,0])
                else:
                    break
            self._data = np.array(self._data)

    def snap_image(self, *args, **kwargs):
        pass

    def get_image(self):
        # From previously loaded file
        if self._preload_file:
            self.index += 1
            if self._data.shape[0] <= self.index:
                self.index = 0

            return self._data[self.index]

        # From live capture
        ret, frame = self._cap.read()
        if ret:
            return frame[:self.res_y, :self.res_x]
        else:
            # From start
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return self.get_image()

    def get_formats(self):
        return _formats[self.info['model']]

    def set_exposure(self, e):
        pass

    def set_gain(self, g):
        pass
