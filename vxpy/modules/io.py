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
import numpy as np

from vxpy.api.attribute import read_attribute
from vxpy import config
from vxpy import definitions
from vxpy.definitions import *
from vxpy.core import process, ipc, logger
from vxpy.core.attribute import Attribute
from vxpy.core.protocol import get_protocol

log = logger.getLogger(__name__)


class Io(process.AbstractProcess):
    name = PROCESS_IO

    _pid_pin_map = dict()
    _pid_attr_map = dict()
    _devices = dict()

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        # Configure devices
        for did, dev_config in config.CONF_IO_DEVICES.items():
            if not all(k in dev_config for k in ("type", "model", "port")):
                log.warning(f'Insufficient information to configure device {did}')
                continue

            try:
                log.info(f'Set up device {did}: {dev_config["model"]} on port {dev_config["port"]}')
                device_type_module = importlib.import_module(f'{PATH_PACKAGE}.{PATH_DEVICE}.{dev_config["type"]}')
                device_cls = getattr(device_type_module, dev_config["model"])

                self._devices[did] = device_cls(dev_config)

            except Exception as exc:
                log.warning(f'Failed to set up device {did} // Exc: {exc}')
                continue

        # Configure pins
        for pin_id, pin_config in config.CONF_IO_PINS.items():
            device_id = pin_config['device']

            if device_id not in self._devices:
                log.warning(f'Pin {pin_id} could not be mapped to device {device_id}. Device not configured.')
                continue

            log.info(f'Set up pin {pin_id}:{pin_config["device"]}.{pin_config["map"]}')

            self._devices[device_id].configure_pin(pin_id, pin_config)

            # Map pins to flat dictionary
            for pid, pin in self._devices[device_id].pins.items():
                self._pid_pin_map[pid] = pin

        # Set timeout during idle
        self.enable_idle_timeout = True

        self.phase_is_active = 0

        self.timetrack = []
        # Run event loop
        self.run(interval=1. / config.CONF_IO_MAX_SR)

    def prepare_protocol(self):
        # Initialize actions related to protocol
        self.current_protocol.initialize_actions()

    def start_phase(self):
        self.phase_is_active = 1

    def end_phase(self):
        self.phase_is_active = 0

    def set_outpin_to_attr(self, pid, attr_name):
        """Connect an output pin ID to a shared attribute. Attribute will be used as data to be written to pin."""

        log.info(f'Set attribute "{attr_name}" to write to pin {pid}')

        # Check of pid is actually configured
        if pid not in self._pid_pin_map:
            log.warning(f'Output "{pid}" is not configured. Cannot connect to attribute {attr_name}')
            return

        # Select pin
        pin = self._pid_pin_map[pid]

        # Check if pin is configured as output
        if pin.config['type'] not in ('do', 'ao'):
            log.warning(f'{pin.config["type"].upper()}/{pid} cannot be configured as output. Not an output channel.')
            return

        # Check if attribute exists
        if not attr_name in Attribute.all:
            log.warning(f'Pin "{pid}" cannot be set to attribute {attr_name}. Attribute does not exist.')

        if pid not in self._pid_attr_map:

            log.info(f'Set {pin.config["type"].upper()}/{pid} to attribute "{attr_name}"')
            self._pid_attr_map[pid] = attr_name
        else:
            log.warning(f'{pin.config["type"].upper()}/{pid} is already set.')

    def main(self):

        tt = []

        # Read data on pins once
        t = time.perf_counter()
        for pin in self._pid_pin_map.values():
            pin._read_data()
        tt.append(time.perf_counter()-t)

        # Write outputs from connected shared attributes
        t = time.perf_counter()
        for pid, attr_name in self._pid_attr_map.items():
            _, _, vals = read_attribute(attr_name)
            self._pid_pin_map[pid].write(vals[0][0])
        tt.append(time.perf_counter()-t)

        # Update routines with data
        t = time.perf_counter()
        self.update_routines(**self._pid_pin_map)
        tt.append(time.perf_counter()-t)

        self.timetrack.append(tt)
        if len(self.timetrack) >= 5000:
            dts = np.array(self.timetrack)
            means = dts.mean(axis=0) * 1000
            stds = dts.std(axis=0) * 1000
            # print('Read data {:.2f} (+/- {:.2f}) ms'.format(means[0], stds[0]))
            # print('Write data {:.2f} (+/- {:.2f}) ms'.format(means[1], stds[1]))
            # print('Update routines {:.2f} (+/- {:.2f}) ms'.format(means[2], stds[2]))
            # print('----')
            self.timetrack = []
