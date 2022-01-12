"""
MappApp .devices/virtual_daq.py
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
import time
import numpy as np

from vxpy.core import logging

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, AnyStr, Union

log = logging.getLogger(__name__)


class Pin:

    def __init__(self, pid, config):
        self.pid = pid
        self.config = config
        self.offset = np.random.randint(4)
        self.fun = np.sin
        self.value = None
        self.is_out = self.config['type'] in ('do', 'ao')

        if 'sawtooth' in self.pid:
            self.fun = lambda t: - 2 * 1. / np.pi * np.arctan(1. / np.tan(np.pi * t / 4.)) + np.random.rand() / 3.
        elif 'rectangular' in self.pid:
            self.fun = lambda t: float(np.sin(t) > 0) + np.random.rand() / 3.

    def _read_data(self):
        self.value = self.fun(time.time() + self.offset / 20 * 2 * np.pi * 1.0)

    def read(self):
        return self.value

    def write(self, value):
        if self.is_out:
            self.value = value
            # print(f'Write to pin {self.pid}:{value}')
        else:
            log.warning(f'Trying to write to input pin {self.pid}')


class VirtualDaqDevice:

    def __init__(self, config):
        self.config = config
        self.pins: Dict[AnyStr, Pin] = dict()
        self.pin_data: Dict[AnyStr, Union[int,float]] = dict()

    def configure_pin(self, pin_id, pin_config):
        self.pins[pin_id] = Pin(pin_id, pin_config)

    def write(self, pid, data):
        """Write data to output pin"""
        self.pins[pid].write(data)

    def read(self, pid):
        """Read (stored) pin data for input pin"""
        return self.pin_data[pid]

    def read_all(self):
        """Read (stored) pin data for all input pins"""
        return self.pin_data

    def read_device_data(self):
        """Read current data on device's input pins and save data temporarily"""
        self.pin_data.update({pid: pin.read() for pid, pin in self.pins.items() if pin.config['type'] in ('di', 'ai')})