"""
MappApp ./Visuals.py - Base stimulus classes which is inherited by
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
from glumpy import gl, gloo
import logging
import numpy as np
from typing import Union

import Logging
import Model

################################
### Abstract visual class

class AbstractVisual:

    _programs    = dict()
    _models   = dict()

    _warns = list()

    parameters = dict()

    def __init__(self, protocol, display):
        self.frame_time = None
        self.protocol = protocol
        self.display = display

    def program(self, pname) -> gloo.Program:
        return self._programs[self.__class__][pname]

    def model(self, mname) -> Model.AbstractModel:
        return self._models[self.__class__][mname]

    def setGlobalUniform(self, name, val):
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


    def draw(self, idx, time):
        raise NotImplementedError('Method draw() not implemented in {}'.format(self.__class__))

    def render(self):
        raise NotImplementedError('Method render() not implemented in {}'.format(self.__class__))

    def update(self, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        Logging.write(logging.WARNING, 'Update method called but not implemented for stimulus {}'.format(self.__class__))


################################
### Spherical stimulus class

from glumpy import glm

import Config
import Def
from helper import Geometry
import IPC
from models import BasicSphere
from Shader import BasicFileShader

from time import perf_counter

class SphericalVisual(AbstractVisual):

    _mask_name = '_mask'

    def __init__(self, *args):
        AbstractVisual.__init__(self, *args)


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


    def draw(self, frame_idx, frame_time):
        self.frame_idx = frame_idx
        self.frame_time = frame_time
        #self.display._glWindow.clear(color=(1.0, 0.0, 0.0, 1.0))

        ### Set time uniforms
        self.setGlobalUniform('u_stime', self.frame_time)

        #### Set 2D scaling for aspect 1
        width = Config.Display[Def.DisplayCfg.window_width]
        height = Config.Display[Def.DisplayCfg.window_height]
        if height > width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, width/height])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([height/width, 1])
        self.setGlobalUniform('u_mapcalib_aspectscale', u_mapcalib_aspectscale)

        ### Set relative size
        self.setGlobalUniform('u_mapcalib_scale', Config.Display[Def.DisplayCfg.sph_view_scale] * np.array ([1, 1]))

        ### Set 3D transform
        distance = Config.Display[Def.DisplayCfg.sph_view_distance]
        fov = 240.0/distance
        translate3d = glm.translation(0, 0, -distance)
        project3d = glm.perspective(fov, 1, 2.0, 100.0)
        self.setGlobalUniform('u_mapcalib_transform3d', translate3d @ project3d)

        ### Clear
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)

        ### Enable stencil and blending
        gl.glEnable(gl.GL_STENCIL_TEST)
        gl.glEnable(gl.GL_BLEND)

        ### Calculate elevation rotation
        rotate_elev_3d = glm.rotate(np.eye(4), -90 + Config.Display[Def.DisplayCfg.sph_view_elev_angle], 1, 0, 0)

        for i in range(4):

            ### (Re)Set basic 3D elevation rotation
            self.setGlobalUniform('u_mapcalib_rotate3d', glm.rotate(np.eye(4), 225, 0, 0, 1) @ rotate_elev_3d)

            ### 2D rotation around center of screen
            self.setGlobalUniform('u_mapcalib_rotate2d', Geometry.rotation2D(np.pi / 4 - np.pi / 2 * i))

            ### 2D translation radially
            radial_offset = np.array([np.real(1.j ** (.5 + i)), np.imag(1.j ** (.5 + i))]) * Config.Display[Def.DisplayCfg.sph_pos_glob_radial_offset]
            xy_offset = np.array([Config.Display[Def.DisplayCfg.glob_x_pos], Config.Display[Def.DisplayCfg.glob_y_pos]])
            self.setGlobalUniform('u_mapcalib_translate2d', radial_offset + xy_offset)

            ### Write stencil buffer from mask sphere
            gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE)
            gl.glStencilFunc(gl.GL_ALWAYS, 1, 0xFF)
            gl.glStencilMask(0xFF)
            gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glColorMask(gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE, gl.GL_FALSE)

            ### Draw mask
            self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)

            gl.glColorMask(gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE, gl.GL_TRUE)
            gl.glStencilFunc(gl.GL_EQUAL, 1, 0xFF)
            gl.glStencilMask(0x00)
            gl.glEnable(gl.GL_DEPTH_TEST)

            ### For debugging:
            #self._mask_program.draw(gl.GL_TRIANGLES, self._mask_model.indexBuffer)

            ### Apply 90*i degree rotation for rendering different parts of actual sphere
            azim_angle = Config.Display[Def.DisplayCfg.sph_view_azim_angle]
            self.setGlobalUniform('u_mapcalib_rotate3d', glm.rotate(np.eye(4), 90 * i + azim_angle, 0, 0, 1) @ rotate_elev_3d)

            ### Call the rendering function of the subclass
            self.render()


################################
### Plane stimulus class

class PlanarVisual(AbstractVisual):

    def __init__(self, *args):
        AbstractVisual.__init__(self, *args)

    def draw(self, frame_idx, frame_time):
        self.display._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))

        ### Construct vertices
        height = Config.Display[Def.DisplayCfg.window_height]
        width = Config.Display[Def.DisplayCfg.window_width]

        ### Set aspect scale to square
        if width > height:
            self.u_mapcalib_xscale = height/width
            self.u_mapcalib_yscale = 1.
        else:
            self.u_mapcalib_xscale = 1.
            self.u_mapcalib_yscale = width/height

        ### Set 2d translation
        self.u_glob_x_position = Config.Display[Def.DisplayCfg.glob_x_pos]
        self.u_glob_y_position = Config.Display[Def.DisplayCfg.glob_y_pos]

        ### Scale
        #self.u_mapcalib_xscale *= Config.Display[Def.DisplayCfg.pla_xextent]
        #self.u_mapcalib_yscale *= Config.Display[Def.DisplayCfg.pla_yextent]

        ### Extents
        self.u_mapcalib_xextent = Config.Display[Def.DisplayCfg.pla_xextent]
        self.u_mapcalib_yextent = Config.Display[Def.DisplayCfg.pla_yextent]

        ### Set real world size multiplier [mm]
        # (PlanarVisual's positions are normalized to the smaller side of the screen)
        self.u_small_side_size = Config.Display[Def.DisplayCfg.pla_small_side]

        ### Set uniforms
        self.setGlobalUniform('u_mapcalib_xscale', self.u_mapcalib_xscale)
        self.setGlobalUniform('u_mapcalib_yscale', self.u_mapcalib_yscale)
        self.setGlobalUniform('u_mapcalib_xextent', self.u_mapcalib_xextent)
        self.setGlobalUniform('u_mapcalib_yextent', self.u_mapcalib_yextent)
        self.setGlobalUniform('u_small_side_size', self.u_small_side_size)
        self.setGlobalUniform('u_glob_x_position', self.u_glob_x_position)
        self.setGlobalUniform('u_glob_y_position', self.u_glob_y_position)

        ### Call the rendering function of the subclass
        self.render()
