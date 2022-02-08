from typing import Any, List, Tuple, Union

import h5py
import numpy as np

from vxpy.core import camera_device
from vxpy.core.camera_device import AbstractCameraDevice, CameraFormat
from vxpy.definitions import *
from vxpy.core import logger

log = logger.getLogger(__name__)

FORMAT_STR = 'format'
FRAMERATE_RANGE_STR = 'framerate_range'

_sample_filename_full = 'samples.hdf5'
_sample_filename_compressed = 'samples_compr.hdf5'

_models: Dict[str, Dict[str, Any]] = {
    'Multi_Fish_Eyes_Cam_20fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('GRAY8', 640, 480)],
        FRAMERATE_RANGE_STR: (1, 20)
    },
    'Single_Fish_Eyes_Cam_20fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('GRAY16', 640, 480)],
        FRAMERATE_RANGE_STR: (1, 20)
    },
    'Single_Fish_Spontaneous_1_115fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480)],
        FRAMERATE_RANGE_STR: (20, 115)
    },
    'Single_Fish_Spontaneous_2_115fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('RGB8', 640, 480),
                     camera_device.CameraFormat('GRAY8', 752, 480),
                     camera_device.CameraFormat('GRAY8', 640, 480)],
        FRAMERATE_RANGE_STR: (5, 115)
    },
    'Single_Fish_Spontaneous_3_115fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('RGB8', 640, 480),
                     camera_device.CameraFormat('GRAY8', 752, 480),
                     camera_device.CameraFormat('GRAY8', 640, 480)],
        FRAMERATE_RANGE_STR: (5, 20)
    },
    'Single_Fish_Spontaneous_4_115fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('RGB8', 640, 480),
                     camera_device.CameraFormat('GRAY8', 752, 480),
                     camera_device.CameraFormat('GRAY8', 640, 480)],
        FRAMERATE_RANGE_STR: (5, 20)
    },
    'Single_Fish_Spontaneous_1_30fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480),
                     camera_device.CameraFormat('RGB8', 640, 480), ],
        FRAMERATE_RANGE_STR: (5, 20)
    },
    'Single_Fish_Free_Swim_Dot_Chased_50fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480)],
        FRAMERATE_RANGE_STR: (5, 20)
    },
    'Single_Fish_Free_Swim_On_random_motion_100fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480)],
        FRAMERATE_RANGE_STR: (5, 20)
    },
    'Single_Fish_OKR_embedded_30fps': {
        FORMAT_STR: [camera_device.CameraFormat('RGB8', 752, 480)],
        FRAMERATE_RANGE_STR: (5, 20)
    }
}


def _get_filepath():
    uncompr_path = os.path.join(PATH_SAMPLE, _sample_filename_full)
    if os.path.exists(uncompr_path):
        return uncompr_path
    return os.path.join(PATH_SAMPLE, _sample_filename_compressed)


class CameraDevice(camera_device.AbstractCameraDevice):

    manufacturer = 'Virtual'

    sink_formats = {'RGB8': (3, np.uint8),
                    'Y800': (3, np.uint8),
                    'GRAY8': (1, np.uint8),
                    'GRAY16': (1, np.uint16)}

    def __init__(self, *args, **kwargs):
        camera_device.AbstractCameraDevice.__init__(self, *args, **kwargs)

        self.t_start = None
        self.t_last = None
        self.i_last = None
        self.f_last = None
        self.res_x = None
        self.res_y = None
        self._data = None
        self._cap = None
        self._fps = None
        self.index = None
        self._h5: Union[h5py.File, None] = None

    def start_stream(self):

        if self.format is None:
            log.error(f'Tried starting camera stream of {self} without format set.')
            return False

        try:
            log.debug(f'Open {_get_filepath()}')
            self._h5 = h5py.File(_get_filepath(), 'r')

            if self.model not in self._h5:
                return False

            self._cap = self._h5[self.model]
            if self.info['preload_file']:
                log.debug('Preload frame data')
                _format = self.format.dtype
                self._data = self._cap[:]
            self.index = 0
            self.res_x, self.res_y = self.format.width, self.format.height

        except Exception as exc:
            log.error(f'Failed to set up virtual camera. // {exc}')
            return False

        else:
            return True

    def end_stream(self):
        if self._h5 is not None:
            self._h5.close()

    def snap_image(self, *args, **kwargs):
        pass

    def get_image(self):
        self.index += 1
        if self._cap.shape[0] <= self.index:
            self.index = 0

        _format = self.sink_formats[self.format.dtype]
        if self.info['preload_file']:
            # From preloaded data
            frame = self._data[self.index][:self.res_y, :self.res_x]

        else:
            # From dataset
            frame = self._cap[self.index][:self.res_y, :self.res_x]

        return np.asarray(frame, dtype=_format[1])

    def get_format_list(self) -> List[CameraFormat]:
        return _models[self.model][FORMAT_STR]

    def _framerate_range(self, _format: CameraFormat) -> Tuple[float, float]:
        """Format not necessary for virtual camera framerate range"""
        return _models[self.model][FRAMERATE_RANGE_STR]

    @classmethod
    def get_camera_list(cls) -> List[AbstractCameraDevice]:
        devices = []

        for sn, m in enumerate(_models.keys()):
            devices.append(CameraDevice(serial=f'{sn:05d}', model=m))

        return devices


if __name__ == '__main__':
    pass
