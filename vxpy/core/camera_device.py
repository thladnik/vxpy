from __future__ import annotations
from abc import ABC, abstractmethod
import importlib
import numpy as np
from typing import Any, Dict, Tuple, Type, Union, List

# from vxpy.core import logging

# log = logging.getLogger(__name__)


def get_camera(device_config: dict) -> AbstractCameraDevice:

    # Import api
    _module = importlib.import_module({device_config['api']})
    camera_class = getattr(_module, 'CameraDevice')

    #  Set up camera using configuration
    camera = camera_class(**device_config)

    return camera


class AbstractCameraDevice(ABC):
    manufacturer: str = None

    sink_formats: Dict[str, Tuple[int, Type[np.dtype]]] = None

    # E.g. sink_formats = {'BGRA': (4, np.uint8),
    #                      'GRAY8': (1, np.uint8),
    #                      'GRAY16': (1, np.uint16)}

    def __init__(self, serial, model,
                 _format=None,
                 dtype=None,
                 width=None,
                 height=None,
                 framerate=None,
                 exposure=None,
                 gain=None,
                 **info):

        self.serial = serial
        self.model = model
        self.set_format(_format, dtype, width, height)
        self.framerate = framerate
        self.exposure = exposure
        self.gain = gain
        self.info = info

    def __repr__(self):
        return f'Camera {self.manufacturer}({self.model}, {self.serial}) @ {self.format}'

    @property
    def exposure(self) -> float:
        return self._exposure

    @exposure.setter
    def exposure(self, value) -> None:
        self._exposure = value

    @property
    def gain(self) -> float:
        return self._gain

    @gain.setter
    def gain(self, value: float) -> None:
        self._gain = value

    @property
    def framerate(self) -> float:
        return self._framerate

    @framerate.setter
    def framerate(self, value: float) -> None:
        self._framerate = value

    def set_format(self,
                   fmt: Union[CameraFormat, None] = None,
                   dtype: Union[str, None] = None,
                   width: Union[int, None] = None,
                   height: Union[int, None] = None) -> None:

        if fmt is None and all([p is not None for p in [dtype, width, height]]):
            fmt = CameraFormat(dtype, width, height)

        self.format = fmt

    @abstractmethod
    def get_format_list(self) -> List[CameraFormat]:
        pass

    @classmethod
    @abstractmethod
    def get_camera_list(cls) -> List[Type[AbstractCameraDevice]]:
        pass


class CameraFormat:

    def __init__(self, dtype: Any, width: int, height: int):
        self.dtype = dtype
        self.width = width
        self.height = height

    def __repr__(self):
        return f'{self.dtype}({self.width}x{self.height})'

    @staticmethod
    def from_str(fmt_str: str) -> CameraFormat:
        substr = fmt_str[0].split('(')
        f = substr[0]
        w, h = [int(i) for i in substr[-1].strip(')').split('x')]

        return CameraFormat(f, w, h)


if __name__ == '__main__':
    print()
