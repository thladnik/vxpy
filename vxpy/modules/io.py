""" General purpose digital/analog input/output module
"""
import importlib
import time
from typing import Dict, Union, Any

import numpy as np

from vxpy.api.attribute import read_attribute
from vxpy import config
from vxpy.definitions import *
import vxpy.core.attribute as vxattribute
import vxpy.core.container as vxcontainer
import vxpy.core.control as vxcontrol
import vxpy.core.ipc as vxipc
import vxpy.core.process as vxprocess
import vxpy.core.logger as vxlogger
import vxpy.core.ui as vxui
import vxpy.core.devices.serial as vxserial


log = vxlogger.getLogger(__name__)


class Io(vxprocess.AbstractProcess):
    name = PROCESS_IO

    # Protocol settings
    current_control: Union[vxcontrol.BaseControl, None] = None
    fallback_phase_counter = 0

    # Device settings
    _pin_id_attr_map: Dict[str, str] = {}
    _daq_pins: Dict[str, vxserial.DaqPin] = {}
    _serial_devices: Dict[str, vxserial.SerialDevice] = {}
    _daq_devices: Dict[str, vxserial.DaqDevice] = {}

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        # Configure devices
        for device in vxserial.devices.values():

            # If device is a DAQ device
            if isinstance(device, vxserial.DaqDevice):

                # Add DAQ device
                self._daq_devices[device.device_id] = device

            # If device is a generic Serial device
            elif isinstance(device, vxserial.SerialDevice):

                # Add serial device
                self._serial_devices[device.device_id] = device
            else:
                log.warning(f'Unknown {device}. Device was set up but may not be usable.')

            # Open device
            try:
                device.open()

            except Exception as exc:
                log.error(f'Failed to open {device} // Exc: {exc}')
                import traceback
                print(traceback.print_exc())
                continue

            # Start device
            try:
                device.start()

            except Exception as exc:
                log.error(f'Failed to start {device} // Exc: {exc}')
                import traceback
                print(traceback.print_exc())
                continue

        # Configure pins
        for daq_device in self._daq_devices.values():

            # Add configured pins on device
            for pin in daq_device.pins.values():
                log.info(f'Initialize {pin}')

                # Initialize pin
                pin.initialize()

                # Save pin to dictionary
                self._daq_pins[pin.pin_id] = pin

                # Add pin data to be written to file
                vxattribute.write_to_file(self, pin.attribute.name)

                vxui.register_with_plotter(pin.attribute.name, axis=vxserial.get_pin_prefix(pin))

        # Allow timeout during idle
        # self.enable_idle_timeout = True

        self.TEST_time = vxipc.get_time()
        # Run event loop
        self.run(interval=1. / config.IO_MAX_SR)
    #
    # def execute_serial_device_call(self, device_id: str, fun: str, *args, **kwargs):
    #
    #     _device = self._serial_devices[device_id]
    #
    #     # Check if it exists
    #     if not hasattr(_device, fun):
    #         log.error(f'Failed to call {fun} on device {_device}')
    #         return
    #
    #     # Call function
    #     getattr(_device, fun)(*args, *kwargs)

    def prepare_trigger_protocol(self):
        # Create all controls during protocol preparation (ahead of protocol run)
        #  This may come with some initial overhead, but reduces latency between stimulation phases
        self.current_protocol.create_controls()

    def prepare_static_protocol(self):
        # Create all controls during protocol preparation (ahead of protocol run)
        #  This may come with some initial overhead, but reduces latency between stimulation phases
        self.current_protocol.create_controls()

    def prepare_trigger_protocol_phase(self):
        # Prepare visual associated with phase
        self.prepare_control()

    def prepare_static_protocol_phase(self):
        # Prepare visual associated with phase
        self.prepare_control()

    def prepare_control(self, control: vxcontrol.BaseControl = None, parameters: dict = None):

        if control is None:
            control = self.current_protocol.current_phase.control

            if control is None:
                return

        # Prepare parameters
        if parameters is None:
            if self.current_protocol is None:
                parameters = {}
            else:
                # Fetch protocol-defined parameters
                parameters = self.current_protocol.current_phase.control_parameters

        self.current_control = control
        self.update_control(parameters)

        # Create dataset for global time
        vxcontainer.create_phase_dataset('__time', (1,), np.float64)

        # Set phase attributes
        attributes = {
            '__target_start_time': self.phase_start_time,
            '__target_end_time': self.phase_end_time,
            '__target_sample_rate': config.DISPLAY_FPS,
            '__visual_module': self.current_control.__module__,
            '__visual_name': str(self.current_control.__class__.__qualname__)
        }
        vxcontainer.add_phase_attributes(attributes)

    def update_control(self, parameters: Dict[str, Any]):
        self.current_control.update(parameters)

    def start_trigger_protocol_phase(self):
        self.start_control()

    def start_static_protocol_phase(self):
        self.start_control()

    def start_control(self):
        if self.current_control is None:
            return

        self.current_control.initialize()
        self.current_control.start()

    def end_static_protocol_phase(self):
        if self.current_control is None:
            return

        self.current_control.end()
        self.current_control = None

    def end_trigger_protocol_phase(self):
        if self.current_control is None:
            return

        self.current_control.end()
        self.current_control = None

    def set_outpin_to_attr(self, pin_id, attr_name):
        """Connect an output pin ID to a shared attribute. Attribute will be used as data to be written to pin."""

        log.info(f'Set attribute "{attr_name}" to write to pin {pin_id}')

        # Check of pid is actually configured
        if pin_id not in self._daq_pins:
            log.warning(f'Output "{pin_id}" is not configured. Cannot connect to attribute {attr_name}')
            return

        # Select pin
        pin = self._daq_pins[pin_id]

        # Check if pin is configured as output
        if pin.signal_direction != vxserial.PINSIGDIR.OUTPUT:
            log.warning(f'Pin {pin} cannot be configured as output. Not an output channel.')
            return

        # Check if attribute exists
        if not attr_name in vxattribute.Attribute.all:
            log.warning(f'Pin "{pin_id}" cannot be set to attribute {attr_name}. Attribute does not exist.')

        if pin_id not in self._pin_id_attr_map:
            log.info(f'Set pin {pin} to attribute "{attr_name}"')
            self._pin_id_attr_map[pin_id] = attr_name
        else:

            log.warning(f'Pin {pin} is already set.')

    def main(self, dt: float):

        if self.current_control is not None and self.current_control.is_active:
            self.current_control.main(dt)

        # Go through all configured pins
        for pin in self._daq_pins.values():

            # Read input pins
            if pin.signal_direction == vxserial.PINSIGDIR.INPUT:
                pin.read_hw()

            # Write output pins
            else:
                pin.write_hw()

        # Run routines
        self.update_routines(**self._daq_pins)

        # Add global time
        vxcontainer.add_to_phase_dataset('__time', vxipc.get_time())

    def _start_shutdown(self):

        # Make sure devices are disconnected before shutting down process
        for device in [*self._serial_devices.values(), *self._daq_devices.values()]:
            device.end()
            device.close()

        vxprocess.AbstractProcess._start_shutdown(self)
