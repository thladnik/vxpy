from typing import Iterator, Union

import pyfirmata
import pyfirmata.util

import vxpy.core.devices.serial as vxserial
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class ArduinoDAQPin(vxserial.SerialDevicePin):

    def write(self) -> bool:
        pass

    def read(self) -> Union[bool, int, float]:
        pass


class ArduinoDAQ(vxserial.SerialDevice):

    _iterator: pyfirmata.util.Iterator = None
    _board: pyfirmata.Board = None

    def _open(self) -> bool:

        # Set up and connect device on configured comport
        try:
            # Try lower board setup time
            # pyfirmata.pyfirmata.BOARD_SETUP_WAIT_TIME = .1
            self._board = getattr(pyfirmata, self.properties["model"])(self.properties['port'])
            log.info(f'Using {self}')

        except Exception as exc:
            log.error(f'Failed to get firmata device for model {self.properties["model"]} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        try:
            # Create and start iterator thread for reads
            self._iterator = pyfirmata.util.Iterator(self._board)

        except Exception as exc:
            log.error(f'Failed to create iterator for board {self._board} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        return True

    def get_pins(self) -> Iterator[str, vxserial.SerialDevicePin]:
        pass

    def _start(self) -> bool:
        try:
            self._iterator.start()

        except Exception as exc:
            log.error(f'Failed to start iterator for board {self._board} in {self}')
            import traceback
            print(traceback.print_exc())

            return False

        return True

    def _end(self) -> bool:
        self._iterator.join()

        return True

    def _close(self) -> bool:
        self._board.exit()

        return True
