"""
MappApp ./Stimulus.py - Base stimulus classes which is inherited by
all stimulus implementations in ./stimulus/.
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
import logging
from glumpy import gl, gloo, transforms
import numpy as np
from typing import List, Dict

import Logging
import Shader
import Model

class AbstractStimulus:

    _texture : np.ndarray = None
    _programs    = dict()
    _models   = dict()

    ########
    # Texture property
    @property
    def texture(self):
        return self._texture
    @texture.setter
    def texture(self, tex):
        self._texture = tex
        self.setUniform('u_texture', self._texture)

    def program(self, pname) -> gloo.Program:
        return self._programs[self.__class__][pname]

    def model(self, mname) -> Model.AbstractModel:
        return self._models[self.__class__][mname]

    def setUniform(self, name, val):
        for pname, p in self._programs[self.__class__].items():
            if name in p._uniforms:
                p[name] = val
            else:
                Logging.logger.log(logging.WARNING, 'Trying to set undefined uniform {} on program {}'
                                   .format(name, pname))


    def addProgram(self, pname, vertex_shader, fragment_shader, geometry_shader=None) -> gloo.Program:
        if self.__class__ not in self._programs:
            self._programs[self.__class__] = dict()
        if pname not in self._programs[self.__class__]:
            self._programs[self.__class__][pname] = gloo.Program(vertex_shader, fragment_shader, geometry_shader)
        return self.program(pname)

    def addModel(self, mname, model_class, **kwargs) -> Model.AbstractModel:
        if self.__class__ not in self._models:
            self._models[self.__class__] = dict()
        if mname not in self._models[self.__class__]:
            self._models[self.__class__][mname] = model_class(**kwargs)
        return self.model(mname)

    def update(self, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        NotImplementedError('update method not implemented for in {}'.format(self.__class__.__name__))


from Shader import Shader
from models import NashCMNSpheres
from helper import NashHelper
from glumpy import glm
class SphericalStimulus(AbstractStimulus):

    def __init__(self, protocol, display):
        self.protocol = protocol
        self.display = display

        ### Set start time
        self.time = 0.0

        ### Create mask model
        self._mask_model = self.addModel('_mask_model',
                                        NashCMNSpheres.UVSphere,
                                        azi=np.pi/2, elv=np.pi, r=1, azitile=20, elvtile=80)
        ### Create mask program
        self._mask_program = self.addProgram('_mask_program',
                                            Shader().addShaderFile('v_ucolor.shader').read(),
                                            Shader().addShaderFile('f_ucolor.shader').read())
        self._mask_program.bind(self._mask_model.vertexBuffer)

        ### Setup basic transformation
        self.rotateMat = glm.rotate(np.eye(4), 90, 0, 0, 1) @ glm.rotate(np.eye(4), 90, 1, 0, 0)
        self.translateMat = glm.translation (0, 0, -6)
        self.projectMat = glm.perspective (45.0, 1, 2.0, 100.0)
        self.transformation = self.rotateMat @ self.translateMat @ self.projectMat

        ### Setup mask program
        for pname, p in self._programs[self.__class__].items():
            p['u_transformation'] = self.transformation
            p['u_rotate'] = NashHelper.rotation2D (np.pi / 4)
            p['u_shift'] = np.array ([0.5, 0.5])
            p['u_map_scale'] = .5 * np.array ([1, 1])
            p['u_color'] = np.array ([0, 0, 0, 1])


    def custom_draw(self):
        pass

    def draw(self, dt):
        """
        METHOD CAN BE RE-IMPLEMENTED.

        By default this method uses the indexBuffer object to draw GL_TRIANGLES.

        :param dt: time since last call
        :return:
        """
        self.time += dt
        #self._programs['u_time'] = self.time

        self.display._glWindow.clear (color=(0.0, 0.0, 0.0, 1.0))
        for i in range(4):
            # Rotate mask around center of screen
            u_rotate2d = NashHelper.rotation2D(np.pi / 4 + np.pi / 2 * i)
            self._mask_program['u_rotate'] = u_rotate2d
            self._mask_program['u_shift'] = np.array([np.real(1.j ** (.5 + i)), np.imag(1.j ** (.5 + i))]) * .7
                ### Apply mask
            gl.glEnable (gl.GL_STENCIL_TEST)
            gl.glStencilOp (gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
            # gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)
            gl.glStencilFunc (gl.GL_ALWAYS, 1, 0xFF)
            gl.glStencilMask (0xFF)
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glColorMask(gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE)
            self._mask_program.draw (gl.GL_TRIANGLES, self._mask_model.indexBuffer)
            gl.glEnable (gl.GL_DEPTH_TEST)
            gl.glColorMask(gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE)
            gl.glStencilFunc (gl.GL_EQUAL, 1, 0xFF)
            gl.glStencilMask (0x00)
            # self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)
            ### Update all mapping related uniforms for all attached programs
            rotateMat = glm.rotate (np.eye (4), 90*i, 0, 0, 1) @ glm.rotate (np.eye (4), 90, 1, 0,0)

            for pname, p in self._programs[self.__class__].items():
                if pname == '_mask_program':
                    p['u_map_scale'] = np.array([1, 1])
                else:
                    p['u_transformation'] = self.transformation# rotateMat @ self.translateMat @ self.projectMat
                    p['u_map_scale'] = .5*np.array([1, 1])
                p['u_rotate'] = NashHelper.rotation2D(np.pi / 4 + np.pi / 2 * i)
                p['u_shift'] = np.array([np.real(1.j ** (.5 + i)), np.imag(1.j ** (.5 + i))]) * .7


            self.custom_draw()
