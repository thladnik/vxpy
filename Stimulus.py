"""
MappApp ./Stimulus.py - Base stimulus classes which is inherited by
all stimulus implementations in ./stimulus/.
Copyright (C) 2020 Tim Hladnik, Yue Zhang

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

################################
### Abstract stimulus class

class AbstractStimulus:

    _texture : np.ndarray = None
    _programs    = dict()
    _models   = dict()

    _warns = list()

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
                # Display warning once if uniform does not exist in program
                sign = '{}>{}>{}'.format(self.__class__, pname, name)
                if sign in self._warns:
                    continue
                self._warns.append(sign)
                Logging.logger.log(logging.WARNING, 'Trying to set undefined uniform {} on program {} in class {}'
                                   .format(name, pname, self.__class__))

    def addProgram(self, pname, vertex_shader, fragment_shader, geometry_shader=None) -> gloo.Program:
        if self.__class__ not in self._programs:
            self._programs[self.__class__] = dict()
        if pname not in self._programs[self.__class__]:
            Logging.write(logging.DEBUG, 'Create program {} in class {}'
                          .format(pname, self.__class__))
            self._programs[self.__class__][pname] = gloo.Program(vertex_shader, fragment_shader, geometry_shader)
        return self.program(pname)

    def addModel(self, mname, model_class, **kwargs) -> Model.AbstractModel:
        if self.__class__ not in self._models:
            self._models[self.__class__] = dict()
        if mname not in self._models[self.__class__]:
            Logging.write(logging.DEBUG, 'Create model {} in class {}'
                          .format(mname, self.__class__))
            self._models[self.__class__][mname] = model_class(**kwargs)
        return self.model(mname)

    def update(self, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        Logging.write(logging.WARNING, 'Update method called but not implemented for stimulus {}'.format(self.__class__))


################################
### Spherical stimulus class

from Shader import Shader
from models import CMNSpheres
from helper import Geometry
from glumpy import glm

import Config
import Definition

class SphericalStimulus(AbstractStimulus):

    _mask_name = '_mask'

    def __init__(self, protocol, display):
        self.protocol = protocol
        self.display = display

        ### Set start time
        self.time = 0.0

        ### Create mask model
        self._mask_model = self.addModel(self._mask_name,
                                         CMNSpheres.UVSphere,
                                         azi=np.pi/2, elv=np.pi, r=1, azitile=20, elvtile=80)
        ### Create mask program
        self._mask_program = self.addProgram(self._mask_name,
                                            Shader().addShaderFile('v_ucolor.shader').read(),
                                            'void main() { gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0); }')
        self._mask_program.bind(self._mask_model.vertexBuffer)


    def render(self):
        pass

    def draw(self, dt):
        self.time += dt
        self.setUniform('u_stime', self.time)
        self.setUniform('u_ptime', self.protocol._time)


        ### Set 2d translation in window
        u_global_shift = np.array([
            Config.Display[Definition.DisplayConfig.float_pos_glob_x_pos],
            Config.Display[Definition.DisplayConfig.float_pos_glob_y_pos]
        ])
        #self.protocol._current.program['u_global_shift'] = u_global_shift

        #### Set scaling for aspect 1:1
        width = Config.Display[Definition.DisplayConfig.int_window_width]
        height = Config.Display[Definition.DisplayConfig.int_window_height]
        if height > width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, width/height])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([height/width, 1])

        translate3d = glm.translation (0, 0, -6)
        project3d = glm.perspective (45.0, 1, 2.0, 100.0)

        ### Set uniforms
        self.setUniform('u_mapcalib_aspectscale', u_mapcalib_aspectscale)
        self.setUniform('u_mapcalib_transform3d', translate3d @ project3d)
        self.setUniform('u_mapcalib_scale', 1.2 * np.array ([1, 1]))

        self.display._glWindow.clear (color=(0.0, 0.0, 0.5, 1.0))
        for i in range(4):
            ### Rotate 3d model
            self.setUniform('u_mapcalib_rotate3d', glm.rotate(np.eye(4), 90, 0, 0, 1) @ glm.rotate(np.eye(4), 90, 1, 0, 0))
            ### Rotate around center of screen
            #self.setUniform('u_mapcalib_rotate2d', Geometry.rotation2D(np.pi / 4 + np.pi / 2 * i))
            self.setUniform('u_mapcalib_rotate2d', Geometry.rotation2D(np.pi / 4 - np.pi / 2 * i))
            ### Translate radially
            self.setUniform('u_mapcalib_translate2d', np.array([np.real(1.j ** (.5 + i)), np.imag(1.j ** (.5 + i))]) * 0.7)

            if True:
                ### Write stencil buffer from mask sphere
                gl.glEnable (gl.GL_STENCIL_TEST)
                gl.glStencilOp (gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
                # gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)
                gl.glStencilFunc (gl.GL_ALWAYS, 1, 0xFF)
                gl.glStencilMask (0xFF)
                gl.glDisable(gl.GL_DEPTH_TEST)
                gl.glColorMask(gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE)
                self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)
                gl.glColorMask(gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE)
                gl.glStencilFunc(gl.GL_EQUAL, 1, 0xFF)
                gl.glStencilMask(0x00)
                #self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)

            gl.glEnable (gl.GL_DEPTH_TEST)
            ### Apply 90*i degree rotation for rendering different parts of actual sphere
            self.setUniform('u_mapcalib_rotate3d', glm.rotate (np.eye (4), -90*i, 0, 0, 1) @ glm.rotate (np.eye (4), 90, 1, 0,0))

            ### Call the
            self.render()
