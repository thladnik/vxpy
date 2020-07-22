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

    u_shape = 'u_shape'
    u_direction = 'u_direction'
    u_spat_period = 'u_spat_period'
    u_lin_velocity = 'u_lin_velocity'

    parameters = {u_shape: None, u_direction:None, u_lin_velocity:None, u_spat_period:None}

    def __init__(self, *args, **params):
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

        self.update(**params)


        self.t = time.time()


    def render(self):
        self.grating['u_stime'] = time.time() - self.t
        self.grating.draw(gl.GL_TRIANGLES, self.plane.indexBuffer)

    def update(self, **params):

        if params.get(self.u_shape) is not None:
            params[self.u_shape] = self.parseShape(params.get(self.u_shape))

        if params.get(self.u_direction) is not None:
            params[self.u_direction] = self.parseDirection(params.get(self.u_direction))

        self.parameters.update({k : p for k, p in params.items() if not(p is None)})
        for k, p in self.parameters.items():
            self.grating[k] = p

    def parseShape(self, shape):
        return 1 if shape == 'rectangular' else 2  # 'sinusoidal'


    def parseDirection(self, orientation):
        return 1 if orientation == 'vertical' else 2  # 'horizontal'
