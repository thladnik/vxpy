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

from core.visual import PlanarVisual
from utils import plane


class Checkerboard(PlanarVisual):

    u_rows = 'u_rows'
    u_cols = 'u_cols'

    parameters = {u_rows: None,
                  u_cols: None}

    def __init__(self, *args, **params):
        PlanarVisual.__init__(self, *args)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(
            np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(
            np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.checker = gloo.Program(self.load_vertex_shader('planar/checker.vert'),
                                    self.load_shader('planar/checker.frag'))
        self.checker['a_position'] = self.position_buffer

        self.update(**params)

    def render(self, frame_time):
        self.apply_transform(self.checker)
        self.checker.draw('triangles', self.index_buffer)
