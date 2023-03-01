"""
MappApp ./routines/camera/display_calibration.py
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
from __future__ import annotations
from typing import List

from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.devices.camera as vxcamera
import vxpy.core.routine as vxroutine


class Frames(vxroutine.CameraRoutine):
    device_list: List[vxcamera.CameraDevice] = []
    frame_postfix = '_frame'

    def __init__(self, *args, **kwargs):
        vxroutine.CameraRoutine.__init__(self, *args, **kwargs)

    def require(self):
        # Fetch all cameras by device_id and append to list
        for device_id in config.CAMERA_DEVICES:
            self.device_list.append(vxcamera.get_camera_by_id(device_id))

        # Set one array attribute per camera device
        for device in self.device_list:
            vxattribute.ArrayAttribute(f'{device.device_id}{self.frame_postfix}',
                                       (device.width, device.height), vxattribute.ArrayType.uint8)

    def initialize(self):
        # Add all frame attributes to candidate list for save to disk
        for device in self.device_list:
            vxattribute.get_attribute(f'{device.device_id}{self.frame_postfix}').add_to_file()

    def main(self, **frames):

        for device_id, frame_data in frames.items():

            if frame_data is None:
                continue

            # Fetch attribute object
            frame_attr = vxattribute.get_attribute(f'{device_id}{self.frame_postfix}')

            # Update shared attributes
            if frame_data.ndim > 2:
                frame_attr.write(frame_data[:, :, 0].T)
            else:
                frame_attr.write(frame_data[:, :].T)
