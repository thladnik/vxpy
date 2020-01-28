"""
MappApp ./stimuli/Checkerboard.py - Checkerboard stimuli
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
import numpy as np

from Stimulus import SphericalStimulus
from models import BasicSphere
from Shader import BasicFileShader

class BlackWhiteCheckerboard(SphericalStimulus):

    def __init__(self, protocol, display, rows, cols):
        """Black-and-white checkerboard for calibration.

        :param protocol: protocol of which stimulus is currently part of
        :param rows: number of rows on checkerboard
        :param cols: number of columns on checkerboard
        """
        SphericalStimulus.__init__(self, protocol, display)

        self.sphere = self.addModel('sphere',
                                    BasicSphere.UVSphere,
                                    theta_lvls=100, phi_lvls=50, theta_range=2*np.pi, upper_phi=np.pi/2)
        self.sphere.createBuffers()
        self.checker = self.addProgram('sphere',
                                       BasicFileShader().addShaderFile('v_checkerboard.glsl', subdir='spherical').read(),
                                       BasicFileShader().addShaderFile('f_checkerboard.glsl', subdir='spherical').read())
        self.checker.bind(self.sphere.vertexBuffer)

        self.update(cols=cols, rows=rows)

    def render(self, dt):
        self.checker.draw(gl.GL_TRIANGLES, self.sphere.indexBuffer)

    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.setUniform('u_checker_cols', cols)

        if rows is not None and rows > 0:
            self.setUniform('u_checker_rows', rows)
