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
from __future__ import annotations
import time
from typing import Dict, AnyStr, Union, Iterator, Tuple, Callable, Any

import numpy as np

import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.devices.serial as vxserial

log = vxlogger.getLogger(__name__)


def on_off(t, freq, t_offset):
    return int(np.sin(t_offset+t * 2 * np.pi * freq) > 0.)


def sinewave(t, freq, t_offset):
    return np.sin(t_offset+t * 2 * np.pi * freq)


def whitenoise_sinewave(t, freq, t_offset, nlvl):
    return sinewave(t, freq, t_offset) / 2 + (np.random.rand() - 0.5) * 2 * nlvl


class VirtualDaqDevice(vxserial.DaqDevice):

    def get_pin_info(self) -> Iterator[Tuple[str, vxserial.PINSIGTYPE, vxserial.PINSIGDIR]]:
        pass

    def _setup_pins(self) -> None:

        # Set up and yield if not done before
        for pin_id, pin_config in self.properties['pins'].items():
            pin = VirtualDaqPin(pin_id, self, pin_config)

            self.pins[pin_id] = pin

    def _open(self) -> bool:
        return True

    def _start(self) -> bool:
        return True

    def _end(self) -> bool:
        return True

    def _close(self) -> bool:
        return True


class VirtualDaqPin(vxserial.DaqPin):

    _board: VirtualDaqDevice
    _available_methods = {'on_off': on_off,
                          'sinewave': sinewave,
                          'whitenoise_sinewave': whitenoise_sinewave}

    def __init__(self, *args, **kwargs):
        vxserial.DaqPin.__init__(self, *args, **kwargs)

        self._dummy_data = 0
        self.fun: Callable = self._available_methods.get(self.properties.get('fun'))
        self.arguments: Dict[str, Any] = self.properties.get('args', {})

    def initialize(self):
        pass

    def _write_hw(self, value):
        pass

    def _read_hw(self) -> Union[bool, int, float]:
        if self.fun is not None:
            return self.fun(vxipc.get_time(), **self.arguments)
        return self._dummy_data
