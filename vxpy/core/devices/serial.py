from __future__ import annotations
import abc
import importlib
from enum import Enum
from typing import Dict, Any, Type, Union, Iterator, Tuple, List

import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
from vxpy.definitions import *
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


def get_serial_device_by_id(device_id: str) -> Union[SerialDevice, SerialDeviceProxy, DaqDevice, None]:
    """Fetch the device by its string identifier
    """
    global devices
    if device_id in devices:
        return devices[device_id]

    # Get device properties from config
    device_props = config.IO_DEVICES.get(device_id)

    # Device not configured?
    if device_props is None:
        return None


    # Get camera api class
    api_cls = get_serial_interface(device_props['api'])

    # Return the camera api object
    _device = api_cls(device_id, **device_props)

    # # Return proxy, if local process is not IO
    # if vxipc.LocalProcess != PROCESS_IO:
    #     return SerialDeviceProxy(device_id, _device)

    return _device


def get_pin(pin_id: str) -> Union[DaqPin, None]:
    global daq_pins
    return daq_pins.get(pin_id, None)


_write_pin_error_log = []
def write_pin(pin_id: str, value: Union[bool, int, float]):
    pin = get_pin(pin_id)
    if pin is None and pin not in _write_pin_error_log:
        log.error(f'Failed to write to pin {pin}. Does not exist')
        _write_pin_error_log.append(pin)
        return
    pin.write(value)


_read_pin_error_log = []
def read_pin(pin_id: str) -> Union[bool, int, float, None]:
    pin = get_pin(pin_id)
    if pin is None and pin not in _read_pin_error_log:
        log.error(f'Failed to read from pin {pin}. Does not exist')
        _read_pin_error_log.append(pin)
        return
    return pin.attribute.read()[-1]


class PINSIGDIR(Enum):
    INPUT = 1
    OUTPUT = 2


class PINSIGTYPE(Enum):
    ANALOG = 1
    DIGITAL = 2
    PWM = 3


def get_pin_prefix(pin: DaqPin) -> str:
    if pin.signal_type == PINSIGTYPE.ANALOG:
        if pin.signal_direction == PINSIGDIR.INPUT:
            prefix = 'ai'
        else:
            prefix = 'ao'
    elif pin.signal_type == PINSIGTYPE.DIGITAL:
        if pin.signal_direction == PINSIGDIR.INPUT:
            prefix = 'di'
        else:
            prefix = 'do'
    elif pin.signal_type == PINSIGTYPE.PWM:
        if pin.signal_direction == PINSIGDIR.OUTPUT:
            prefix = 'pwm'
        else:
            log.error(f'Unable to configure {pin}. PWM must be ouput')
            prefix = ''
    else:
        log.error(f'Unable to configure {pin}. Unknown configuration')
        prefix = ''

    return prefix


class DaqPin:

    signal_direction: PINSIGDIR = None
    signal_type: PINSIGTYPE = None
    attribute: vxattribute.ArrayAttribute = None
    _new_write_value_proxy = None

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

        success = True
        try:
            self.signal_type = getattr(PINSIGTYPE, self.properties['type'].upper())
        except:
            log.error(f'Unknown type {self.properties["type"]} for {self}')
            success = False
        else:
            try:
                self.signal_direction = getattr(PINSIGDIR, self.properties['direction'].upper())
            except:
                success = False
                log.error(f'Unknown direction {self.properties["direction"]} for {self}')

        if not success:
            log.error(f'Failed to set up {self}')
            return

        # Create shared attribute for pin
        if self.signal_type in [PINSIGTYPE.ANALOG, PINSIGTYPE.PWM]:
            datatype = vxattribute.ArrayType.float64
        else:
            datatype = vxattribute.ArrayType.bool
        self.attribute = vxattribute.ArrayAttribute(f'{get_pin_prefix(self)}_{pin_id}', (1,), datatype)

        # Create ValueProxy for output pins
        if self.signal_direction == PINSIGDIR.OUTPUT:
            _type = int if self.signal_type == PINSIGTYPE.DIGITAL else float
            self._new_write_value_proxy = vxipc.get_manager('io_devices').Value(_type, None)

    def __repr__(self):
        return f'{self.__class__.__name__}(\'{self.pin_id}\', {self.signal_type}, {self.signal_direction})'

    @abc.abstractmethod
    def initialize(self):
        pass

    def write(self, value):
        """Write new value to pin"""
        self._new_write_value_proxy.value = value

    @abc.abstractmethod
    def _write_hw(self, value):
        """Write new value to hardware (to be implemented in DaqPin subclass)
        """

    def write_hw(self):
        """Write new value to hardware (called in Io module)
        """
        # Get value from ValueProxy
        write_value = self._new_write_value_proxy.value
        if write_value is None:
            return

        # Call hardware write implementation
        self._write_hw(write_value)

        # Write same value to attribute
        self.attribute.write(write_value)

    @abc.abstractmethod
    def _read_hw(self) -> Union[bool, int, float]:
        """Read new value from hardware and return it (to be implemented in DaqPin subclass)
        """

    def read_hw(self) -> None:
        """Read new value from hardware (called in Io module)
        """
        self.attribute.write(self._read_hw())


class DaqDevice:
    """Base class of a DAQ device"""

    def __init__(self, device_id, **kwargs):
        self.device_id: str = device_id
        self.properties: Dict[str, Any] = kwargs
        self.pins: Dict[str, DaqPin] = {}

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

    @abc.abstractmethod
    def _setup_pins(self):
        pass

    def setup_pins(self) -> None:
        if len(self.pins) > 0:
            log.error(f'Tried to re-run pin setup for {self}')
            return
        self._setup_pins()

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

    def __init__(self, device_id: str, **kwargs):
        self.device_id: str = device_id
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


# class SerialDeviceProxy:
#
#     def __init__(self, device_id: str, device: SerialDevice):
#         self.device_id: str  = device_id
#         self._device: SerialDevice = device
#
#
#     # def __getattribute__(self, item):
#     #
#     #     # Intercept all function calls
#     #     attr = getattr(self._device, item)
#     #     if hasattr(attr, '__call__'):
#     #         vxipc.io_rpc('execute_serial_device_call', self.device_id)