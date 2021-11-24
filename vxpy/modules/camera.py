"""
MappApp ./modules/camera_aio.py
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
from typing import Dict

from vxpy import Config
from vxpy import Def
from vxpy import Logging
from vxpy.core import process, ipc
from vxpy.core.camera import AbstractCameraDevice, open_device, _use_apis
from vxpy.devices.camera.virtual import virtual_camera


class Camera(process.AbstractProcess):
    name = Def.Process.Camera

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)
        global _use_apis
        _use_apis.append(virtual_camera)

        self.cameras: Dict[str, AbstractCameraDevice] = dict()

        # Set up cameras
        for config in Config.Camera[Def.CameraCfg.devices]:
            device_id = config['id']
            device = open_device(config)
            if device.open():
                Logging.write(Logging.INFO, f'Use {device} as \"{device_id}\"')
            else:
                # TODO: add more info for user
                Logging.write(Logging.WARNING, f'Unable to use {device} as \"{device_id}\"')
                continue

            # Save to dictionary and start
            self.cameras[device_id] = device
            self.cameras[device_id].start_stream()


        base_target_fps = 150.

        if ipc.Control.General[Def.GenCtrl.min_sleep_time] > 1./base_target_fps:
            Logging.write(Logging.WARNING,
                          'Mininum sleep period is ABOVE '
                          'average target frametime of 1/{}s.'
                          'This will cause increased CPU usage.'
                          .format(base_target_fps))

        # Run event loop
        self.enable_idle_timeout = False
        self.run(interval=1/base_target_fps)

    def start_protocol(self):
        pass

    def start_phase(self):
        pass

    def end_phase(self):
        pass

    def end_protocol(self):
        pass

    def main(self):

        # self._run_protocol()

        # Snap image
        for device_id, cam in self.cameras.items():
            cam.snap_image()

        # Update routines
        self.update_routines(**{device_id: cam.get_image() for device_id, cam in self.cameras.items()})
