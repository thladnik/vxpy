"""
MappApp ./process/Io.py - General purpose digital/analog input/output process.
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
import Process
import Def
import IPC
import Logging

class Main(Process.AbstractProcess):
    name = Def.Process.Io

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        ################################
        ### Set up device
        self.device = None
        if Config.Io[Def.IoCfg.device_type] == 'Arduino':
            import devices.microcontrollers.Arduino
            self.device = devices.microcontrollers.Arduino.Device()

        run = False
        try:
            if self.device is None:
                raise Exception('No applicable device found.')
            else:
                run = self.device.connect() and self.device.setup()

        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'Could not connect to device. // Exception: {}'
                               .format(exc))
            self.setState(Def.State.STOPPED)

        ### Run event loop
        if run:
            self.run()

    def _prepareProtocol(self):
        print('Protocollin\' and rollin\'')
        self.protocol = 'something'

    def _preparePhase(self):
        print('phase lala')

    def _cleanupProtocol(self):
        print('Just cleanin\'')


    def main(self):

        # (optional) Sleep to reduce CPU usage
        dt = self.t + 1./Config.Io[Def.IoCfg.sample_rate] - time.perf_counter()
        if dt > IPC.Control.General[Def.GenCtrl.min_sleep_time]:
            time.sleep(3*dt/4)

        # Precise timing
        while time.perf_counter() < self.t + 1./Config.Io[Def.IoCfg.sample_rate]:
            pass

        # Update routines
        IPC.Routines.Io.update(self.device.readAll())
        self._runProtocol()

