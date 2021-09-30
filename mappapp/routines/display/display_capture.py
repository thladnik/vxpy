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
from mappapp.api.attribute import ArrayAttribute, ArrayType, ObjectAttribute, write_to_file
from mappapp.api.routine import DisplayRoutine


class StaticParameters(DisplayRoutine):
    """This routine buffers the visual parameters,
    but doesn't register them to be written to file continuously"""

    def setup(self):

        # Set up shared variables
        self.parameters = ObjectAttribute('static_display_parameters')

    def main(self, visual):
        if visual is None:
            params = None
        else:
            params = visual.parameters

        self.parameters.write(params)


class DynamicParameters(DisplayRoutine):
    """This routine buffers the visual parameters
    and registers them to be written to file"""

    def setup(self):

        # Set up shared variables
        self.parameters = ObjectAttribute('dynamic_display_parameters')
        write_to_file(self, 'dynamic_display_parameters')

    def main(self, visual):
        if visual is None:
            params = None
        else:
            params = visual.parameters

        self.parameters.write(params)


class Frames(DisplayRoutine):

    def setup(self, *args, **kwargs):

        # Set up shared variables
        self.width = Config.Display[Def.DisplayCfg.window_width]
        self.height = Config.Display[Def.DisplayCfg.window_height]
        self.frame = ArrayAttribute('display_frame', (self.height, self.width, 3), ArrayType.uint8)
        write_to_file(self, 'display_frame')

    def main(self, visual):
        if visual is None:
            return

        frame = visual.frame.read('color', alpha=False)

        self.frame.write(frame)
