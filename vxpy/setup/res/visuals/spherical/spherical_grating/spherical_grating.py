"""
vxpy ./visuals/spherical/grating.py
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

from vxpy.api.visual import SphericalVisual
from vxpy.utils import sphere


class BlackWhiteGrating(SphericalVisual):
    # (optional) Add a short description
    description = 'Spherical black und white contrast grating stimulus'

    # (optional) Define names for used variables
    p_shape = 'p_shape'
    p_type = 'p_type'
    u_ang_velocity = 'u_ang_velocity'
    u_spat_period = 'u_spat_period'

    # (optional) Define parameters of an interface
    interface = [
        # Name, 'value1', 'value2', 'value3'
        (p_shape, 'rectangular', 'sinusoidal'),
        (p_type, 'rotation', 'translation'),
        # Name, default, min, max, additional info
        (u_ang_velocity, 5., 0., 100., {'step_size': 1.}),
        (u_spat_period, 40., 2., 360., {'step_size': 1.})]

    def __init__(self, *args):
        """Black und white contrast grating stimulus on a sphere

        :param p_shape: <string> shape of grating; either 'rectangular' or 'sinusoidal'; rectangular is a zero-rectified sinusoidal
        :param p_type: <string> motion type of grating; either 'rotation' or 'translation'
        :param u_lin_velocity: <float> linear velocity of grating in [mm/s]
        :param u_spat_period: <float> spatial period of the grating in [mm]
        :param u_time: <float> time elapsed since start of visual [s]
        """
        SphericalVisual.__init__(self, *args)

        # Set up 3d model of sphere
        self.sphere = sphere.UVSphere(azim_lvls=60, elev_lvls=30)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        # Set up program
        vert = self.load_vertex_shader('./spherical_grating.vert')
        frag = self.load_shader('./spherical_grating.frag')
        self.grating = gloo.Program(vert, frag)

    def initialize(self, **params):
        # Reset u_time to 0 on each visual initialization
        self.grating['u_time'] = 0.0

        # Set positions with buffers
        self.grating['a_position'] = self.position_buffer
        self.grating['a_azimuth'] = self.azimuth_buffer
        self.grating['a_elevation'] = self.elevation_buffer

    def render(self, dt):
        # Add elapsed time to u_time
        self.grating['u_time'] += dt

        # Apply default transforms to the program for mapping according to hardware calibration
        self.apply_transform(self.grating)

        # Draw the actual visual stimulus using the indices of the  triangular faces
        self.grating.draw('triangles', self.index_buffer)

    @staticmethod
    def parse_p_shape(waveform):
        return 1 if waveform == 'rectangular' else 2  # 'sinusoidal'

    @staticmethod
    def parse_p_type(direction):
        return 1 if direction == 'translation' else 2  # 'horizontal'
