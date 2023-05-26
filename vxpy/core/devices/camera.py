"""
vxPy ./core/devices/camera.py
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
from __future__ import annotations
import abc
import importlib

from typing import Dict, List, Any, Type, Union

import numpy as np

import vxpy.core.logger as vxlogger
from vxpy import config

log = vxlogger.getLogger(__name__)


def get_camera_interface(api_path: str) -> Union[Type[CameraDevice], None]:
    """Fetch the specified camera API class from given path.
    API class should be a subclass of CameraDevice"""

    try:
        parts = api_path.split('.')
        mod = importlib.import_module('.'.join(parts[:-1]))

    except Exception as exc:
        log.error(f'Unable to load interface from {api_path}')
        import traceback
        print(traceback.print_exc())

        return None

    device_cls = getattr(mod, parts[-1])

    if not issubclass(device_cls, CameraDevice):
        log.error(f'Device of interface {api_path} is not a {CameraDevice.__name__}')
        return None

    return device_cls


def get_camera_by_id(device_id) -> Union[CameraDevice, None]:
    """Fetch the camera """
    # Get camera properties from config
    camera_props = config.CAMERA_DEVICES.get(device_id)

    # Camera not configured?
    if camera_props is None:
        return None

    # Get camera api class
    api_cls = get_camera_interface(camera_props['api'])

    # Return the camera api object
    return api_cls(device_id, **camera_props)


class CameraDevice(abc.ABC):
    """Abstract camera device class. Should be inherited by all camera devices"""

    def __init__(self, device_id: str = None, **kwargs):
        self.device_id: str = device_id
        self.properties: Dict[str, Any] = kwargs

    def get_metadata(self) -> Dict[str, Any]:
        return {}

    def get_settings(self) -> Dict[str, Any]:
        return {}

    @property
    @abc.abstractmethod
    def frame_rate(self) -> float:
        pass

    @frame_rate.setter
    @abc.abstractmethod
    def frame_rate(self, value: float) -> bool:
        pass

    @property
    @abc.abstractmethod
    def width(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def height(self) -> int:
        pass

    @classmethod
    @abc.abstractmethod
    def get_camera_list(cls) -> List[CameraDevice]:
        pass

    @abc.abstractmethod
    def _open(self) -> bool:
        pass

    def open(self) -> bool:

        try:
            return self._open()

        except Exception as exc:
            log.error(f'Failed to open {self}: {exc}')
            return False

    @abc.abstractmethod
    def _start_stream(self) -> bool:
        pass

    def start_stream(self) -> bool:

        try:
            return self._start_stream()

        except Exception as exc:
            log.error(f'Failed to start stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def next_snap(self) -> bool:
        pass

    @abc.abstractmethod
    def snap_image(self) -> bool:
        pass

    @abc.abstractmethod
    def next_image(self) -> bool:
        pass

    @abc.abstractmethod
    def get_image(self) -> np.ndarray:
        pass

    @abc.abstractmethod
    def _end_stream(self) -> bool:
        pass

    def end_stream(self) -> bool:

        try:
            return self._end_stream()

        except Exception as exc:
            log.error(f'Failed to end stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def _close(self) -> bool:
        pass

    def close(self) -> bool:

        # Try connecting
        try:
            return self._close()

        except Exception as exc:
            log.error(f'Failed to close {self}: {exc}')
            return False
