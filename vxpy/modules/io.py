"""
MappApp ./modules/display_calibration.py - General purpose digital/analog input/output modules.
Copyright (C) 2020 Tim Hladnik

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
import importlib
import time
from typing import Dict

import numpy as np

from vxpy.api.attribute import read_attribute
from vxpy import config
from vxpy.definitions import *
import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.process as vxprocess
import vxpy.core.logger as vxlogger
import vxpy.core.ui as vxui
import vxpy.core.devices.serial as vxserial

log = vxlogger.getLogger(__name__)


class Io(vxprocess.AbstractProcess):
    name = PROCESS_IO

    _pin_id_attr_map: Dict[str, str] = {}
    _daq_pins: Dict[str, vxserial.DaqPin] = {}
    _serial_devices: Dict[str, vxserial.SerialDevice] = {}
    _daq_devices: Dict[str, vxserial.DaqDevice] = {}

    @staticmethod
    def get_pin_prefix(pin: vxserial.DaqPin) -> str:
        if pin.signal_type == vxserial.PINSIGTYPE.ANALOG:
            if pin.signal_direction == vxserial.PINSIGDIR.IN:
                prefix = 'ai'
            else:
                prefix = 'ao'
        else:
            if pin.signal_direction == vxserial.PINSIGDIR.IN:
                prefix = 'di'
            else:
                prefix = 'do'

        return prefix

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        # Configure devices
        for device_id, dev_config in config.IO_DEVICES.items():

            api_path = dev_config['api']
            if api_path is None:
                log.error(f'Could not configure device {device_id}. No API provided.')
                continue

            # Get device API
            device = vxserial.get_serial_device_by_id(device_id)
            log.info(f'Set up device {device_id}: {device}')

            # If device is a DAQ device
            if isinstance(device, vxserial.DaqDevice):

                # Add DAQ device
                self._daq_devices[device_id] = device

            # If device is a generic Serial device
            elif isinstance(device, vxserial.SerialDevice):

                # Add serial device
                self._serial_devices[device_id] = device
            else:
                log.warning(f'Unknown device {device_id}. Device was set up but may not be usable.')

            # Open device
            try:
                device.open()

            except Exception as exc:
                log.error(f'Failed to open device {device_id} // Exc: {exc}')
                import traceback
                print(traceback.print_exc())
                continue

            # Start device
            try:
                device.start()

            except Exception as exc:
                log.error(f'Failed to start device {device_id} // Exc: {exc}')
                import traceback
                print(traceback.print_exc())
                continue

        # Configure pins
        for daq_device in self._daq_devices.values():

            # Add configured pins on device
            for pin_id, pin in daq_device.get_pins():
                if pin_id in self._daq_pins:
                    log.error(f'Pin {pin_id} is already configured. Unable to add to device {daq_device}')
                    continue

                # Initialize pin
                pin.initialize()

                # Save pin to dictionary
                self._daq_pins[pin_id] = pin

                # Add pin data to be written to file
                prefix = self.get_pin_prefix(pin)
                attr_name = f'{prefix}_{pin_id}'
                vxattribute.write_to_file(self, attr_name)

                vxui.register_with_plotter(attr_name, axis=prefix)

        # Allow timeout during idle
        # self.enable_idle_timeout = True

        self.timetrack = []
        # Run event loop
        self.run(interval=1. / config.IO_MAX_SR)

    def prepare_static_protocol(self):
        # Initialize actions related to protocol
        self.current_protocol.initialize_actions()

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
        if pin.signal_direction != vxserial.PINSIGDIR.OUT:
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

    def main(self):

        tt = []

        # # Read data on pins once
        # t = time.perf_counter()
        # for pin in self._daq_pins.values():
        #     pin._read_data()
        # tt.append(time.perf_counter()-t)

        # Go through all configured pins
        for pin_id, pin in self._daq_pins.items():

            prefix = self.get_pin_prefix(pin)

            # Read input pins
            if pin.signal_direction == vxserial.PINSIGDIR.IN:
                input_attr_name = f'{prefix}_{pin_id}'
                vxattribute.write_attribute(input_attr_name, pin.read())

            # Write output pins
            else:
                # Write attribute data to output pins if mapped
                if pin_id in self._pin_id_attr_map:
                    output_attr_name = self._pin_id_attr_map[pin_id]
                    _, _, vals = read_attribute(output_attr_name)
                    self._daq_pins[pin_id].write(vals[0][0])

        # Run routines
        self.update_routines(**self._daq_pins)

    def _start_shutdown(self):

        # Make sure devices are disconnected before shutting down process
        for device in [*self._serial_devices.values(), *self._daq_devices.values()]:
            device.end()
            device.close()

        vxprocess.AbstractProcess._start_shutdown(self)
