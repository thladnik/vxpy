"""
MappApp ./visuals/planar/grating.py
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

from mappapp.core import visual
from mappapp.utils import plane


class SingleMovingDot(visual.PlanarVisual):
    description = ''

    u_dot_lateral_offset = 'u_dot_lateral_offset'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg
    u_time = 'u_time'  # s
    u_vertical_offset = 'u_vertical_offset'
    # u_start_delay = 'u_start_delay'

    parameters = {
        u_dot_lateral_offset: 10.0,
        u_dot_ang_dia: 20.,
        u_dot_ang_velocity: 80.,
        u_time: 0.,
        u_vertical_offset: 20.
    }

    interface = [
    ]

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.program = gloo.Program(self.load_vertex_shader('planar/single_moving_dot.vert'),
                                    self.load_shader('planar/single_moving_dot.frag'))
        self.program['a_position'] = self.position_buffer

        self.update(**kwargs)

    def reset(self):
        self.program['u_time'] = 0.

    def render(self, dt):
        self.program['u_time'] += dt

        self.apply_transform(self.program)
        self.program.draw('triangles', self.index_buffer)
