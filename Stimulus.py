"""
MappApp ./Stimulus.py - Base stimulus class which is inherited by
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

from glumpy import gl, gloo, transforms
import numpy as np

import Shader
import Model

class AbstractStimulus:

    _texture : np.ndarray = None
    program  : gloo.Program = None

    ########
    # Texture property
    @property
    def texture(self):
        return self._texture
    @texture.setter
    def texture(self, tex):
        self.program['u_texture'] = tex
        self._texture = tex


class SphericalStimulus(AbstractStimulus):
    _base_vertex_shader   : str = '_v_base.shader'
    _vertex_shader        : str = 'v_default.shader'

    _base_fragment_shader : str = '_f_base.shader'
    _fragment_shader      : str = None

    _model : Model.AbstractModel = None

    def __init__(self, protocol, display):
        self.protocol = protocol
        self.display = display

        ### Set start time
        self.time = 0.0

    def _createProgram(self):
        ### Create program
        self.program = gloo.Program(self.getVertexShader(), fragment=self.getFragmentShader())

        ### Set and attach viewport
        self.program['viewport'] = transforms.Viewport()
        self.display._glWindow.attach(self.program['viewport'])

        ### Bind vertex buffer of model to program
        self.program.bind(self._model.vertexBuffer)

    def getVertexShader(self):
        return Shader.Shader(self._base_vertex_shader, self._vertex_shader).getString()

    def getFragmentShader(self):
        return Shader.Shader(self._base_fragment_shader, self._fragment_shader).getString()

    def draw_update(self):
        """Method can be re-implemented to periodically update uniforms.
        """
        pass

    def draw(self, dt):
        """
        METHOD CAN BE RE-IMPLEMENTED.

        By default this method uses the indexBuffer object to draw GL_TRIANGLES.

        :param dt: time since last call
        :return:
        """
        self.time += dt
        self.program['u_time'] = self.time

        self.draw_update()

        ### GL commands
        self.display._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))
        gl.glEnable(gl.GL_DEPTH_TEST)

        ### Draw
        self.program.draw(gl.GL_TRIANGLES, self._model.indexBuffer)

    def update(self, **kwargs):
        """
        Method that is called by default to update stimulus parameters.

        Has to be re-implemented in child class if stimulus contains
        uniforms which can be manipulated externally.
        """
        NotImplementedError('update method not implemented for in {}'.format(self.__class__.__name__))

