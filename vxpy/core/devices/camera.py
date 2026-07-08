"""Core camera device module for vxPy.

Provides the abstract :class:`CameraDevice` base class and helper functions
for loading camera device implementations from their fully qualified import
paths.
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
    """Get camera interface.
    
    Parameters
    ----------
    api_path : str
        Description.
    
    Returns
    -------
    Union[Type[CameraDevice], None]
        Description.
    """

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
    """Get camera by id.
    
    Parameters
    ----------
    device_id : Any
        Description.
    
    Returns
    -------
    Union[CameraDevice, None]
        Description.
    """
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
    """CameraDevice class."""

    def __init__(self, device_id: str = None, **kwargs):
        """  init  .
        
        Parameters
        ----------
        device_id : str
            Description.
        **kwargs : Any
            Description.
        """
        self.device_id: str = device_id
        self.properties: Dict[str, Any] = kwargs

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata.
        
        Returns
        -------
        Dict[str, Any]
            Description.
        """
        return {}

    def get_settings(self) -> Dict[str, Any]:
        """Get settings.
        
        Returns
        -------
        Dict[str, Any]
            Description.
        """
        return {}

    @property
    @abc.abstractmethod
    def frame_rate(self) -> float:
        """Frame rate.
        
        Returns
        -------
        float
            Description.
        """
        pass

    @frame_rate.setter
    @abc.abstractmethod
    def frame_rate(self, value: float) -> bool:
        """Frame rate.
        
        Parameters
        ----------
        value : float
            Description.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    @property
    @abc.abstractmethod
    def width(self) -> int:
        """Width.
        
        Returns
        -------
        int
            Description.
        """
        pass

    @property
    @abc.abstractmethod
    def height(self) -> int:
        """Height.
        
        Returns
        -------
        int
            Description.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_camera_list(cls) -> List['CameraDevice']:
        """Get camera list.
        
        Returns
        -------
        List['CameraDevice']
            Description.
        """
        pass

    @abc.abstractmethod
    def _open(self) -> bool:
        """ open.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def open(self) -> bool:
        """Open.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._open()

        except Exception as exc:
            log.error(f'Failed to open {self}: {exc}')
            return False

    @abc.abstractmethod
    def _start_stream(self) -> bool:
        """ start stream.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def start_stream(self) -> bool:
        """Start stream.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._start_stream()

        except Exception as exc:
            log.error(f'Failed to start stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def next_snap(self) -> bool:
        """Next snap.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    @abc.abstractmethod
    def snap_image(self) -> bool:
        """Snap image.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    @abc.abstractmethod
    def next_image(self) -> bool:
        """Next image.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    @abc.abstractmethod
    def get_image(self) -> np.ndarray:
        """Get image.
        
        Returns
        -------
        np.ndarray
            Description.
        """
        pass

    @abc.abstractmethod
    def _end_stream(self) -> bool:
        """ end stream.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def end_stream(self) -> bool:
        """End stream.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._end_stream()

        except Exception as exc:
            log.error(f'Failed to end stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def _close(self) -> bool:
        """ close.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def close(self) -> bool:
        """Close.
        
        Returns
        -------
        bool
            Description.
        """
        # Try connecting
        try:
            return self._close()

        except Exception as exc:
            log.error(f'Failed to close {self}: {exc}')
            return False
