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

import Controller
import Def
from devices import Arduino
import IPC
import Logging

class Main(Controller.BaseProcess):
    name = Def.Process.IO

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        try:
            Arduino.getSerialConnection()
        except:
            Logging.logger.log(logging.WARNING, 'No connected serial device found.')


        ### Run event loop
        self.run()


    def main(self):
        #print(self.getState())
        ########
        ### RUNNING
        if self.inState(self.State.RUNNING):

            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                Logging.write(logging.INFO, 'Phase {} ended.'.format(IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]))
                self.setState(self.State.PHASE_END)
                return

            #TODO: actually draw frame
            pass

        ########
        ### IDLE
        elif self.inState(self.State.IDLE):

            ## Ctrl PREPARE_PROTOCOL
            if self.inState(self.State.PREPARE_PROTOCOL, Def.Process.Controller):

                # TODO: actually set up protocol
                protocol = IPC.Control.Protocol[Def.ProtocolCtrl.name]

                # Set next state
                self.setState(self.State.WAIT_FOR_PHASE)
                return

            ### Fallback, timeout
            time.sleep(0.05)

        ########
        ### WAIT_FOR_PHASE
        elif self.inState(self.State.WAIT_FOR_PHASE):

            if not(self.inState(self.State.PREPARE_PHASE, Def.Process.Controller)):
                return

            # TODO: actually set up phase
            phase = IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]

            # Set next state
            self.setState(self.State.READY)

        ########
        ### READY
        elif self.inState(self.State.READY):
            if not(self.inState(self.State.RUNNING, Def.Process.Controller)):
                return

            ### Wait for go time
            while self.inState(self.State.RUNNING, Def.Process.Controller):
                if IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] <= time.time():
                    Logging.write(logging.INFO, 'Start at {}'.format(time.time()))
                    self.setState(self.State.RUNNING)
                    break

            return

        ########
        ### PHASE_END
        elif self.inState(self.State.PHASE_END):

            ####
            ## Ctrl in PREPARE_PHASE -> there's a next phase
            if self.inState(self.State.PREPARE_PHASE, Def.Process.Controller):
                self.setState(self.State.WAIT_FOR_PHASE)
                return

            elif self.inState(self.State.PROTOCOL_END, Def.Process.Controller):

                # TODO: clean up protocol

                self.setState(self.State.IDLE)
            else:
                pass

        ########
        ### Fallback: timeout
        else:
            time.sleep(0.05)
    def startProtocol(self):
        Logging.write(logging.INFO, 'Start new protocol ({})'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.name]))

        ### Set protocol
        self.protocol1 = 'blabla'

        ### Stand by for phase
        self.setState(self.State.standby)

    def stopProtocol(self):
        Logging.write(logging.INFO, 'Stop protocol ({})'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.name]))

        ### Cleanup
        self.protocol1 = None

        ### Turn to idle
        self.setState(self.State.IDLE)
