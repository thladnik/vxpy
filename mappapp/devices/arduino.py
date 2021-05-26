"""
MappApp ./devices/arduino.py
Copyright (C) 2020 Tim Hladnik, Yue Zhang

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
import pyfirmata

from mappapp import Config
from mappapp import Def
from mappapp import Logging

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, AnyStr, Union

class ArduinoBoard:
    model = 'Arduino'

    class Pin(pyfirmata.Pin):
        def __init__(self, pid, config, *args, **kwargs):
            pyfirmata.Pin.__init__(self, *args, **kwargs)
            self.pid = pid
            self.config = config
            self.data = None
            self.is_out = self.config['type'] in ('do', 'ao')

        def read(self):
            return self.data

        def _read_data(self):
            self.data = pyfirmata.Pin.read(self)

        def write(self, value):
            if self.is_out:
                self.value = value
                pyfirmata.Pin.write(self, value)
            else:
                Logging.write(Logging.WARNING, f'Trying to write to input pin {self.pid}')

    def __init__(self, config):
        self.config = config
        self.pins: Dict[AnyStr, ArduinoBoard.Pin] = dict()
        self.pin_data: Dict[AnyStr, Union[int,float]] = dict()

        # Set up and connect device on configured comport
        _devstr = f'device {config["type"]}>>{config["model"]}'
        try:
            self._board = getattr(pyfirmata, config['model'])(config['com'])
            Logging.write(Logging.INFO, f'Using {_devstr}')
        except:
            Logging.write(Logging.WARNING, f'Failed to set up {_devstr}')

    def configure_pins(self, **pins):
        for pid, config in pins.items():
            Logging.write(Logging.INFO, f"Configure pin {pid} with {config}")
            try:
                self.pins[pid] = self._board.get_pin(config['map'])
            except:
                Logging.write(Logging.WARNING, f"Failed to configure pin {pid} with {config}")

    def write(self, **data):
        for pin_id, pin_data in data.items():
            self.pins[pin_id].write(pin_data)

    def read(self, pid):
        return self.pin_data[pid]

    def read_all(self):
        return self.pin_data

    def read_device_data(self):
        """Read current data on device's input pins and save data temporarily"""
        self.pin_data.update({pid: pin.read() for pid, pin in self.pins.items() if pin.config['type'] in ('di', 'ai')})

class ArduinoNanoBoard(ArduinoBoard):
    model = 'ArduinoNano'


class ArduinoUnoBoard(ArduinoBoard):
    model = 'ArduinoUno'


class ArduinoDueBoard(ArduinoBoard):
    model = 'ArduinoDue'

