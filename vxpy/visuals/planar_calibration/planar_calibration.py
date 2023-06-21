"""
vxpy ./visuals/planar/calibration.py
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

import vxpy.core.visual as vxvisual
from vxpy.utils import plane


class Sinusoid2d(vxvisual.PlanarVisual):

    u_sp_vertical = vxvisual.FloatParameter('u_sp_vertical', static=True, default=15., limits=(5, 180), step_size=5.)
    u_sp_horizontal = vxvisual.FloatParameter('u_sp_horizontal', static=True, default=22.5, limits=(5, 360), step_size=5.)
    u_checker_pattern = vxvisual.FloatParameter('u_checker_pattern', static=True, value_map={'Checker': 1, 'Sinusoid': 0})

    def __init__(self, *args, **kwargs):
        vxvisual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.XYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.sinusoid = gloo.Program(self.load_vertex_shader('./sinusoid_2d.vert'),
                                     self.load_shader('./sinusoid_2d.frag'))
        self.sinusoid['a_position'] = self.position_buffer

        self.u_sp_horizontal.connect(self.sinusoid)
        self.u_sp_vertical.connect(self.sinusoid)
        self.u_checker_pattern.connect(self.sinusoid)

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        self.apply_transform(self.sinusoid)
        self.sinusoid.draw('triangles', self.index_buffer)
