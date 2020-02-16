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
from typing import Union

import Logging
import Shader
import Model

################################
### Abstract stimulus class

class AbstractStimulus:

    _texture : np.ndarray = None
    _programs    = dict()
    _models   = dict()
    _stimuli  = list()

    _warns = list()


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
                Logging.logger.log(logging.DEBUG, 'Trying to set undefined uniform {} on program {} in class {}'
                                   .format(name, pname, self.__class__))

    def addProgram(self, pname, vertex_shader, fragment_shader, geometry_shader=None) -> gloo.Program:
        if self.__class__ not in self._programs:
            self._programs[self.__class__] = dict()
        if pname not in self._programs[self.__class__]:
            Logging.write(logging.DEBUG, 'Create program {} in class {}'
                          .format(pname, self.__class__))
            self._programs[self.__class__][pname] = gloo.Program(vertex_shader, fragment_shader, geometry_shader)
        return self.program(pname)

    def deleteProgram(self, pname):
        if self.__class__ in self._programs and pname in self._programs[self.__class__]:
            Logging.write(logging.DEBUG, 'Delete program {} in class {}'
                          .format(pname, self.__class__))
            del self._programs[self.__class__][pname]
            if pname in self._warns:
                self._warns.pop(self._warns.index(pname))

    def addModel(self, mname, model_class, **kwargs) -> Union[Model.AbstractModel,
                                                              Model.SphereModel]:
        if self.__class__ not in self._models:
            self._models[self.__class__] = dict()
        if mname not in self._models[self.__class__]:
            Logging.write(logging.DEBUG, 'Create model {} in class {}'
                          .format(mname, self.__class__))
            self._models[self.__class__][mname] = model_class(**kwargs)
        return self.model(mname)


    def draw(self, dt):
        NotImplementedError('Method draw() not implemented in {}'.format(self.__class__))

    def render(self, dt):
        NotImplementedError('Method render() not implemented in {}'.format(self.__class__))

    def update(self, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        Logging.write(logging.WARNING, 'Update method called but not implemented for stimulus {}'.format(self.__class__))


################################
### Spherical stimulus class

from Shader import BasicFileShader
from models import BasicSphere
from helper import Geometry
from glumpy import glm

import Config
from Definition import Display

class SphericalStimulus(AbstractStimulus):

    _mask_name = '_mask'

    def __init__(self, protocol, display):
        self.protocol = protocol
        self.display = display

        ### Set state
        self._started = False
        self._running = False
        self._stopped = False

        ### Create mask model
        self._mask_model = self.addModel(self._mask_name,
                                         BasicSphere.UVSphere,
                                         theta_lvls=50, phi_lvls=50,
                                         theta_range=np.pi/2, upper_phi=np.pi/4, radius=1.0)
        self._mask_model.createBuffers()
        ### Create mask program
        self._mask_program = self.addProgram(self._mask_name,
                                             BasicFileShader().addShaderFile('v_sphere_map.glsl', subdir='spherical').read(),
                                            'void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }')
        self._mask_program.bind(self._mask_model.vertexBuffer)


    def start(self):
        self._started = True

    def draw(self, dt):
        self.display._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))

        if self._running and not(self._stopped):
            self.time += dt
        elif self._started and not(self._running):
            self.time = 0.0
            self._running = True
        elif self._stopped or not(self._started):
            return

        ### Set time uniforms
        self.setUniform('u_stime', self.time)
        self.setUniform('u_ptime', self.protocol._time)

        #### Set 2D scaling for aspect 1:1
        width = Config.Display[Display.window_width]
        height = Config.Display[Display.window_height]
        if height > width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, width/height])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([height/width, 1])

        ### Set 3D translation and projection
        distance = Config.Display[Display.view_distance]
        translate3d = glm.translation(0, 0, -distance)
        fov = 240.0/distance
        project3d = glm.perspective(fov, 1, 2.0, 100.0)

        ### Set uniforms
        self.setUniform('u_mapcalib_aspectscale', u_mapcalib_aspectscale)
        self.setUniform('u_mapcalib_transform3d', translate3d @ project3d)
        self.setUniform('u_mapcalib_scale', Config.Display[Display.view_scale] * np.array ([1, 1]))

        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)


        for i in range(4):
            gl.glEnable(gl.GL_STENCIL_TEST)
            gl.glEnable(gl.GL_BLEND)

            elev = Config.Display[Display.view_elev_angle]
            elevRot3d = glm.rotate(np.eye(4), -90 + elev, 1, 0, 0)
            ### Rotate 3d model
            self.setUniform('u_mapcalib_rotate3d', glm.rotate(np.eye(4), 225, 0, 0, 1) @ elevRot3d)
            ### Rotate around center of screen
            self.setUniform('u_mapcalib_rotate2d', Geometry.rotation2D(np.pi / 4 - np.pi / 2 * i))
            ### Translate radially
            radialOffset = np.array([np.real(1.j ** (.5 + i)), np.imag(1.j ** (.5 + i))]) * Config.Display[Display.pos_glob_radial_offset]
            xyOffset =  np.array([Config.Display[Display.pos_glob_x_pos], Config.Display[Display.pos_glob_y_pos]])
            translate2d = radialOffset + xyOffset
            self.setUniform('u_mapcalib_translate2d', translate2d)

            ### Write stencil buffer from mask sphere
            gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
            gl.glStencilFunc(gl.GL_ALWAYS, 1, 0xFF)
            gl.glStencilMask(0xFF)
            gl.glClear(gl.GL_STENCIL_BUFFER_BIT)  # THIS HAS TO BE RIGHT HERE !!!
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glColorMask(gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE)
            self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)
            gl.glColorMask(gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE)
            gl.glStencilFunc(gl.GL_EQUAL, 1, 0xFF)
            gl.glStencilMask(0x00)
            gl.glEnable(gl.GL_DEPTH_TEST)

            ### For debugging:
            #self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)

            ### Apply 90*i degree rotation for rendering different parts of actual sphere
            azim_angle = Config.Display[Display.view_azim_angle]
            self.setUniform('u_mapcalib_rotate3d', glm.rotate(np.eye(4), 90*i + azim_angle, 0, 0, 1) @ elevRot3d)

            ### Call the rendering function of the subclass
            self.render(dt)

################################
### Plane stimulus class

class PlaneStimulus(AbstractStimulus):

    def __init__(self, display, protocol):
        self.display = display
        self.protocol = protocol

        ### Set state
        self._started = False
        self._running = False
        self._stopped = False


    def start(self):
        self._started = True


    def draw(self, dt):
        self.display._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))

        if self._running and not(self._stopped):
            self.time += dt
        elif self._started and not(self._running):
            self.time = 0.0
            self._running = True
        elif self._stopped or not(self._started):
            return


        ### Construct vertices
        height = Config.Display[Display.window_height]
        width = Config.Display[Display.window_width]

        if width > height:
            self.u_mapcalib_xscale = height/width

        self.setUniform('u_mapcalib_xscale', self.u_mapcalib_xscale)

        ### Call the rendering function of the subclass
        self.render(dt)
