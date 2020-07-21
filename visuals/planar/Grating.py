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
class BlackAndWhiteGrating(PlanarVisual):

    def __init__(self, *args, direction, shape, lin_velocity, spat_period):
        """

        :param args: positional arguments to parent class
        :param direction: movement direction of grating; either 'vertical' or 'horizontal'
        :param shape: shape of grating; either 'rectangular' or 'sinusoidal'; rectangular is a zero-rectified sinusoidal
        :param lin_velocity: <float> linear velocity of grating in [mm/s]
        :param spat_period: <float> spatial period of the grating in [mm]
        """
        # TODO: add temporal velocity and do automatic conversion
        PlanarVisual.__init__(self, *args)

        self.plane = self.addModel('planar',
                                   BasicPlane.VerticalXYPlane)
        self.plane.createBuffers()

        self.grating = self.addProgram('checker',
                                       BasicFileShader().addShaderFile('planar/grating_v.glsl').read(),
                                       BasicFileShader().addShaderFile('planar/grating_f.glsl').read())
        self.grating.bind(self.plane.vertexBuffer)

        self.update(shape=shape, direction=direction, lin_velocity=lin_velocity, spat_period=spat_period)

        self.t = time.time()


    def render(self):
        self.grating['u_stime'] = time.time() - self.t
        self.grating.draw(gl.GL_TRIANGLES, self.plane.indexBuffer)

    def update(self, shape=None, direction=None, lin_velocity=None, spat_period=None):

        if shape is not None:
            self._setShape(shape)

        if direction is not None:
            self._setOrientation(direction)

        if lin_velocity is not None:
            self.grating['u_lin_velocity'] = lin_velocity

        if spat_period is not None and spat_period > 0:
            self.grating['u_spatial_period'] = spat_period

    def _setShape(self, shape):
        if shape == 'rectangular':
            self.grating['u_shape'] = 1
        elif shape == 'sinusoidal':
            self.grating['u_shape'] = 2

    def _setOrientation(self, orientation):
        if orientation == 'vertical':
            self.grating['u_direction'] = 1
        elif orientation == 'horizontal':
            self.grating['u_direction'] = 2