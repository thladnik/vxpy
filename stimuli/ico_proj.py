"""
MappApp ./stimuli/ico_proj.py - icoCMN stimuli
Copyright (C) 2020 Yue Zhang

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

import numpy as np
from scipy import signal

from glumpy import gl, gloo,glm

import Logging
import Shader
from helper.nash_helper import *
from Stimulus import SphericalStimulus
from models import dividable_icosphere

# TODO: Fix shader compatibility, write stimulus, test if stimulus class allows multiple program
class icoCMN(SphericalStimulus):

    _sphere_model = dividable_icosphere.diviable_icosphere(subdivisionTimes=1)
    _mask_model   = dividable_icosphere.mask_UVsphere(np.pi/2,np.pi,1,20,80)
    _base_vertex_shader = "_v_empty.shader"
    _base_fragment_shader = "_f_empty.shader"
    _vertex_shader = "v_tex.shader"
    _vertex_mask_shader = "v_ucolor.shader"
    _fragment_shader = 'f_tex.shader'
    _fragment_mask_shader = 'f_ucolor.shader'

    def __init__(self, protocol,display):
        """

        :param protocol: protocol of which stimulus is currently part of

        :param orientation: orientation of grating; either 'vertical' or 'horizontal'
        :param shape: shape of underlying function; either 'rectangular' or 'sinusoidal'
        :param velocity:
        :param num:
        """
        super().__init__(protocol,display)
        self._sphere_model.build()
        Isize = self._sphere_model.indexBuffer.size
        sp_sigma = .8  # spatial CR
        tp_sigma = 15  # temporal CR
        spkernel = np.exp (-(self._sphere_model.intertile_distance ** 2) / (2 * sp_sigma ** 2))
        spkernel *= spkernel > .001
        tp_min_length = np.int (np.ceil (np.sqrt (-2 * tp_sigma ** 2 * np.log (.01 * tp_sigma * np.sqrt (2 * np.pi)))))
        tpkernel = np.linspace (-tp_min_length, tp_min_length, num=2 * tp_min_length + 1)
        tpkernel = 1 / (tp_sigma * np.sqrt (2 * np.pi)) * np.exp (-tpkernel ** 2 / (2 * tp_sigma ** 2))
        tpkernel *= tpkernel > .001

        flowvec = np.random.normal (size=[np.int (Isize / 3), 500, 3])  # Random white noise motion vector
        flowvec /= vecNorm (flowvec)[:, :, None]
        tpsmooth_x = signal.convolve (flowvec[:, :, 0], tpkernel[np.newaxis, :], mode='same')
        tpsmooth_y = signal.convolve (flowvec[:, :, 1], tpkernel[np.newaxis, :], mode='same')
        tpsmooth_z = signal.convolve (flowvec[:, :, 2], tpkernel[np.newaxis, :], mode='same')
        spsmooth_x = np.dot (spkernel, tpsmooth_x)
        spsmooth_y = np.dot (spkernel, tpsmooth_y)
        spsmooth_z = np.dot (spkernel, tpsmooth_z)  #
        spsmooth_Q = qn(np.array ([spsmooth_x, spsmooth_y, spsmooth_z]).transpose ([1, 2, 0]))

        tileCen_Q = qn (self._sphere_model.tile_center)
        tileOri_Q1 = qn (np.real (self._sphere_model.tile_orientation)).normalize[:, None]
        tileOri_Q2 = qn (np.imag (self._sphere_model.tile_orientation)).normalize[:, None]
        projected_motmat = projection (tileCen_Q[:, None], spsmooth_Q)
        self.motmatFull = qdot (tileOri_Q1, projected_motmat) - 1.j * qdot (tileOri_Q2, projected_motmat)
        spsmooth_azi = np.angle (spsmooth_x + spsmooth_y * 1.j) * 0 + 1
        spsmooth_elv = np.angle (np.abs (spsmooth_x + spsmooth_y * 1.j) + spsmooth_z * 1.j) * 0
        startpoint = cen2tri (np.random.rand (np.int (Isize / 3)), np.random.rand (np.int (Isize / 3)), .1)
        self._sphere_model.vertexBuffer['texcoord'] = startpoint.reshape([-1,2])
        self._mask_model.r = np.mean(vecNorm(self._sphere_model.vertexBuffer['position']))
        self._mask_model.build()

        self.program = gloo.Program (self.getVertexShader (), fragment=self.getFragmentShader ())
        self.mask_program = gloo.Program(Shader.Shader(self._base_vertex_shader,self._vertex_mask_shader).getString(),
                                         fragment = Shader.Shader(self._base_fragment_shader,self._fragment_mask_shader).getString())
        self.program.bind(self._sphere_model.vertexBuffer)
        self.mask_program.bind(self._mask_model.vertexBuffer)

        # self.program_model = np.eye (4, dtype=np.float32)
        self.rotateMat = glm.rotate(np.eye(4), 90, 0, 0, 1) @ glm.rotate(np.eye(4), 90, 1, 0, 0)
        self.translateMat = glm.translation (0, 0, -6)
        self.projectMat = glm.perspective (45.0, 1, 2.0, 100.0)
        self.transformation = self.rotateMat @ self.translateMat @ self.projectMat

        self.program['texture']= np.uint8(np.random.randint(0, 2, [100, 100, 1]) * np.array([[[1, 1, 1]]]) * 255)
        self.program['texture'].wrapping = gl.GL_REPEAT

        self.program['u_transformation'] = self.transformation
        self.program['u_rotate'] = rotation2D (np.pi / 4)
        self.program['u_shift'] = np.array ([0.5, 0.5])
        self.program['u_scale'] = .5 * np.array ([1, 1])

        self.mask_program['u_transformation'] = self.transformation
        self.mask_program['u_rotate'] = rotation2D (np.pi / 4)
        self.mask_program['u_shift'] = np.array ([0.5, 0.5])
        self.mask_program['u_scale'] = .5 * np.array ([1, 1])
        self.mask_program['u_color'] = np.array ([0, 0, 0, 1])
        self.i = 0

    def draw(self, dt) :
        """
        METHOD CAN BE RE-IMPLEMENTED.

        By default this method uses the indexBuffer object to draw GL_TRIANGLES.

        :param dt: time since last call
        :return:
        """
        # self.program['u_time'] = self.time

        ### GL commands
        self.display._glWindow.clear (color=(0.0, 0.0, 0.0, 1.0))
        tidx = np.mod(self.i,499)
        motmat = np.repeat(self.motmatFull[:,tidx],3,axis = 0)
        self._sphere_model.vertexBuffer['texcoord'] += np.array([np.real(motmat), np.imag(motmat)]).T / 80
        for i in np.arange (4) :
            self.rotateMat = glm.rotate (np.eye (4), 90, 0, 0, 1) @ glm.rotate (np.eye (4), 90, 1, 0,0)
            # self.transformation = self.rotateMat @ self.translateMat @ self.projectMat
            self.mask_program['u_transformation'] = self.transformation
            self.mask_program['u_rotate'] = rotation2D (np.pi / 4 + np.pi / 2 * i)
            self.mask_program['u_shift'] = np.array ([np.real (1.j ** (.5 + i)), np.imag (1.j ** (.5 + i))]) * .7

            self.program['u_transformation'] = self.rotateMat @ self.translateMat @ self.projectMat
            self.program['u_rotate'] = rotation2D (np.pi / 4 + np.pi / 2 * i)
            self.program['u_shift'] = np.array ([np.real (1.j ** (.5 + i)), np.imag (1.j ** (.5 + i))]) * .7

            gl.glEnable (gl.GL_STENCIL_TEST)
            gl.glStencilOp (gl.GL_KEEP, gl.GL_KEEP, gl.GL_REPLACE);
            # gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)
            gl.glStencilFunc (gl.GL_ALWAYS, 1, 0xFF)
            gl.glStencilMask (0xFF)
            gl.glDisable (gl.GL_DEPTH_TEST)

            self.mask_program.draw (gl.GL_TRIANGLES, self._mask_model.indexBuffer)
            gl.glEnable (gl.GL_DEPTH_TEST)
            gl.glStencilFunc (gl.GL_EQUAL, 1, 0xFF)
            gl.glStencilMask (0x00)

            self.program.draw (gl.GL_TRIANGLES, self._sphere_model.indexBuffer)
        self.i += 1