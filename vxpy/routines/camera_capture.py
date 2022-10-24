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
from typing import List, Tuple

from vxpy import config
import vxpy.api.attribute as vxattribute
import vxpy.api.routine as vxroutine


class Frames(vxroutine.CameraRoutine):

    device_list: List[Tuple[str, int, int]] = []
    frame_postfix = '_frame'

    def __init__(self, *args, **kwargs):
        vxroutine.CameraRoutine.__init__(self, *args, **kwargs)

    @classmethod
    def require(cls):
        for device_id, device_config in config.CONF_CAMERA_DEVICES.items():
            cls.device_list.append((device_id, device_config['width'], device_config['height']))

        # Set one array attribute per camera device
        for device_id, res_x, res_y in cls.device_list:
            vxattribute.ArrayAttribute(f'{device_id}{cls.frame_postfix}', (res_x, res_y), vxattribute.ArrayType.uint8)

    def initialize(self):
        # Add all frame attributes to candidate list for save to disk
        for device_id, _, _ in self.device_list:
            vxattribute.get_attribute(f'{device_id}{self.frame_postfix}').add_to_file()

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
