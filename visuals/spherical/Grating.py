"""
MappApp ./visuals/Grating.py - Grating visuals
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

from Shader import BasicFileShader
from Visuals import SphericalVisual
from models import BasicSphere


class BlackWhiteGrating(SphericalVisual):

    u_waveform = 'u_waveform'
    u_direction = 'u_direction'
    u_ang_velocity = 'u_ang_velocity'
    u_spat_period = 'u_spat_period'

    parameters = {u_waveform: None,
                  u_direction: None,
                  u_ang_velocity: None,
                  u_spat_period: None}

    def __init__(self, *args, **params):
        SphericalVisual.__init__(self, *args)

        # Set up sphere
        self.sphere = BasicSphere.UVSphere(azim_lvls=60, elev_lvls=30)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        # Set up program
        self.grating = gloo.Program(
            BasicFileShader().addShaderFile('spherical/grating.vert').read(),
            BasicFileShader().addShaderFile('spherical/grating.frag').read())
        self.grating['a_position'] = self.position_buffer
        self.grating['a_azimuth'] = self.azimuth_buffer
        self.grating['a_elevation'] = self.elevation_buffer

    def render(self, frame_time):
        self.grating['u_stime'] = frame_time

        self.apply_transform(self.grating)
        self.grating.draw('triangles', self.index_buffer)

    def parse_u_waveform(self, waveform):
        return 1 if waveform == 'rectangular' else 2  # 'sinusoidal'

    def parse_u_direction(self, direction):
        return 1 if direction == 'vertical' else 2  # 'horizontal'
