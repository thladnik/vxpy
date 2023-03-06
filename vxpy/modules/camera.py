"""
vxPy ./modules/camera.py
Copyright (C) 2022 Tim Hladnik

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

from vxpy import config
from vxpy.definitions import *
import vxpy.core.process as vxprocess
import vxpy.core.logger as vxlogger
import vxpy.core.devices.camera as vxcamera

log = vxlogger.getLogger(__name__)


class Camera(vxprocess.AbstractProcess):
    name = PROCESS_CAMERA
    cameras: Dict[str, vxcamera.CameraDevice] = {}

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        # Set up cameras
        for device_id in config.CAMERA_DEVICES:
            self.cameras[device_id] = vxcamera.get_camera_by_id(device_id)
            self.cameras[device_id].open()
            self.cameras[device_id].start_stream()

        target_interval = 1/200.

        # Run event loop
        self.run(interval=target_interval)

    def prepare_static_protocol(self):
        pass

    def start_static_protocol_phase(self):
        pass

    def end_protocol_phase(self):
        pass

    def end_static_protocol(self):
        pass

    def _recording_attributes(self):
        metadata = {'__camera_device_list': list(config.CAMERA_DEVICES.keys())}

        for device_id, cam_props in config.CAMERA_DEVICES.items():
            for key, val in cam_props.items():
                metadata[f'__{device_id}_{key}'] = val

            for key, val in self.cameras[device_id].get_metadata().items():
                metadata[f'__{device_id}_meta_{key}'] = val

            for key, val in self.cameras[device_id].get_settings().items():
                metadata[f'__{device_id}_settings_{key}'] = val

        return metadata

    def main(self):

        for camera_id, camera in self.cameras.items():

            if camera.next_snap():
                camera.snap_image()

            # Update routine with new image if available
            if camera.next_image():
                self.update_routines(**{camera_id: camera.get_image()})

    def _start_shutdown(self):

        # Make sure camera streams are terminated before shutting down process
        for camera in self.cameras.values():
            camera.end_stream()
            camera.close()

        vxprocess.AbstractProcess._start_shutdown(self)
