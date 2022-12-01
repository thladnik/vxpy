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
import threading
from typing import Tuple, Union, List
import numpy as np

from vxpy import config
from vxpy.definitions import *
import vxpy.core.process as vxprocess
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.devices.camera as vxcamera

log = vxlogger.getLogger(__name__)


class Camera(vxprocess.AbstractProcess):
    name = PROCESS_CAMERA
    # _camera_threads: Dict[str, threading.Thread] = {}
    cameras: Dict[str, vxcamera.CameraDevice] = {}
    # _current_frame_index: Dict[str, Union[int, bool]] = {}
    # _frames: Dict[str, List[Union[np.ndarray, None]]] = {}
    # _next_snap: Dict[str, float] = {}

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        # Set up cameras
        for device_id in config.CONF_CAMERA_DEVICES:
            self.cameras[device_id] = vxcamera.get_camera_by_id(device_id)
            self.cameras[device_id].open()
            self.cameras[device_id].start_stream()

        target_interval = 1/200.

        if vxipc.Control.General[GenCtrl.min_sleep_time] > target_interval:
            log.warning(f'Minimum sleep period ABOVE average target frame time of {target_interval:.5f}s.'
                        'This will cause increased CPU usage.')

        # Run event loop
        self.enable_idle_timeout = False
        self.run(interval=target_interval)

    def prepare_static_protocol(self):
        pass

    def start_static_protocol_phase(self):
        pass

    def end_protocol_phase(self):
        pass

    def end_static_protocol(self):
        pass

    def _start_shutdown(self):

        # Make sure camera streams are terminated before shutting down process
        for camera in self.cameras.values():
            camera.end_stream()
            camera.close()

        vxprocess.AbstractProcess._start_shutdown(self)

    def main(self):

        for camera_id, camera in self.cameras.items():
            camera.snap_image()

            self.update_routines(**{camera_id: camera.get_image()})

            # if vxipc.get_time() >= self._next_snap[camera_id]:
            #
            #     # Snap image and update routine
            #     camera.snap_image()
            #
            #     # Set next update time
            #     self._next_snap[camera_id] = vxipc.get_time() + 1. / camera.framerate
