"""
MappApp ./visuals/Spherical_Calibration.py - Checkerboard visuals
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

from mappapp.core.visual import SphericalVisual
from mappapp.utils import sphere


class BlackWhiteCheckerboard(SphericalVisual):

    u_elevation_sf = 'u_elevation_sf'
    u_azimuth_sf = 'u_azimuth_sf'

    parameters = {u_elevation_sf: None,
                  u_azimuth_sf: None}

    def __init__(self, *args, **params):
        """Black-and-white checkerboard for calibration.

        :param protocol: protocol of which stimulus is currently part of
        :param rows: number of rows on checkerboard
        :param cols: number of columns on checkerboard
        """
        SphericalVisual.__init__(self, *args)

        self.sphere = sphere.UVSphere(azim_lvls=100,elev_lvls=50,azimuth_range=2 * np.pi,upper_elev=np.pi / 2)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        self.checker = gloo.Program(self.load_vertex_shader('spherical/checkerboard.vert'),
                                    self.load_shader('spherical/checkerboard.frag'))
        self.checker['a_position'] = self.position_buffer
        self.checker['a_azimuth'] = self.azimuth_buffer
        self.checker['a_elevation'] = self.elevation_buffer

        self.update(**params)

    def render(self, frame_time):
        self.apply_transform(self.checker)
        self.checker.draw('triangles', self.index_buffer)

    def update(self, **params):

        self.parameters.update({k : p for k, p in params.items() if not(p is None)})
        for k, p in self.parameters.items():
            if hasattr(self, 'parse_{}'.format(k)):
                self.checker[k] = getattr(self, 'parse_{}'.format(k))(p)
            else:
                self.checker[k] = p


class RegularMesh(SphericalVisual):

    u_rows = 'u_rows'
    u_cols = 'u_cols'

    parameters = {u_rows: None, u_cols: None}

    def __init__(self, *args, **params):
        SphericalVisual.__init__(self, *args)

        self.sphere = sphere.UVSphere(azim_lvls=100,elev_lvls=50,azimuth_range=2 * np.pi,upper_elev=np.pi / 2)
        self.index_buffer = gloo.IndexBuffer(self.sphere.indices)
        self.position_buffer = gloo.VertexBuffer(self.sphere.a_position)
        self.azimuth_buffer = gloo.VertexBuffer(self.sphere.a_azimuth)
        self.elevation_buffer = gloo.VertexBuffer(self.sphere.a_elevation)

        self.mesh = gloo.Program(self.load_vertex_shader('spherical/checkerboard.vert'),
                                       self.load_shader('spherical/regular_mesh.frag'))
        self.mesh['a_position'] = self.position_buffer
        self.mesh['a_azimuth'] = self.azimuth_buffer
        self.mesh['a_elevation'] = self.elevation_buffer
        self.update(**params)

    def render(self, frame_time):
        self.apply_transform(self.mesh)
        self.mesh.draw('triangles', self.index_buffer)
