"""
MappApp ./routines/display/__init__.py
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
from mappapp import Config
from mappapp import Def
from mappapp.core.routine import ArrayAttribute, ArrayDType, DisplayRoutine, ObjectAttribute


class StaticParameters(DisplayRoutine):
    """This routine buffers the visual parameters,
    but only doesn't register them to be written to file"""

    def __init__(self, *args, **kwargs):
        DisplayRoutine.__init__(self, *args, **kwargs)

        # Set up shared variables
        self.buffer.param = ObjectAttribute()

    def execute(self, visual):
        if visual is None:
            params = None
        else:
            params = visual.parameters

        self.buffer.param.write(params)


class DynamicParameters(DisplayRoutine):
    """This routine buffers the visual parameters
    and registers them to be written to file"""

    def __init__(self, *args, **kwargs):
        DisplayRoutine.__init__(self, *args, **kwargs)

        # Set up shared variables
        self.buffer.param = ObjectAttribute()
        self.file_attrs.append('param')

    def execute(self, visual):
        if visual is None:
            params = None
        else:
            params = visual.parameters

        self.buffer.param.write(params)


class Frames(DisplayRoutine):

    def __init__(self, *args, **kwargs):
        DisplayRoutine.__init__(self, *args, **kwargs)

        # Set up shared variables
        self.width = Config.Display[Def.DisplayCfg.window_width]
        self.height = Config.Display[Def.DisplayCfg.window_height]
        self.buffer.frame = ArrayAttribute((self.height, self.width, 3), ArrayDType.uint8)
        self.add_to_file('frame')

    def execute(self, visual):
        if visual is None:
            return

        frame = visual.frame.read('color', alpha=False)

        self.buffer.frame.write(frame)
