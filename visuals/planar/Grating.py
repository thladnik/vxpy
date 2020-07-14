"""
MappApp ./visuals/planar/Grating.py -
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

from Visuals import PlanarVisual
from models import BasicPlane
from Shader import BasicFileShader

from glumpy import gl
import time
class BlackAndWhiteHorizontalGrating(PlanarVisual):

    def __init__(self, *args, orientation, shape, velocity, num):
        PlanarVisual.__init__(self, *args)

        self.plane = self.addModel('planar',
                                   BasicPlane.VerticalXYPlane)
        self.plane.createBuffers()

        self.grating = self.addProgram('checker',
                                       BasicFileShader().addShaderFile('planar/grating_v.glsl').read(),
                                       BasicFileShader().addShaderFile('planar/grating_f.glsl').read())
        self.grating.bind(self.plane.vertexBuffer)

        self.update(shape=shape, orientation=orientation, velocity=velocity, num=num)

        self.t = time.time()


    def render(self):
        self.grating['u_stime'] = time.time() - self.t
        self.grating.draw(gl.GL_TRIANGLES, self.plane.indexBuffer)

    def update(self, shape=None, orientation=None, velocity=None, num=None):

        if shape is not None:
            self._setShape(shape)

        if orientation is not None:
            self._setOrientation(orientation)

        if velocity is not None:
            self.grating['u_velocity'] = velocity

        if num is not None and num > 0:
            self.grating['u_stripes_num'] = num

    def _setShape(self, shape):
        if shape == 'rectangular':
            self.grating['u_shape'] = 1
        elif shape == 'sinusoidal':
            self.grating['u_shape'] = 2

    def _setOrientation(self, orientation):
        if orientation == 'vertical':
            self.grating['u_orientation'] = 1
        elif orientation == 'horizontal':
            self.grating['u_orientation'] = 2