"""
MappApp ./routines/camera/__init__.py
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

from vxpy import Config
from vxpy import Def
from vxpy.api.routine import CameraRoutine
from vxpy.api.attribute import ArrayAttribute, ArrayType
from vxpy.core.camera import Format


class Frames(CameraRoutine):

    def __init__(self, *args, **kwargs):
        CameraRoutine.__init__(self, *args, **kwargs)

    def setup(self):
        self.device_list: List[Tuple[str, int, int]] = []
        for dev in Config.Camera[Def.CameraCfg.devices]:
            fmt = Format.from_str(dev['format'])
            self.device_list.append((dev['id'], fmt.width, fmt.height))

        # Set up buffer frame attribute for each camera device
        self.frames = {}
        for device_id, res_x, res_y in self.device_list:
            # Set one array attribute per camera device
            attr_name = f'{device_id}_frame'
            self.frames[attr_name] = ArrayAttribute(attr_name, (res_y, res_x), ArrayType.uint8)

    def initialize(self):
        for attr in self.frames.values():
            attr.add_to_file()

    def main(self, **frames):
        for device_id, frame in frames.items():

            if frame is None:
                continue

            attr_name = f'{device_id}_frame'

            # Update shared attributes
            if frame.ndim > 2:
                # getattr(self.buffer, f'{device_id}_frame').write(frame[:, :, 0])
                self.frames[attr_name].write(frame[:, :, 0])
            else:
                self.frames[attr_name].write(frame[:, :])
                # getattr(self.buffer, f'{device_id}_frame').write(frame[:, :])


