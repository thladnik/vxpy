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
import IPC
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class Main(Controller.BaseProcess):
    name = Definition.Process.Camera

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        ### Set camera buffer object
        IPC.CameraBufferObject.constructBuffers()

        ### Set recording parameters
        self.frameDims = (int(Config.Camera[Definition.Camera.res_y]),
                          int(Config.Camera[Definition.Camera.res_x]))
        self.fps = Config.Camera[Definition.Camera.fps]

        ### Set up camera
        ## The Imaging Source cameras
        if Config.Camera[Definition.Camera.manufacturer] == 'TIS':
            import devices.cameras.tisgrabber as IC
            self.camera = IC.TIS_CAM()
            self.camera.open(Config.Camera[Definition.Camera.model])
            self.camera.SetVideoFormat(Config.Camera[Definition.Camera.format])
            self.camera.SetPropertySwitch("Framerate","Auto",0)
            self.camera.SetPropertySwitch("Exposure","Auto",0)
            self.camera.SetPropertyAbsoluteValue("Exposure", "Value", 1./1000)
            self.camera.SetFrameRate(self.fps)
            self.camera.SetContinuousMode(0)
            self.camera.StartLive(0)

        ## Virtual camera
        elif Config.Camera[Definition.Camera.manufacturer] == 'virtual':
            import devices.cameras.virtual as VC
            self.camera = VC.VirtualCamera()
            self.camera.setVideoFormat(Config.Camera[Definition.Camera.format],
                                       Config.Camera[Definition.Camera.res_y],
                                       Config.Camera[Definition.Camera.res_x])

        Logging.logger.log(logging.DEBUG, 'Using camera {}>>{}'
                           .format(Config.Camera[Definition.Camera.manufacturer],
                                   Config.Camera[Definition.Camera.model]))

        ### Run event loop
        self.run()

    def main(self):
        # Fetch current frame
        frame = self.camera.GetImage()
        # Update buffers
        IPC.CameraBufferObject.update(frame)

        # Wait until next frame
        t = self.t + 1./self.fps - perf_counter()
        if t > 0.:
            sleep(t)
