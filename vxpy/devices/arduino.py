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
import traceback

import pyfirmata

from vxpy.core import logging

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, Union

log = logging.getLogger(__name__)


class Pin:
    def __init__(self, board, pid, config):
        try:
            self.board = board
            self._pin = self.board.get_pin(config['map'])
            self.pid = pid
            self.config = config
            self.data = None
            self.is_out = self.config['type'] in ('do', 'ao')
            log.info(f"Configure pin {pid} with {config}")
        except:
            log.warning(f"Failed to configure pin {pid} with {config}")
            import traceback
            traceback.print_exc()

    def read(self):
        return self.data if self.data is not None else 0

    def _read_data(self):
        self.data = self._pin.read()

    def write(self, value):
        if self.is_out:
            self.value = value
            self._pin.write(value)
        else:
            log.warning(f'Trying to write to input pin {self.pid}')


class ArduinoBoard:
    model = 'Arduino'  # Arduino is default Arduino Uno in Firmata

    def __init__(self, config):
        self.config = config
        self.pins: Dict[str, Pin] = dict()
        self.pin_data: Dict[str, Union[int, float]] = dict()

        # Set up and connect device on configured comport
        _devstr = f'device {config["type"]}>>{config["model"]}'
        try:
            # Try lower board setup time
            # pyfirmata.pyfirmata.BOARD_SETUP_WAIT_TIME = .1
            self._board = getattr(pyfirmata, self.model)(config['port'])
            log.info(f'Using {_devstr}')
        except:
            log.warning(f'Failed to set up {_devstr}')
            import trace
            print(traceback.print_exc())

        # Create and start iterator thread for reads
        self.it = pyfirmata.util.Iterator(self._board)
        self.it.start()

    # def configure_pins(self, **pins):
    #     for pid, config in pins.items():
    #         self.pins[pid] = Pin(self._board, pid, config)

    def configure_pin(self, pin_id, pin_config):
        self.pins[pin_id] = Pin(self._board, pin_id, pin_config)

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

    def __init__(self, *args, **kwargs):
        super(ArduinoNanoBoard, self).__init__(*args, **kwargs)


class ArduinoDueBoard(ArduinoBoard):
    model = 'ArduinoDue'

    def __init__(self, *args, **kwargs):
        super(ArduinoDueBoard, self).__init__(*args, **kwargs)


class ArduinoMegaBoard(ArduinoBoard):
    model = 'ArduinoMega'

    def __init__(self, *args, **kwargs):
        super(ArduinoMegaBoard, self).__init__(*args, **kwargs)

