"""
MappApp ./routines/DisplayRoutines.py - Custom processing routine implementations for the display process.
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

import Config
import Def
from Routine import AbstractRoutine, ArrayAttribute, ArrayDType, ObjectAttribute

class ParameterRoutine(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        # Set up shared variables
        self.buffer.parameters = ObjectAttribute()

    def _compute(self, data):
        # Here data == visual
        self.buffer.parameters.write(data.parameters)

    def _out(self):
        index, time, parameters = self.buffer.parameters.read(0)

        print(parameters)

        for key, value in parameters[0].items():
            yield key, time[0], value

class FrameRoutine(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        # Set up shared variables
        # TODO: is there a better way? This just assumes FB size = window size
        self.width = Config.Display[Def.DisplayCfg.window_width]
        self.height = Config.Display[Def.DisplayCfg.window_height]
        self.buffer.frame = ArrayAttribute((self.height, self.width, 3), ArrayDType.uint8)

    def _compute(self, data):
        # Here data == visual
        frame = data.frame.read('color', alpha=False)
        self.buffer.frame.write(frame)

    def _out(self):
        index, time, frame = self.buffer.frame.read(0)

        yield 'frame', time[0], frame[0]