"""
MappApp ./process/DefaultCameraRoutines.py - Handles camera interaction and writes to the camera routines.
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

import Config
import Process
import Def
import devices.Camera
import IPC
import Logging

if Def.Env == Def.EnvTypes.Dev:
    from IPython import embed

class Camera(Process.AbstractProcess):
    name = Def.Process.Camera

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        self.cameras = dict()
        for device_id, manufacturer, model, format in zip(Config.Camera[Def.CameraCfg.device_id],
                                                          Config.Camera[Def.CameraCfg.manufacturer],
                                                          Config.Camera[Def.CameraCfg.model],
                                                          Config.Camera[Def.CameraCfg.format]):
            ### Get selected camera
            try:

                if manufacturer == 'TIS':
                    from devices.Camera import CAM_TIS
                    cam = CAM_TIS(model, format)
                elif manufacturer == 'virtual':
                    from devices.Camera import CAM_Virtual
                    cam = CAM_Virtual(model, format)

                self.cameras[device_id] = cam

                Logging.logger.log(Logging.INFO, 'Using camera {}>>{} ({}) as \"{}\"'
                               .format(manufacturer,
                                       model,
                                       format,
                                       device_id))
            except Exception as exc:
                Logging.logger.log(Logging.INFO, 'Unable to use camera {}>>{} ({}) // Exception: {}'
                                   .format(manufacturer,
                                           model,
                                           format,
                                           exc))


        target_fps = Config.Camera[Def.CameraCfg.fps]

        if IPC.Control.General[Def.GenCtrl.min_sleep_time] > 1./target_fps:
            Logging.write(Logging.WARNING, 'Mininum sleep period is ABOVE '
                                           'average target frametime of 1/{}s.'
                                            'This will cause increased CPU usage.'
                                            .format(target_fps))

        ### Run event loop
        self.run(interval=1/target_fps)

    def main(self):

        ### Snap image
        for device_id, cam in self.cameras.items():
            cam.snapImage()

        # Update routines
        IPC.Routines.Camera.update(**{device_id : cam.getImage() for device_id, cam in self.cameras.items()})
