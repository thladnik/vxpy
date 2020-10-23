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
from dataclasses import dataclass, make_dataclass

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

        self.update(**params)

    def render(self, frame_time):
        self.grating['u_stime'] = frame_time

        self.apply_transform(self.grating)
        self.grating.draw('triangles', self.index_buffer)

    def update(self, **params):

        if params.get(self.u_waveform) is not None:
            params[self.u_waveform] = self.parse_shape(params.get(self.u_waveform))

        if params.get(self.u_direction) is not None:
            params[self.u_direction] = self.parse_direction(params.get(self.u_direction))

        self.parameters.update({k : p for k, p in params.items() if not(p is None)})
        for k, p in self.parameters.items():
            self.grating[k] = p

    def parse_shape(self, shape):
        return 1 if shape == 'rectangular' else 2  # 'sinusoidal'

    def parse_direction(self, orientation):
        return 1 if orientation == 'vertical' else 2  # 'horizontal'
