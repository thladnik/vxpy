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
from vxpy import definitions
from vxpy.definitions import *
from vxpy.core import process, ipc, logger, camera_device

log = logger.getLogger(__name__)


class Camera(process.AbstractProcess):
    name = PROCESS_CAMERA
    _camera_threads: Dict[str, threading.Thread] = {}
    cameras: Dict[str, camera_device.AbstractCameraDevice] = {}
    _current_frame_index: Dict[str, Union[int, bool]] = {}
    _frames: Dict[str, List[Union[np.ndarray, None]]] = {}
    _next_snap: Dict[str, float] = {}

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        # Set up cameras
        for device_id, device_config in config.CONF_CAMERA_DEVICES.items():
            self._open_camera(device_id, device_config)

            # self._camera_threads[device_id] = threading.Thread(target=self._run_camera_thread,
            #                                                    args=(device_id, device_config))
            # self._camera_threads[device_id].start()

        target_interval = 1/200.

        if ipc.Control.General[definitions.GenCtrl.min_sleep_time] > target_interval:
            log.warning(f'Minimum sleep period ABOVE average target frame time of {target_interval:.5f}s.'
                        'This will cause increased CPU usage.')

        # Run event loop
        self.enable_idle_timeout = False
        self.run(interval=target_interval)

    def _open_camera(self, camera_id, device_config):
        device = camera_device.get_camera(device_config)

        if device.start_stream():
            log.info(f'Use {device} as \"{camera_id}\"')
            self.cameras[camera_id] = device
            self._next_snap[camera_id] = -np.inf
        else:
            # TODO: add more info for user
            log.error(f'Unable to use {device} as \"{camera_id}\"')
            return

    # def _run_camera_thread(self, device_id, device_config):
    #     camera_device = camera.open_device(device_id, device_config)
    #     if camera_device.open():
    #         log.info(f'Use {camera_device} as \"{device_id}\"')
    #     else:
    #         # TODO: add more info for user
    #         log.warning(f'Unable to use {camera_device} as \"{device_id}\"')
    #         return
    #
    #     # Save to dictionary and start
    #     camera_device.start_stream()
    #
    #     self._frames[device_id] = [None, None]
    #     self._current_frame_index[device_id] = 0
    #
    #     t = time.perf_counter()
    #     interval = 1 / device_config['fps']
    #     while True:
    #         time.sleep((t + interval) - time.perf_counter())
    #
    #         # NOTE: NEVER PUT A BUSY LOOP IN A THREAD
    #
    #         # print(f'{(time.perf_counter()-t):.3f} snap {device_id}')
    #         # Set new modules time for this iteration
    #         t = time.perf_counter()
    #
    #         # Snap image on camera
    #         camera_device.snap_image()
    #
    #         # Write frame to buffer
    #         self._current_frame_index[device_id] = not(self._current_frame_index[device_id])
    #         idx = self._current_frame_index[device_id]
    #         self._frames[device_id][idx] = camera_device.get_image()

    def start_protocol(self):
        pass

    def start_phase(self):
        pass

    def end_phase(self):
        pass

    def end_protocol(self):
        pass

    def _start_shutdown(self):
        for camera in self.cameras.values():
            camera.end_stream()
        process.AbstractProcess._start_shutdown(self)

    def main(self):

        for camera_id, camera in self.cameras.items():

            if self.global_t >= self._next_snap[camera_id]:

                # Snap image and update routine
                camera.snap_image()
                self.update_routines(**{camera_id: camera.get_image()})

                # Set next update time
                self._next_snap[camera_id] = self.global_t + 1. / camera.framerate

        # # Snap image
        # for device_id, cam in self.cameras.items():
        #     cam.snap_image()
        #
        # # Update routines
        # self.update_routines(**{device_id: cam.get_image() for device_id, cam in self.cameras.items()})

        # Update routines
        # current_frames = {}
        # for device_id in self._frames:
        #     idx = self._current_frame_index[device_id]
        #     frame = self._frames[device_id][idx]
        #     current_frames[device_id] = frame
        #
        #     if frame is not None:
        #         self._frames[device_id][idx] = None
        #
        # print(f'Update {len(current_frames)}')
        # self.update_routines(**current_frames)
