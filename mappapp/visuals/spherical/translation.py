"""
MappApp ./visuals/spherical/translation.py
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
import numpy as np
from vispy import gloo, util

from mappapp.core import visual
from mappapp.utils import sphere


class TunnelTranslation(visual.SphericalVisual):

    @staticmethod
    def parse_u_waveform(waveform):
        return 1 if waveform == 'rectangular' else 2  # 'sinusoidal'

    @staticmethod
    def parse_u_direction(direction):
        return 1 if direction == 'vertical' else 2  # 'horizontal'

    u_waveform = 'u_waveform'
    u_lin_velocity = 'u_lin_velocity'
    u_spat_period = 'u_spat_period'
    p_fish_direction = 'p_fish_direction'
    p_fish_position = 'p_fish_position'
    p_fish_velocity = 'p_fish_velocity'

    default_front_dir = np.array([1., 0., 0.])
    default_fish_pos = np.array([0., 0.])
    default_fish_dir = np.array([1., 0., 0.])

    parameters = {u_waveform: 'rectangular',
                  u_lin_velocity: 0.1,
                  u_spat_period: 0.05,
                  p_fish_direction: default_fish_dir/np.linalg.norm(default_fish_dir),
                  p_fish_position: default_fish_pos/np.linalg.norm(default_fish_pos)}

    def __init__(self, *args, **kwargs):
        visual.SphericalVisual.__init__(self, *args, **kwargs)

        # Set up sphere
        self.sphere = sphere.UVSphere(azim_lvls=60,elev_lvls=30)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)

        # Set up program
        vert = self.load_vertex_shader('spherical/tunnel_translation.vert')
        frag = self.load_shader('spherical/tunnel_translation.frag')
        self.program = gloo.Program(vert, frag)
        self.program['a_position'] = self.position_buffer

        self.front_direction = self.default_front_dir / np.linalg.norm(self.default_front_dir)

    def render(self, frame_time):
        fish_direction = self.parameters.get(self.p_fish_direction)

        # For tasting of dynamic fish direction
        # fish_direction = np.array([np.sin(frame_time/2), np.cos(frame_time/2), (np.cos(frame_time/4) + 1.0)/4.0])
        # fish_direction /= np.linalg.norm(fish_direction)

        # Standard rotation for physical setup (TODO: make configurable?)
        rotate = util.transforms.rotate(45., [0., 0., 1.])

        # Calculate rotation axis and angle
        W = np.cross(self.front_direction, fish_direction)
        angle = np.arccos(np.dot(self.front_direction, fish_direction))

        # Apply rotation
        if not(np.isclose(angle, 0.0, atol=1.e-4)):
            rotate = np.dot(rotate, util.transforms.rotate(angle / np.pi * 180.0, W))

        self.program['u_rotate'] = rotate

        self.program['u_time'] = frame_time

        self.apply_transform(self.program)
        self.program.draw('triangles', self.index_buffer)

