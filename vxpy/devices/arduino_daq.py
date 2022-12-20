from __future__ import annotations
from typing import Iterator, Union, Tuple

import pyfirmata
import pyfirmata.util

import vxpy.core.devices.serial as vxserial
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class ArduinoDAQPin(vxserial.DaqPin):

    _board: ArduinoDaq
    _pin: pyfirmata.Pin

    def __init__(self, *args, **kwargs):
        vxserial.DaqPin.__init__(self, *args, **kwargs)

        sigtype, pin_num, sigdir = self.properties['map'].split(':')
        failed = None
        if sigtype == 'd':
            self.signal_type = vxserial.PINSIGNAL.DIGITAL
        elif sigtype == 'a':
            self.signal_type = vxserial.PINSIGNAL.ANALOG
        else:
            failed = f'Unknown signal type {sigtype}'

        if sigdir == 'i':
            self.signal_direction = vxserial.PINDIR.IN
        elif sigdir == 'o':
            self.signal_direction = vxserial.PINDIR.OUT
        else:
            failed = f'Unknown signal direction {sigdir}'

        if failed is not None:
            log.error(f'Failed to set up pin {self.properties["map"]} on device {self._board}. {failed}')
            return

        # Use map property to get pin from board
        self._pin = self._board.board.get_pin(self.properties['map'])
        log.info(f'Set up pin {self}')

    def write(self, value) -> bool:
        self._pin.write(value)
        return True

    def read(self) -> Union[bool, int, float]:
        return self._pin.read()


class ArduinoDaq(vxserial.DaqDevice):

    _iterator: pyfirmata.util.Iterator = None
    board: pyfirmata.Board = None

    def _open(self) -> bool:

        # Set up and connect device on configured comport
        try:
            # Try lower board setup time
            # pyfirmata.pyfirmata.BOARD_SETUP_WAIT_TIME = .1
            self.board = getattr(pyfirmata, self.properties["model"])(self.properties['port'])
            log.info(f'Using {self}')

        except Exception as exc:
            log.error(f'Failed to get firmata device for model {self.properties["model"]} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        try:
            # Create and start iterator thread for reads
            self._iterator = pyfirmata.util.Iterator(self.board)

        except Exception as exc:
            log.error(f'Failed to create iterator for board {self.board} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        return True

    def get_pins(self) -> Iterator[Tuple[str, vxserial.DaqPin]]:
        for pin_id, pin_config in self.properties['pins'].items():
            # Create and set up pin
            pin = ArduinoDAQPin(pin_id, self, pin_config)

            # Save to device
            self._pins[pin_id] = pin

            # Yield now
            yield pin_id, pin

    def _start(self) -> bool:
        try:
            self._iterator.start()

        except Exception as exc:
            log.error(f'Failed to start iterator for board {self.board} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        return True

    def _end(self) -> bool:
        self._iterator.join()

        return True

    def _close(self) -> bool:
        self.board.exit()

        return True
