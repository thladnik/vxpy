from __future__ import annotations
import abc
import importlib
from typing import Dict, Any, Type, Union, Iterator

import vxpy.core.logger as vxlogger
from vxpy import config

log = vxlogger.getLogger(__name__)


def get_serial_interface(api_path: str) -> Union[Type[SerialDevice], None]:
    """Fetch the specified serial device API class from given path.
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

    if not issubclass(device_cls, SerialDevice):
        log.error(f'Device of interface {api_path} is not a {SerialDevice.__name__}')
        return None

    return device_cls


def get_serial_device_by_id(device_id: str) -> Union[SerialDevice, None]:
    """Fetch the device by its string identifier"""
    # Get camera properties from config
    device_props = config.CONF_IO_DEVICES.get(device_id)

    # Camera not configured?
    if device_props is None:
        return None

    # Get camera api class
    api_cls = get_serial_interface(device_props['api'])

    # Return the camera api object
    return api_cls(device_id, **device_props)


class SerialDevicePin:

    @abc.abstractmethod
    def write(self) -> bool:
        pass

    @abc.abstractmethod
    def read(self) -> Union[bool, int, float]:
        pass


class SerialDevice:
    """Base class of any serial device"""

    def __init__(self, device_id, baud_rate, **kwargs):
        self.device_id: str = device_id
        self.baud_rate: int = baud_rate
        self.properties: Dict[str, Any] = kwargs

    def __repr__(self):
        return f'{SerialDevice.__name__}::{self.__class__.__name__}'

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
    def get_pins(self) -> Iterator[str, SerialDevicePin]:
        pass

    @abc.abstractmethod
    def _start(self) -> bool:
        pass

    def start(self) -> bool:

        try:
            return self._start()

        except Exception as exc:
            log.error(f'Failed to start stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def _end(self) -> bool:
        pass

    def end(self) -> bool:

        try:
            return self._end()

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
