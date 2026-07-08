"""Core module for serial and DAQ devices.

Provides base classes for serial communication devices (:class:`SerialDevice`)
and data acquisition devices (:class:`DaqDevice`, :class:`DaqPin`), together
with helper functions for looking up and reading/writing pins.
"""
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


def get_serial_interface(api_path: str) -> Union[Type['SerialDevice'], Type['DaqDevice'], None]:
    """Get serial interface.
    
    Parameters
    ----------
    api_path : str
        Description.
    
    Returns
    -------
    Union[Type['SerialDevice'], Type['DaqDevice'], None]
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

    if not issubclass(device_cls, (SerialDevice, DaqDevice)):
        log.error(f'Device of interface {api_path} is not a {SerialDevice.__name__}')
        return None

    return device_cls


def get_serial_device_by_id(device_id: str) -> Union['SerialDevice', 'DaqDevice', None]:
    """Get serial device by id.
    
    Parameters
    ----------
    device_id : str
        Description.
    
    Returns
    -------
    Union['SerialDevice', 'DaqDevice', None]
        Description.
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

    return _device


def get_pin(pin_id: str) -> Union['DaqPin', None]:
    """Get pin.
    
    Parameters
    ----------
    pin_id : str
        Description.
    
    Returns
    -------
    Union['DaqPin', None]
        Description.
    """
    global daq_pins
    return daq_pins.get(pin_id, None)


_write_pin_error_log = []


def write_pin(pin_id: str, value: Union[bool, int, float]):
    """Write pin.
    
    Parameters
    ----------
    pin_id : str
        Description.
    value : Union[bool, int, float]
        Description.
    """
    pin = get_pin(pin_id)
    if pin is None and pin not in _write_pin_error_log:
        log.error(f'Failed to write to pin {pin}. Does not exist')
        _write_pin_error_log.append(pin)
        return
    pin.write(value)


_read_pin_error_log = []


def read_pin(pin_id: str) -> Union[bool, int, float, None]:
    """Read pin.
    
    Parameters
    ----------
    pin_id : str
        Description.
    
    Returns
    -------
    Union[bool, int, float, None]
        Description.
    """
    pin = get_pin(pin_id)
    if pin is None and pin not in _read_pin_error_log:
        log.error(f'Failed to read from pin {pin}. Does not exist')
        _read_pin_error_log.append(pin)
        return
    return pin.attribute.read()[-1]


class PINSIGDIR(Enum):
    """PINSIGDIR class."""
    INPUT = 1
    OUTPUT = 2


class PINSIGTYPE(Enum):
    """PINSIGTYPE class."""
    ANALOG = 1
    DIGITAL = 2
    PWM = 3


def get_pin_prefix(pin: 'DaqPin') -> str:
    """Get pin prefix.
    
    Parameters
    ----------
    pin : 'DaqPin'
        Description.
    
    Returns
    -------
    str
        Description.
    """
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
    """DaqPin class."""

    signal_direction: PINSIGDIR = None
    signal_type: PINSIGTYPE = None
    attribute: vxattribute.ArrayAttribute = None
    _new_write_value_proxy = None

    def __init__(self, pin_id: str, board: 'DaqDevice', properties: Dict[str, Any]):
        """  init  .
        
        Parameters
        ----------
        pin_id : str
            Description.
        board : 'DaqDevice'
            Description.
        properties : Dict[str, Any]
            Description.
        """
        self.pin_id: str = pin_id
        self._board: DaqDevice = board
        self.properties: Dict[str, Any] = properties

        global daq_pins
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
        """  repr  .
        """
        return f'{self.__class__.__name__}(\'{self.pin_id}\', {self.signal_type}, {self.signal_direction})'

    @abc.abstractmethod
    def initialize(self):
        """Initialize.
        """
        pass

    def write(self, value):
        """Write.
        
        Parameters
        ----------
        value : Any
            Description.
        """
        self._new_write_value_proxy.value = value

    @abc.abstractmethod
    def _write_hw(self, value):
        """ write hw.
        
        Parameters
        ----------
        value : Any
            Description.
        """

    def write_hw(self):
        """Write hw.
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
        """ read hw.
        
        Returns
        -------
        Union[bool, int, float]
            Description.
        """

    def read_hw(self) -> None:
        """Read hw.
        """
        self.attribute.write(self._read_hw())


class DaqDevice:
    """DaqDevice class."""

    def __init__(self, device_id, **kwargs):
        """  init  .
        
        Parameters
        ----------
        device_id : Any
            Description.
        **kwargs : Any
            Description.
        """
        self.device_id: str = device_id
        self.properties: Dict[str, Any] = kwargs
        self.pins: Dict[str, DaqPin] = {}

        # Add device to global dictionary
        global devices
        devices[self.device_id] = self

    def __repr__(self):
        """  repr  .
        """
        return f'{self.__class__.__name__}(\'{self.device_id}\')'

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
    def _setup_pins(self):
        """ setup pins.
        """
        pass

    def setup_pins(self) -> None:
        """Setup pins.
        """
        if len(self.pins) > 0:
            log.error(f'Tried to re-run pin setup for {self}')
            return
        self._setup_pins()

    @abc.abstractmethod
    def _start(self) -> bool:
        """ start.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def start(self) -> bool:
        """Start.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._start()

        except Exception as exc:
            log.error(f'Failed to start stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def _end(self) -> bool:
        """ end.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def end(self) -> bool:
        """End.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._end()

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
        try:
            return self._close()

        except Exception as exc:
            log.error(f'Failed to close {self}: {exc}')
            return False


class SerialDevice(abc.ABC):
    """SerialDevice class."""

    def __init__(self, device_id: str, **kwargs):
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

        # Add device to global dictionary
        global devices
        devices[self.device_id] = self

    def __repr__(self):
        """  repr  .
        """
        return f'{SerialDevice.__name__}::{self.__class__.__name__}({self.device_id})'

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
    def _start(self) -> bool:
        """ start.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def start(self) -> bool:
        """Start.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._start()

        except Exception as exc:
            log.error(f'Failed to start stream {self}: {exc}')
            return False

    @abc.abstractmethod
    def _end(self) -> bool:
        """ end.
        
        Returns
        -------
        bool
            Description.
        """
        pass

    def end(self) -> bool:
        """End.
        
        Returns
        -------
        bool
            Description.
        """
        try:
            return self._end()

        except Exception as exc:
            log.error(f'Failed to end {self}: {exc}')
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

