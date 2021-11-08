"""
vxpy ./visuals/planar/grating.py
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

from vxpy.api.visual import PlanarVisual
from vxpy.utils import plane


class BlackAndWhiteGrating(PlanarVisual):
    # (optional) Add a short description
    description = 'Black und white contrast grating stimulus'

    # (optional) Define names for used variables
    p_shape = 'p_shape'
    p_direction = 'p_direction'
    u_lin_velocity = 'u_lin_velocity'
    u_spat_period = 'u_spat_period'
    u_time = 'u_time'

    # (optional) Define parameters of an interface
    interface = [
        # Name, 'value1', 'value2', 'value3'
        (p_shape, 'rectangular', 'sinusoidal'),
        (p_direction, 'horizontal', 'vertical'),
        # Name, default, min, max, additional info
        (u_lin_velocity, 5., 0., 100., dict(step_size=1.)),
        (u_spat_period, 10., 1.0, 200., dict(step_size=1.))
    ]

    def __init__(self, *args):
        """Black und white contrast grating stimulus

        :param p_shape: <string> shape of grating; either 'rectangular' or 'sinusoidal'; rectangular is a zero-rectified sinusoidal
        :param p_direction: <string> movement direction of grating; either 'vertical' or 'horizontal'
        :param u_lin_velocity: <float> linear velocity of grating in [mm/s]
        :param u_spat_period: <float> spatial period of the grating in [mm]
        :param u_time: <float> time elapsed since start of visual [s]
        """
        PlanarVisual.__init__(self, *args)

        # Set up model of a 2d plane
        self.plane_2d = plane.XYPlane()

        # Get vertex positions and corresponding face indices
        faces = self.plane_2d.indices
        vertices = self.plane_2d.a_position

        # Create vertex and index buffers
        self.index_buffer = gloo.IndexBuffer(faces)
        self.position_buffer = gloo.VertexBuffer(vertices)

        # Create a shader program
        vert = self.load_vertex_shader('./planar_grating.vert')
        frag = self.load_shader('./planar_grating.frag')
        self.grating = gloo.Program(vert, frag)

    def initialize(self, *args, **kwargs):
        # Reset u_time to 0 on each visual initialization
        self.grating['u_time'] = 0.

        # Set positions with vertex buffer
        self.grating['a_position'] = self.position_buffer

    def render(self, dt):
        # Add elapsed time to u_time
        self.grating['u_time'] += dt

        # Apply default transforms to the program for mapping according to hardware calibration
        self.apply_transform(self.grating)

        # Draw the actual visual stimulus using the indices of the  triangular faces
        self.grating.draw('triangles', self.index_buffer)

    # Parse function for waveform shape
    @staticmethod
    def parse_p_shape(shape: str) -> int:
        return 1 if shape == 'rectangular' else 2  # 'sinusoidal'

    # Parse function for motion direction
    @staticmethod
    def parse_p_direction(orientation: str) -> int:
        return 1 if orientation == 'vertical' else 2  # 'horizontal'
