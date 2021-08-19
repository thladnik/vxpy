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

from mappapp import Config
from mappapp import Def
from mappapp.core import routine


class Frames(routine.CameraRoutine):

    def __init__(self, *args, **kwargs):
        routine.CameraRoutine.__init__(self, *args, **kwargs)

        self.device_list = list(zip(Config.Camera[Def.CameraCfg.device_id],
                                    Config.Camera[Def.CameraCfg.res_x],
                                    Config.Camera[Def.CameraCfg.res_y]))

        target_fps = Config.Camera[Def.CameraCfg.fps]

        # Set up buffer frame attribute for each camera device
        for device_id, res_x, res_y in self.device_list:
            # Set one array attribute per camera device
            array_attr = routine.ArrayAttribute((res_y, res_x), routine.ArrayDType.uint8, length=2*target_fps)
            attr_name = f'{device_id}_frame'
            setattr(self.buffer, attr_name, array_attr)
            # Add to be written to file
            self.file_attrs.append(attr_name)

    def execute(self, **frames):
        for device_id, frame in frames.items():

            if frame is None:
                continue

            # Update shared attributes
            if frame.ndim > 2:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :, 0])
            else:
                getattr(self.buffer, f'{device_id}_frame').write(frame[:, :])


