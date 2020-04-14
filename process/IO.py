"""
MappApp ./process/IO.py - General purpose digital/analog input/output process.
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

import logging
import time

import Config
import Controller
import Def
import IPC
import Logging

class Main(Controller.AbstractProcess):
    name = Def.Process.IO

    def __init__(self, **kwargs):
        Controller.AbstractProcess.__init__(self, **kwargs)

        self.device = None
        if Config.IO[Def.IoCfg.device_type] == 'Arduino':
            import devices.microcontrollers.Arduino
            self.device = devices.microcontrollers.Arduino.Device()

        try:
            if self.device is None:
                raise Exception('No applicable device found.')
            else:
                if self.device.connect():
                    if self.device.setup():
                        ### Run event loop
                        self.run()
        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'Could not connect to device. // Exception: {}'
                               .format(exc))
            self.setState(Def.State.STOPPED)



    def _prepareProtocol(self):
        print('Protocollin\' and rollin\'')
        self.protocol = 'something'

    def _preparePhase(self):
        print('phase lala')

    def _cleanupProtocol(self):
        print('Just cleanin\'')


    def main(self):

        if self._runProtocol():
            self.device._digital['test01_pwmout'].write(1)
            time.sleep(0.5)
            self.device._digital['test01_pwmout'].write(0)
            time.sleep(0.5)
            pass
