"""
vxPy ./routines/display/display_capture.py
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
import numpy as np

from vxpy import calib
import vxpy.api.attribute as vxattribute
import vxpy.api.routine as vxroutine
import vxpy.core.visual as vxvisual


class Frames(vxroutine.DisplayRoutine):

    def require(self, *args, **kwargs):

        # Set up shared variables
        self.width = calib.CALIB_DISP_WIN_SIZE_WIDTH
        self.height = calib.CALIB_DISP_WIN_SIZE_HEIGHT
        self.frame = vxattribute.ArrayAttribute('display_frame',
                                                (self.width, self.height, 3),
                                                vxattribute.ArrayType.uint8)

    def initialize(self):
        self.frame.add_to_file()

    def main(self, visual: vxvisual.AbstractVisual):
        if visual is None:
            return

        frame = np.swapaxes(visual.transform.frame.read('color', alpha=False), 0, 1)

        self.frame.write(frame)
