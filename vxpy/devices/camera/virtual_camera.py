"""
vxPy ./devices/camera/virtual_camera.py
Copyright (C) 2022 Tim Hladnik

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
from typing import Any, Dict, List, Tuple, Union

import cv2
import h5py
import numpy as np

import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.devices.camera as vxcamera
from vxpy.definitions import *

log = vxlogger.getLogger(__name__)

_sample_filename_full = 'samples.hdf5'
_sample_filename_compressed = 'samples_compr.hdf5'


def _get_filepath():
    uncompr_path = os.path.join(PATH_SAMPLE, _sample_filename_full)
    if os.path.exists(uncompr_path):
        return uncompr_path
    return os.path.join(PATH_SAMPLE, _sample_filename_compressed)


available_datasets = [
    'Multi_Fish_Eyes_Cam_20fps',
    'Single_Fish_Eyes_Cam_20fps',
    'Single_Fish_Spontaneous_1_115fps',
    'Single_Fish_Spontaneous_2_115fps',
    'Single_Fish_Spontaneous_3_115fps',
    'Single_Fish_Spontaneous_4_115fps',
    'Single_Fish_Spontaneous_1_30fps',
    'Single_Fish_Free_Swim_Dot_Chased_50fps',
    'Single_Fish_Free_Swim_On_random_motion_100fps',
    'Single_Fish_OKR_embedded_30fps'
]


class VirtualCamera(vxcamera.CameraDevice):

    def __repr__(self):
        return f'{VirtualCamera.__name__} {self.properties["data_path"]}'

    def get_settings(self) -> Dict[str, Any]:
        return {'data_path': self.properties['data_path'], 'width':
            self.width, 'height': self.height, 'frame_rate': self.frame_rate}

    @property
    def exposure(self) -> float:
        return 1

    @property
    def gain(self) -> float:
        return 1

    @property
    def frame_rate(self) -> float:
        return self.properties['frame_rate']

    @property
    def width(self) -> float:
        return self.properties['width']

    @property
    def height(self) -> float:
        return self.properties['height']

    def __init__(self, *args, **kwargs):
        vxcamera.CameraDevice.__init__(self, *args, **kwargs)

        self.f_last = None
        self.res_x = None
        self.res_y = None
        self._data = None
        self._cap = None
        self.index = None
        self._h5: Union[h5py.File, None] = None
        self.next_time_get_image = vxipc.get_time()

    def _open(self):

        log.debug(f'Open {_get_filepath()}')
        self._h5 = h5py.File(_get_filepath(), 'r')

        if self.properties['data_source'] == 'HDF5':
            self._cap = self._h5[self.properties['data_path']]
            if self.properties['preload_data']:
                log.debug('Preload frame data')
                self._data = self._cap[:]
            self.index = 0
        elif self.properties['data_source'] == 'AVI':
            self._cap = cv2.VideoCapture(self.properties['data_path'])
            self.index = 0
        else:
            return False

        return True

    def _start_stream(self):
        return True

    def next_snap(self) -> bool:
        return False

    def snap_image(self, *args, **kwargs):
        pass

    def next_image(self) -> bool:
        return vxipc.get_time() >= self.next_time_get_image

    def get_image(self):
        self.index += 1

        if self.properties['data_source'] == 'HDF5':
            if self._cap.shape[0] <= self.index:
                self.index = 0

            if self.properties['preload_data']:
                # From preloaded data
                frame = self._data[self.index][:self.res_y, :self.res_x]

            else:
                # From dataset
                try:
                    frame = self._cap[self.index][:self.res_y, :self.res_x]
                except:
                    log.error(f'Error reading frame for device {self}')
                    return None

        elif self.properties['data_source'] == 'AVI':
            ret, frame = self._cap.read()
            if not ret:
                print('Reset')
                self._cap = cv2.VideoCapture(self.properties['data_path'])
                ret, frame = self._cap.read()

            if frame is None:
                return

            frame = frame[:, :, 0]

        # Set next frame time
        self.next_time_get_image = vxipc.get_time() + 1. / self.frame_rate

        return np.asarray(frame, dtype=np.uint8)

    def _end_stream(self) -> bool:
        if self._h5 is not None:
            self._h5.close()
            self._h5 = None

        return True

    def _close(self) -> bool:
        pass

    @classmethod
    def get_camera_list(cls) -> List[vxcamera.CameraDevice]:
        h5file = h5py.File(_get_filepath(), 'r')
        camera_list = []
        for dataset_name in available_datasets:
            if dataset_name not in h5file:
                continue

            parts = dataset_name.split('_')
            fps = float(parts[-1].replace('fps', ''))

            # Get dataset and append camera to list
            dataset = h5file[dataset_name]
            props = {'width': dataset.shape[2], 'height': dataset.shape[1],
                     'data_path': dataset.name, 'frame_rate': fps}
            camera_list.append(VirtualCamera(**props))

        return camera_list


if __name__ == '__main__':
    pass
