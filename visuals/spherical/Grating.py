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

from glumpy import gl
import time

from Shader import BasicFileShader
from Visuals import SphericalVisual
from models import BasicSphere


class BlackWhiteGrating(SphericalVisual):

    u_shape = 'u_shape'
    u_direction = 'u_direction'
    u_spat_period = 'u_spat_period'
    u_ang_velocity = 'u_ang_velocity'

    parameters = {u_shape: None, u_direction:None, u_ang_velocity:None, u_spat_period:None}

    def __init__(self, *args, **params):

        SphericalVisual.__init__(self, *args)

        ### Set up model
        self.sphere = self.addModel('sphere',
                                    BasicSphere.UVSphere,
                                    theta_lvls=60, phi_lvls=30)
        self.sphere.createBuffers()

        ### Set up program
        self.grating = self.addProgram('grating',
                                       BasicFileShader().addShaderFile('spherical/grating.vert').read(),
                                       BasicFileShader().addShaderFile('spherical/grating.frag').read())
        self.grating.bind(self.sphere.vertexBuffer)

        self.update(**params)

        self.t = time.time()

    def render(self):
        self.grating['u_stime'] = time.time() - self.t
        self.grating.draw(gl.GL_TRIANGLES, self.sphere.indexBuffer)

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
