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

import cv2
import logging
import numpy as np
from time import perf_counter, strftime, sleep

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


        ### Set avg. minimum sleep period
        times = list()
        for i in range(100):
            t = perf_counter()
            sleep(10**-10)
            times.append(perf_counter()-t)
        self.acqSleepThresh = np.quantile(times, 0.95)
        msg = 'Set acquisition threshold to {0:.6f}s'.format(self.acqSleepThresh)
        if self.acqSleepThresh > 1./Config.Camera[Def.CameraCfg.fps]:
            msg_type = logging.WARNING
            msg += '. Threshold is ABOVE average target frame time of 1/{}s.'\
                .format(Config.Camera[Def.CameraCfg.fps])
        else:
            msg_type = logging.INFO

        Logging.write(msg_type, msg)

        ### Run event loop
        self.run()

    def main(self):
        # Update camera settings
        # All camera settings with the "*_prop_*" substring
        # are considered properties which may be changed online
        for setting, value in Config.Camera.items():
            if setting.find('_prop_') >= 0:
                self.camera.updateProperty(setting, value)

        # Fetch current frame
        frame = self.camera.getImage()
        # Update routines
        IPC.Routines.Camera.update(frame)

        # Wait until next frame
        t = self.t + 1./Config.Camera[Def.CameraCfg.fps] - perf_counter()
        if t > self.acqSleepThresh:
            sleep(t)
