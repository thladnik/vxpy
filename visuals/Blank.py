"""
MappApp ./visuals/Spherical_Calibration.py - Checkerboard visuals
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

from vispy import gloo
import numpy as np

from visuals.__init__ import PlanarVisual
from models import BasicPlane


class Blank(PlanarVisual):

    p_color = 'p_color'

    parameters = {p_color: None}

    def __init__(self, *args, **params):
        PlanarVisual.__init__(self, *args)

        self.plane = BasicPlane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(
            np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(
            np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.update(**params)

    def render(self, frame_time):
        gloo.clear(self.parameters[self.p_color])
