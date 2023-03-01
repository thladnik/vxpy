from __future__ import annotations
import abc
import importlib
from enum import Enum
from typing import Dict, Any, Type, Union, Iterator, Tuple, List

import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
from vxpy import config

log = vxlogger.getLogger(__name__)

# Dictionary to hold all configured devices
devices: Dict[str, Union[SerialDevice, DaqDevice]] = {}
daq_pins: Dict[str, DaqPin] = {}


def get_serial_interface(api_path: str) -> Union[Type[SerialDevice], Type[DaqDevice], None]:
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

    if not issubclass(device_cls, (SerialDevice, DaqDevice)):
        log.error(f'Device of interface {api_path} is not a {SerialDevice.__name__}')
        return None

    return device_cls


def get_serial_device_by_id(device_id: str) -> Union[SerialDevice, DaqDevice, None]:
    """Fetch the device by its string identifier"""
    # Get camera properties from config
    device_props = config.IO_DEVICES.get(device_id)

    # Camera not configured?
    if device_props is None:
        return None

    # Get camera api class
    api_cls = get_serial_interface(device_props['api'])

    # Return the camera api object
    return api_cls(device_id, **device_props)


class PINSIGDIR(Enum):
    IN = 1
    OUT = 2


class PINSIGTYPE(Enum):
    ANALOG = 1
    DIGITAL = 2


class DaqPin:

    signal_direction: PINSIGDIR = None
    signal_type: PINSIGTYPE = None

    def __init__(self, pin_id: str, board: DaqDevice, properties: Dict[str, Any]):
        self.pin_id: str = pin_id
        self._board: DaqDevice = board
        self.properties: Dict[str, Any] = properties

        global daq_pins
        # Checking if pin has been created does not work on Unix
        # (forked subprocesses already get updated module with serial DAQ pin list from controller)
        # if self.pin_id in daq_pins:
        #     log.error(f'Tried setting up {self} more than once')
        #     return
        daq_pins[self.pin_id] = self

    def __repr__(self):
        return f'{self.__class__.__name__}(\'{self.pin_id}\', {self.signal_type}, {self.signal_direction})'

    @abc.abstractmethod
    def initialize(self):
        pass

    @abc.abstractmethod
    def write(self, value) -> bool:
        pass

    @abc.abstractmethod
    def read(self) -> Union[bool, int, float]:
        pass


class DaqDevice:
    """Base class of a DAQ device"""

    def __init__(self, device_id, **kwargs):
        self.device_id: str = device_id
        self.properties: Dict[str, Any] = kwargs
        self._pins: Dict[str, DaqPin] = {}

        # Add device to global dictionary
        global devices
        # Checking if device has been created does not work on Unix
        # (forked subprocesses already get updated module with serial device list from controller)
        # if self.device_id in devices:
        #     log.error(f'Tried setting up device {self} more than once')
        #     return
        devices[self.device_id] = self

    def __repr__(self):
        return f'{self.__class__.__name__}(\'{self.device_id}\')'

    @abc.abstractmethod
    def _open(self) -> bool:
        pass

    def open(self) -> bool:

        try:
            return self._open()

        except Exception as exc:
            log.error(f'Failed to open {self}: {exc}')
            return False

    def get_pins(self) -> List[Tuple[str, DaqPin]]:
        """"""
        if len(self._pins) == 0:
            self._setup_pins()

        return [(pin_id, pin) for pin_id, pin in self._pins.items()]

    @abc.abstractmethod
    def _setup_pins(self) -> None:
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


class SerialDevice:
    """Base class of any serial device"""

    def __init__(self, device_id, baud_rate, **kwargs):
        self.device_id: str = device_id
        self.baud_rate: int = baud_rate
        self.properties: Dict[str, Any] = kwargs

        # Add device to global dictionary
        global devices
        # Checking if device has been created does not work on Unix
        # (forked subprocesses already get updated module with serial device list from controller)
        # if self.device_id in devices:
        #     log.error(f'Tried setting up device {self} more than once')
        #     return
        devices[self.device_id] = self

    def __repr__(self):
        return f'{SerialDevice.__name__}::{self.__class__.__name__}({self.device_id})'

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
            log.error(f'Failed to end {self}: {exc}')
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
