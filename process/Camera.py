"""
MappApp ./process/Camera.py - Handles camera interaction and writes to the camera buffers.
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
import Controller
import Definition
import devices.Camera
import IPC
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class Main(Controller.BaseProcess):
    name = Definition.Process.Camera

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        ### Set recording parameters
        self.frameDims = (int(Config.Camera[Definition.Camera.res_y]),
                          int(Config.Camera[Definition.Camera.res_x]))
        self.fps = Config.Camera[Definition.Camera.fps]

        ### Get selected camera
        self.camera = devices.Camera.GetCamera(1)

        Logging.logger.log(logging.INFO, 'Using camera {}>>{}'
                           .format(Config.Camera[Definition.Camera.manufacturer],
                                   Config.Camera[Definition.Camera.model]))

        ### Set avg. minimum sleep period
        sleep(2)  # Wait to determine sleep period (on initial startup heavy CPU load skews the results)
        times = list()
        for i in range(100):
            t = perf_counter()
            sleep(10**-10)
            times.append(perf_counter()-t)
        self.acqSleepThresh = np.quantile(times, 0.95)
        Logging.write(logging.INFO, 'Set acquisition threshold to {0:.4f}s'.format(self.acqSleepThresh))

        ### Run event loop
        self.run()

    def main(self):
        # Update camera settings
        # All camera settings with the "*_prop_*" substring are considered properties which may be changed online
        for setting, value in Config.Camera.items():
            if setting.find('_prop_') >= 0:
                self.camera.updateProperty(setting, value)

        # Fetch current frame
        frame = self.camera.getImage()
        # Update buffers
        IPC.CameraBufferObject.update(frame)

        # Wait until next frame
        t = self.t + 1./self.fps - perf_counter()
        if t > self.acqSleepThresh:
            sleep(t)
