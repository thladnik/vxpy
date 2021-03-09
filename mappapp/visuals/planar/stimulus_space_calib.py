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

from mappapp.core.visual import PlanarVisual
from mappapp.utils import plane

"""
MappApp ./visuals/planar/calibration.py
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
import cv2 as cv

from mappapp.core.visual import PlanarVisual
from mappapp.utils import plane


class QRcalib(PlanarVisual):

    u_sf_vertical = 'u_sf_vertical'
    u_sf_horizontal = 'u_sf_horizontal'
    u_checker_pattern = 'u_checker_pattern'
    qrimg_fn = 'qrimg_fn'

    parameters = {u_sf_vertical: 0.1,
                  u_sf_horizontal: 0.1,
                  u_checker_pattern: True,
                  qrimg_fn: 'QRreg.png'}
    interface = []
    def __init__(self, *args, vert_shader=None, **params):
        PlanarVisual.__init__(self, *args)
        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mrender = gloo.Program(self.load_vertex_shader('planar/texture_mapping.vert'),
                                    self.load_shader('planar/texture_mapping.frag'))
        self.mrender['a_position'] = [(+1, -1), (+1, +1), (-1, -1), (-1, +1)]
        self.mrender['u_texture']  = cv.imread('QRreg.png',cv.IMREAD_GRAYSCALE)
        self.mrender['a_texcoord'] = [(0., 0.), (0., 1.), (1., 0.), (1., 1.)]

        self.update(**params)

    def render(self, frame_time):
        self.apply_transform(self.mrender)
        self.mrender.draw('triangle_strip')