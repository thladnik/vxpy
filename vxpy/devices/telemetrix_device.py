from telemetrix import telemetrix

from vxpy.core.devices import serial as vxserial


class Telemetrix(vxserial.SerialDevice):

    board: telemetrix.Telemetrix = None

    def _open(self) -> bool:

        _arduino_instance_id = self.properties.get('arduino_instance_id', 1)

        self.board = telemetrix.Telemetrix(arduino_instance_id=_arduino_instance_id)

    def _start(self) -> bool:
        self.board.start()

    def _end(self) -> bool:
        pass

    def _close(self) -> bool:
        self.board.shutdown()
        