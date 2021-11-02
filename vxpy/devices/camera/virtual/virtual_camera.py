import cv2
import h5py
import numpy as np
import os
import time
from typing import Dict

from vxpy.core.camera import AbstractCameraDevice, Format
from vxpy import Def

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
            'Single_Fish_Spontaneous_1@115fps': ['RGB8(640x480)@115', 'Y800(600x380)@115', 'RGB8(600x380)@115'],
            'Single_Fish_Spontaneous_2@115fps': ['RGB8(640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_3@115fps': ['RGB8(640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_4@115fps': ['RGB8(640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_1@30fps': ['RGB8(640x480)', 'Y800 (600x380)', ],
            'Single_Fish_Free_Swim_Dot_Chased@50fps': ['RGB8 (640x480)', 'Y800 (600x380)', ],
            'Single_Fish_Free_Swim_On_random_motion@100fps': ['RGB8 (640x480)', 'Y800 (600x380)', ],
            'Single_Fish_OKR_embedded@30fps': ['RGB8 (640x480)', 'Y800 (600x380)', ]}

_sample_files = {'Multi_Fish_Eyes_Cam@20fps': 'Fish_eyes_multiple_fish_30s.avi',
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
        self._preload_file = True
        self.res_x = None
        self.res_y = None
        self._data = None
        self._cap = None
        self._fps = None
        self.index = None
        self._h5 = None

    def _get_filepath(self):
        return os.path.join(Def.Path.Sample, 'samples_compr.h5')

    def open(self):
        if os.path.exists(self._get_filepath()):
            h5 = h5py.File(self._get_filepath(), 'r')
            contained = self.info['model'] in h5
            h5.close()
            return contained
        return False

    def start_stream(self):
        self._h5 = h5py.File(self._get_filepath(), 'r')
        self._cap = self._h5[self.info['model']]
        if self._preload_file:
            self._data = self._cap[:]
        self.index = 0
        self.res_x, self.res_y = self._fmt.width, self._fmt.height

    def snap_image(self, *args, **kwargs):
        pass

    def get_image(self):
        self.index += 1
        if self._cap.shape[0] <= self.index:
            self.index = 0

        if self._preload_file:
            # From preloaded data
            return self._data[self.index][:self.res_y, :self.res_x]
        else:
            # From dataset
            return self._cap[self.index][:self.res_y, :self.res_x]

    def get_formats(self):
        _fmts = [Format.from_str(fmt) for fmt in _formats[self.info['model']]]
        return _fmts

    def set_exposure(self, e):
        pass

    def set_gain(self, g):
        pass
