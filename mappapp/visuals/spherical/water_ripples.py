"""
MappApp ./visuals/water_ripples.py
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
"""

from glumpy import gl
import numpy as np
import imageio
import logging

from mappapp import Logging,Def,Config
from mappapp.core.visual import SphericalVisual
from mappapp.utils import sphere


class RipplesOnStaticBackground(SphericalVisual):

    def __init__(self, *args, u_mod_sign, u_mod_depth, u_mod_shape, u_mod_vel, u_mod_width,
                 u_mod_min_elev=-np.pi/2, u_mod_max_elev=+np.pi/2, u_upper_field_flash=0):

        SphericalVisual.__init__(self, *args)

        ### Create model
        self.sphere_model = self.addModel('sphere',
                                          sphere.UVSphere,
                                          theta_lvls=100,phi_lvls=50,theta_range=2*np.pi,upper_phi=np.pi/2)
        ### Set texture coords
        self.sphere_model.setTextureCoords('uv_standard')
        ## Create routines
        self.sphere_model.createBuffers()

        ### Create program
        self.texture_program = self.addProgram('sphere',
                                                self.load_vertex_shader('spherical/v_tex.glsl'),
                                                self.load_shader('spherical/f_tex.glsl'))
        self.texture_program.bind(self.sphere_model.vertexBuffer)

        ### TODO: loading jpg causes stimulus presentation to hang in beginning; fix this in display class
        ### Set texture
        #im = imageio.imread('samples/earth_uv_no_clouds_8k.jpg', 'jpg')
        #im = imageio.imread('samples/Lighthouse_360_NoLicense.jpg', 'jpg')
        im = imageio.imread('samples/Natural_360_Frame.jpg', 'jpg')
        self.texture_program['u_texture'] = np.flipud(im).copy()

        ### Update parameters
        self.update(u_mod_sign=u_mod_sign, u_mod_depth=u_mod_depth,
                    u_mod_shape=u_mod_shape, u_mod_vel=u_mod_vel,
                    u_mod_width=u_mod_width, u_mod_min_elev=u_mod_min_elev,
                    u_mod_max_elev=u_mod_max_elev, u_upper_field_flash=u_upper_field_flash)

        ### Set ripple program dict/index
        self.ripple_programs = dict()
        self.progI = 1
        self._overflowWarn = False


    def render(self):
        ### First: render textured sphere
        self.texture_program.draw(gl.GL_TRIANGLES, self.sphere_model.indexBuffer)

        ### Second: start new ripple?
        if np.random.randint(Config.Display[Def.DisplayCfg.fps] * 2) == 0:

            # Create program
            self.ripple_programs[self.progI] = self.addProgram(self.progI,
                BasicFileShader().addShaderFile('v_single_ripple_on_background.glsl', subdir='spherical').read(),
                BasicFileShader().addShaderFile('f_single_ripple_on_background.glsl', subdir='spherical').read()
            )
            self.ripple_programs[self.progI].bind(self.sphere_model.vertexBuffer)

            # Set uniforms
            self.ripple_programs[self.progI]['u_mod_sign'] = self.u_mod_sign
            self.ripple_programs[self.progI]['u_mod_depth'] = self.u_mod_depth
            self.ripple_programs[self.progI]['u_mod_shape'] = 1 if self.u_mod_shape == 'normal' else 2
            self.ripple_programs[self.progI]['u_mod_width'] = self.u_mod_width
            self.ripple_programs[self.progI]['u_mod_min_elev'] = self.u_mod_min_elev
            self.ripple_programs[self.progI]['u_mod_max_elev'] = self.u_mod_max_elev
            self.ripple_programs[self.progI]['u_upper_field_flash'] = self.u_upper_field_flash
            # TODO: Note-to-self; this z-layer workaround is stupid, get rid of it
            self.ripple_programs[self.progI]['u_mod_zlayer'] = self.progI

            #self.ripple_programs[self.progI]['u_mod_pos'] = -1.
            self.ripple_programs[self.progI]['u_mod_start_time'] = self.frame_time
            self.ripple_programs[self.progI]['u_mod_vel'] = self.u_mod_vel

            self.progI += 1

        ### Third: render all ripples
        gl.glEnable(gl.GL_ALPHA_TEST)
        for pname in list(self.ripple_programs):
            prog = self.ripple_programs[pname]
            # Increment position
            #prog['u_mod_pos'] += self.u_mod_vel * dt / 20.0
            prog['u_mod_time'] = self.frame_time

            # Remove program if it has passed the sphere
            pos = (prog['u_mod_time'] - prog['u_mod_start_time']) * prog['u_mod_vel'] / 20
            if pos < 0 or pos > 2:
                del self.ripple_programs[pname]
                self.deleteProgram(pname)
                continue

            # Draw ripple
            prog.draw(gl.GL_TRIANGLES, self.sphere_model.indexBuffer)

        gl.glDisable(gl.GL_ALPHA_TEST)

        if not(bool(self.ripple_programs)):
            # Reset program index when no ripple_programs are running (also z-layer height)
            self.progI = 1
            self._overflowWarn = False
        else:
            # Check maximum z-layer value; above some point z-layer differences may be visible in stimulus
            if self.progI > 100 and not(self._overflowWarn):
                Logging.write(logging.WARNING,'Z-layer level of ripple shader programs in stimulus {} '
                                               'has exceeded soft z-layer limit'
                              .format(self.__class__))
                self._overflowWarn = True

    def update(self, u_mod_sign=None, u_mod_depth=None, u_mod_shape=None, u_mod_vel=None,
               u_mod_width=None, u_mod_min_elev=None, u_mod_max_elev=None, u_upper_field_flash=None):

        self.u_mod_sign = u_mod_sign
        self.u_mod_depth = u_mod_depth
        self.u_mod_shape = u_mod_shape
        self.u_mod_vel = u_mod_vel
        self.u_mod_width = u_mod_width
        self.u_mod_min_elev = u_mod_min_elev
        self.u_mod_max_elev = u_mod_max_elev
        self.u_upper_field_flash = u_upper_field_flash
"""