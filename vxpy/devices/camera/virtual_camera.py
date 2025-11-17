"""Vritual camera device that reads from a dataset or video file for testing and debugging.
"""
from typing import Any, Dict, List, Tuple, Union

import cv2
import h5py
import numpy as np

import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.devices.camera as vxcamera
from vxpy.utils import examples

log = vxlogger.getLogger(__name__)


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
        self._cap = None
        self._tstart = None
        self._times = None
        self.index = None
        self._h5: Union[h5py.File, None] = None
        self.next_time_get_image = vxipc.get_time()

    def _open(self):

        self.index = 0
        log.debug(f'Open dummy camera data file')
        if self.properties['data_source'].lower() == 'dataset':
            self._h5 = examples.load_dataset(self.properties['data_path'])
            self._cap = self._h5['frames']

            # Check for precise timing information
            if 'times' in self._h5:
                self._times = self._h5['times'][:]
                self._tstart = vxipc.get_time()

            if self.properties['preload_data']:
                log.debug('Preload frame data')
                self._cap = self._cap[:]

        elif self.properties['data_source'].lower() == 'hdf5':
            self._h5 = h5py.File(self.properties['data_path'], 'r')
            self._cap = self._h5[self.properties['data_name']]
            if self.properties['preload_data']:
                log.debug('Preload frame data')
                self._cap = self._cap[:]

        elif self.properties['data_source'].lower() == 'avi':
            self._cap = cv2.VideoCapture(self.properties['data_path'])
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
        frame = None
        if self.properties['data_source'].lower() in ['dataset', 'hdf5']:
            if self._cap.shape[0] <= self.index:
                self.index = 0

            if self._tstart is not None and self.index < self._cap.shape[0]-1:
                tmin = self._times[self.index+1]

                if tmin > vxipc.get_time() - self._tstart:
                    return

            frame = self._cap[self.index][:self.res_y, :self.res_x]

        elif self.properties['data_source'].lower() == 'avi':
            ret, frame = self._cap.read()
            if not ret:
                self._cap = cv2.VideoCapture(self.properties['data_path'])
                ret, frame = self._cap.read()

        if frame is None:
            return

        if len(frame.shape) > 2:
            frame = frame[:, :, 0]

        # Set next frame time
        self.next_time_get_image = vxipc.get_time() + 1. / self.frame_rate

        self.index += 1

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
        camera_list = []
        for key in examples.get_local_dataset_names():

            with examples.load_dataset(key) as h5f:

                parts = key.split('_')
                fps = float(parts[-1].replace('Hz', ''))

                # Get dataset and append camera to list
                props = {'width': h5f['frames'].shape[2], 'height': h5f['frames'].shape[1],
                         'data_source': 'dataset', 'data_path': key, 'frame_rate': fps}
                camera_list.append(VirtualCamera(**props))

        return camera_list


if __name__ == '__main__':
    pass
