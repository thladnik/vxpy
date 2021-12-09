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
from vxpy import config
from vxpy import Def
from vxpy.api.attribute import ArrayAttribute, ArrayType, ObjectAttribute, write_to_file
from vxpy.api.routine import DisplayRoutine
from vxpy.core.visual import AbstractVisual


class StaticParameters(DisplayRoutine):
    """This routine buffers the visual parameters,
    but doesn't register them to be written to file continuously"""

    def setup(self):

        # Set up shared variables
        self.parameters = ObjectAttribute('sdp')

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
        self.parameters = ObjectAttribute('ddp')

    def initialize(self):
        self.parameters.add_to_file()

    def main(self, visual: AbstractVisual):
        if visual is None:
            values = None
        else:
            # Use parameters dictionary
            values = visual.parameters.copy()

            # Add custom program uniforms
            new = dict()
            for program_name, program in visual.custom_programs.items():
                for var_qualifier, var_type, var_name in program.variables:
                    # Write any uniform variables that are not textures
                    # or part of the display calibration ("u_mapcalib_*")
                    if var_qualifier != 'uniform' \
                            or var_type not in ('int', 'float', 'vec2', 'vec3', 'mat2', 'mat3', 'mat4') \
                            or var_name.startswith('u_mapcalib_'):
                        continue
                    try:
                        new[f'{program_name}_{var_name}'] = program[var_name]
                        if var_name == 'u_time':
                            print(program[var_name][0], '(routine)')
                    except:
                        pass

            values.update(new)

        self.parameters.write(values)


class Frames(DisplayRoutine):

    def setup(self, *args, **kwargs):

        # Set up shared variables
        self.width = config.Display[Def.DisplayCfg.window_width]
        self.height = config.Display[Def.DisplayCfg.window_height]
        self.frame = ArrayAttribute('display_frame', (self.height, self.width, 3), ArrayType.uint8)

    def initialize(self):
        self.frame.add_to_file()

    def main(self, visual):
        if visual is None:
            return

        frame = visual.frame.read('color', alpha=False)

        self.frame.write(frame)
