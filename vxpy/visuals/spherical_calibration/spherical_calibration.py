"""
vxpy ./visuals/spherica/calibration.py
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
from vxpy.utils import sphere


class BlackWhiteCheckerboard(vxvisual.SphericalVisual):

    u_elevation_sp = vxvisual.FloatParameter('u_elevation_sp', static=True, default=15., limits=(5, 180), step_size=5.)
    u_azimuth_sp = vxvisual.FloatParameter('u_azimuth_sp', static=True, default=22.5, limits=(5, 360), step_size=5.)

    def __init__(self, *args, **kwargs):
        """Black-and-white checkerboard for calibration."""

        vxvisual.SphericalVisual.__init__(self, *args, **kwargs)

        self.sphere = sphere.UVSphere(azim_lvls=100, elev_lvls=50, azimuth_range=2 * np.pi, upper_elev=np.pi / 2)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        self.checker = gloo.Program(self.load_vertex_shader('./static_checker.vert'),
                                    self.load_shader('./static_checker.frag'))
        self.checker['a_position'] = self.position_buffer
        self.checker['a_azimuth'] = self.azimuth_buffer
        self.checker['a_elevation'] = self.elevation_buffer

        self.u_elevation_sp.connect(self.checker)
        self.u_azimuth_sp.connect(self.checker)

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        self.checker.draw('triangles', self.index_buffer)


class RegularMesh(vxvisual.SphericalVisual):

    u_elevation_sp = vxvisual.FloatParameter('u_elevation_sp', static=True, default=15., limits=(5, 180), step_size=5.)
    u_azimuth_sp = vxvisual.FloatParameter('u_azimuth_sp', static=True, default=22.5, limits=(5, 360), step_size=5.)
    u_line_threshold = vxvisual.FloatParameter('u_line_threshold', static=True, default=0.995, limits=(0.001, 1.0), step_size=0.001)

    def __init__(self, *args, **kwargs):
        vxvisual.SphericalVisual.__init__(self, *args, **kwargs)

        self.sphere = sphere.UVSphere(azim_lvls=100, elev_lvls=50, azimuth_range=2 * np.pi, upper_elev=np.pi / 2)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        self.mesh = gloo.Program(self.load_vertex_shader('./static_mesh.vert'),
                                 self.load_shader('./static_mesh.frag'))
        self.mesh['a_position'] = self.position_buffer
        self.mesh['a_azimuth'] = self.azimuth_buffer
        self.mesh['a_elevation'] = self.elevation_buffer

        self.u_elevation_sp.connect(self.mesh)
        self.u_azimuth_sp.connect(self.mesh)
        self.u_line_threshold.connect(self.mesh)

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        self.mesh.draw('triangles', self.index_buffer)
