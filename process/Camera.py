"""
MappApp ./process/Camera.py - Handles camera interaction and writes to the camera routines.
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
import devices.Camera
import IPC
import Logging

if Def.Env == Def.EnvTypes.Dev:
    from IPython import embed

class Main(Process.AbstractProcess):
    name = Def.Process.Camera

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        ### Set recording parameters
        self.frameDims = (int(Config.Camera[Def.CameraCfg.res_y]),
                          int(Config.Camera[Def.CameraCfg.res_x]))

        ### Get selected camera
        try:
            self.camera = devices.Camera.GetCamera(1)

            Logging.logger.log(logging.INFO, 'Using camera {}>>{}'
                           .format(Config.Camera[Def.CameraCfg.manufacturer],
                                   Config.Camera[Def.CameraCfg.model]))
        except Exception as exc:
            Logging.logger.log(logging.INFO, 'Unable to use camera {}>>{} // Exception: {}'
                               .format(Config.Camera[Def.CameraCfg.manufacturer],
                                       Config.Camera[Def.CameraCfg.model],
                                       exc))


        if IPC.Control.General[Def.GenCtrl.min_sleep_time] > 1./Config.Camera[Def.CameraCfg.fps]:
            Logging.write(logging.WARNING, 'Mininum sleep period is ABOVE '
                                           'average target frametime of 1/{}s.'
                                            'This will cause increased CPU usage.'
                                            .format(Config.Camera[Def.CameraCfg.fps]))

        ### Run event loop
        self.run()

    def main(self):
        # Update camera settings
        # All camera settings with the "*_prop_*" substring
        # are considered properties which may be changed online
        # (Please don't touch the rest)
        for setting, value in Config.Camera.items():
            if setting.find('_prop_') >= 0:
                self.camera.updateProperty(setting, value)

        # (optional) Sleep to reduce CPU usage
        #dt = self.t + 1./Config.Camera[Def.CameraCfg.fps] - time.perf_counter()
        #if dt > IPC.Control.General[Def.GenCtrl.min_sleep_time]:
        #    time.sleep(3*dt/4)

        # Precise timing
        #while time.perf_counter() < self.t + 1./Config.Camera[Def.CameraCfg.fps]:
        #    pass

        # Update routines
        IPC.Routines.Camera.update(self.camera.getImage())
