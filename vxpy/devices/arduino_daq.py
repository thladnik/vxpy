from __future__ import annotations
from typing import Iterator, Union, Tuple

import pyfirmata
import pyfirmata.util

import vxpy.core.devices.serial as vxserial
import vxpy.core.logger as vxlogger
from vxpy.core.devices.serial import PINSIGTYPE, PINSIGDIR

log = vxlogger.getLogger(__name__)


class ArduinoDaq(vxserial.DaqDevice):

    _iterator: pyfirmata.util.Iterator = None
    board: pyfirmata.Board = None

    def get_pin_info(self) -> Iterator[Tuple[str, PINSIGTYPE, PINSIGDIR]]:
        pass

    def _open(self) -> bool:

        # Set up and connect device on configured comport
        try:
            # Try lower board setup time
            # pyfirmata.pyfirmata.BOARD_SETUP_WAIT_TIME = .1
            self.board = getattr(pyfirmata, self.properties["model"])(self.properties['port'])
            firmata_version_str = ".".join([str(i) for i in self.board.firmata_version])
            log.info(f'Using {self}')
            log.info(f'Board {self} running {self.board.firmware} v{firmata_version_str}')

        except Exception as exc:
            log.error(f'Failed to get Firmata device for model {self.properties["model"]} in {self}')
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

    def _setup_pins(self) -> None:

        for pin_id, pin_config in self.properties['pins'].items():
            # Create and set up pin
            pin = ArduinoDaqPin(pin_id, self, pin_config)

            # Save to device
            self._pins[pin_id] = pin

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


class ArduinoDaqPin(vxserial.DaqPin):

    _board: ArduinoDaq
    _pin: pyfirmata.Pin

    def __init__(self, *args, **kwargs):
        vxserial.DaqPin.__init__(self, *args, **kwargs)

        # Set signal type and direction based on map string
        sigtype, pin_num, sigdir = self.properties['map'].split(':')
        failed = None
        if sigtype == 'd':
            self.signal_type = vxserial.PINSIGTYPE.DIGITAL
        elif sigtype == 'a':
            self.signal_type = vxserial.PINSIGTYPE.ANALOG
        else:
            failed = f'Unknown signal type {sigtype}'

        if sigdir == 'i':
            self.signal_direction = vxserial.PINSIGDIR.IN
        elif sigdir == 'o':
            self.signal_direction = vxserial.PINSIGDIR.OUT
        else:
            failed = f'Unknown signal direction {sigdir}'

        if failed is not None:
            log.error(f'Failed to set up pin {self.properties["map"]} on device {self._board}. {failed}')
            return

    def initialize(self):
        # Use map property to get pin from board
        log.info(f'Initialize pin {self} on device {self._board}')
        self._pin = self._board.board.get_pin(self.properties['map'])

    def write(self, value) -> bool:
        self._pin.write(value)
        return True

    def read(self) -> Union[bool, int, float]:
        return self._pin.read()