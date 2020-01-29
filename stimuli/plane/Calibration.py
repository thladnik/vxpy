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

from Stimulus import PlaneStimulus
from models import BasicPlane
from Shader import BasicFileShader


class Checkerboard(PlaneStimulus):

    def __init__(self, protcol, display):
        PlaneStimulus.__init__(self, display=display, protocol=protcol)

        self.plane = self.addModel('plane',
                                   BasicPlane.VerticalXYPlane)
        self.plane.createBuffers()

        self.checker = self.addProgram('checker',
                                       BasicFileShader().addShaderFile('checker_v.glsl', subdir='plane').read(),
                                       BasicFileShader().addShaderFile('checker_f.glsl', subdir='plane').read())
        self.checker.bind(self.plane.vertexBuffer)


    def render(self, dt):
        self.checker.draw(gl.GL_TRIANGLES, self.plane.indexBuffer)