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


class BlackAndWhiteGrating(visual.PlanarVisual):
    description = 'Black und white contrast grating stimulus'

    def triggerme01(self):
        print('TRIGGERED')

    u_shape = 'u_shape'
    u_direction = 'u_direction'
    u_lin_velocity = 'u_lin_velocity'
    u_spat_period = 'u_spat_period'
    u_time = 'u_time'

    parameters = {
        u_shape: 'rectangular',
        u_direction: 'horizontal',
        u_lin_velocity: 5.,
        u_spat_period: 10.,
        u_time: 0.
    }

    interface = [
        (u_shape, 'rectangular', 'sinusoidal'),
        (u_direction, 'horizontal', 'vertical'),
        (u_lin_velocity, 5., 0., 100., dict(step_size=1.)),
        (u_spat_period, 10., 1.0, 200., dict(step_size=1.)),
        ('trigger_something', triggerme01)
    ]

    def __init__(self, *args, **kwargs):
        """

        :param args: positional arguments to parent class
        :param direction: movement direction of grating; either 'vertical' or 'horizontal'
        :param shape: shape of grating; either 'rectangular' or 'sinusoidal'; rectangular is a zero-rectified sinusoidal
        :param lin_velocity: <float> linear velocity of grating in [mm/s]
        :param spat_period: <float> spatial period of the grating in [mm]
        """
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(
            np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(
            np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.grating = gloo.Program(self.load_vertex_shader('planar/grating.vert'),
                                    self.load_shader('planar/grating.frag'))
        self.grating['a_position'] = self.position_buffer

        self.update(**kwargs)

    def reset(self):
        self.grating['u_time'] = 0.

    def render(self, dt):
        self.grating['u_time'] += dt  #time.time() - self.start_time

        self.apply_transform(self.grating)
        self.grating.draw('triangles', self.index_buffer)

    def parse_u_shape(self, shape):
        return 1 if shape == 'rectangular' else 2  # 'sinusoidal'

    def parse_u_direction(self, orientation):
        return 1 if orientation == 'vertical' else 2  # 'horizontal'
