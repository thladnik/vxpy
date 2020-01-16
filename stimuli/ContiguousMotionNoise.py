"""
MappApp ./stimuli/ContiguousMotionNoise.py - icoCMN stimuli
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
from Shader import Shader
from helper import Geometry
from Stimulus import SphericalStimulus
from models import CMNSpheres

# TODO: Fix shader compatibility, write stimulus, test if stimulus class allows multiple program
class IcoCMN(SphericalStimulus):


    def __init__(self, protocol, display):
        SphericalStimulus.__init__(self, protocol, display)

        ### Define model
        self.sphere_model = self.addModel('sphere',
                                          CMNSpheres.IcoSphere,
                                          subdivisionTimes=1)

        ### Define program
        self.sphere_program = self.addProgram('sphere',
                                              Shader().addShaderFile('v_tex.shader').read(),
                                              Shader().addShaderFile('f_tex.shader').read())

        ### Bind vertex buffer
        self.sphere_program.bind(self.sphere_model.vertexBuffer)

        Isize = self.sphere_model.indexBuffer.size
        sp_sigma = .8  # spatial CR
        tp_sigma = 15  # temporal CR
        spkernel = np.exp (-(self.sphere_model.intertile_distance ** 2) / (2 * sp_sigma ** 2))
        spkernel *= spkernel > .001
        tp_min_length = np.int (np.ceil (np.sqrt (-2 * tp_sigma ** 2 * np.log (.01 * tp_sigma * np.sqrt (2 * np.pi)))))
        tpkernel = np.linspace (-tp_min_length, tp_min_length, num=2 * tp_min_length + 1)
        tpkernel = 1 / (tp_sigma * np.sqrt (2 * np.pi)) * np.exp (-tpkernel ** 2 / (2 * tp_sigma ** 2))
        tpkernel *= tpkernel > .01

        flowvec = np.random.normal (size=[np.int (Isize / 3), 500, 3])  # Random white noise motion vector
        flowvec /= Geometry.vecNorm (flowvec)[:, :, None]
        tpsmooth_x = signal.convolve (flowvec[:, :, 0], tpkernel[np.newaxis, :], mode='same')
        tpsmooth_y = signal.convolve (flowvec[:, :, 1], tpkernel[np.newaxis, :], mode='same')
        tpsmooth_z = signal.convolve (flowvec[:, :, 2], tpkernel[np.newaxis, :], mode='same')
        spsmooth_x = np.dot (spkernel, tpsmooth_x)
        spsmooth_y = np.dot (spkernel, tpsmooth_y)
        spsmooth_z = np.dot (spkernel, tpsmooth_z)  #
        spsmooth_Q = Geometry.qn(np.array([spsmooth_x, spsmooth_y, spsmooth_z]).transpose ([1, 2, 0]))

        tileCen_Q = Geometry.qn (self.sphere_model.tile_center)
        tileOri_Q1 = Geometry.qn (np.real (self.sphere_model.tile_orientation)).normalize[:, None]
        tileOri_Q2 = Geometry.qn (np.imag (self.sphere_model.tile_orientation)).normalize[:, None]
        projected_motmat = Geometry.projection (tileCen_Q[:, None], spsmooth_Q)
        self.motmatFull = Geometry.qdot (tileOri_Q1, projected_motmat) - 1.j * Geometry.qdot (tileOri_Q2, projected_motmat)
        startpoint = Geometry.cen2tri (np.random.rand (np.int (Isize / 3)), np.random.rand (np.int (Isize / 3)), .1)

        self.sphere_model.vertexBuffer['a_texcoord'] = startpoint.reshape([-1, 2])
        self.sphere_program['u_texture']= np.uint8(np.random.randint(0, 2, [100, 100, 1]) * np.array([[[1, 1, 1]]]) * 255)
        self.sphere_program['u_texture'].wrapping = gl.GL_REPEAT

        self.i = 0

    def render(self) :

        ### Update texture coordinates
        tidx = np.mod(self.i,499)
        motmat = np.repeat(self.motmatFull[:,tidx],3,axis = 0)
        self.sphere_model.vertexBuffer['a_texcoord'] += np.array([np.real(motmat), np.imag(motmat)]).T / 80

        ## Call draw of main program
        self.sphere_program.draw (gl.GL_TRIANGLES, self.sphere_model.indexBuffer)
        self.i += 1