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

from vxpy.core import visual
from vxpy.utils import plane


class Sinusoid2d(visual.PlanarVisual):

    u_sp_vertical = 'u_sp_vertical'
    u_sp_horizontal = 'u_sp_horizontal'
    u_checker_pattern = 'u_checker_pattern'

    interface = [
        (u_sp_vertical, 0.5, 1., 100., dict(step_size=1.)),
        (u_sp_horizontal, 0.5, 1., 100., dict(step_size=1.))
    ]

    def __init__(self, *args):
        visual.PlanarVisual.__init__(self, *args)

        self.plane = plane.XYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.program = gloo.Program(self.load_vertex_shader('./sinusoid_2d.vert'),
                                    self.load_shader('./sinusoid_2d.frag'))
        self.program['a_position'] = self.position_buffer

    def initialize(self, *args, **kwargs):
        self.program['u_checker_pattern'] = 0

    def render(self, frame_time):
        self.apply_transform(self.program)
        self.program.draw('triangles', self.index_buffer)


class Checkerboard(visual.PlanarVisual):

    u_sp_vertical = 'u_sp_vertical'
    u_sp_horizontal = 'u_sp_horizontal'
    u_checker_pattern = 'u_checker_pattern'

    interface = [
        (u_sp_vertical, 0.5, 1., 100., dict(step_size=1.)),
        (u_sp_horizontal, 0.5, 1., 100., dict(step_size=1.))
    ]

    def __init__(self, *args):
        visual.PlanarVisual.__init__(self, *args)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.program = gloo.Program(self.load_vertex_shader('./sinusoid_2d.vert'),
                                    self.load_shader('./sinusoid_2d.frag'))
        self.program['a_position'] = self.position_buffer

    def initialize(self, *args, **kwargs):
        self.program['u_checker_pattern'] = 1

    def render(self, frame_time):
        self.apply_transform(self.program)
        self.program.draw('triangles', self.index_buffer)
