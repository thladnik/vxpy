"""
vxpy ./visuals/planar/blank.py
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
from vispy import gloo
import numpy as np

from vxpy.core import visual
from vxpy.utils import plane


class Clear(visual.PlanarVisual):
    description = 'A blank screen of arbitrary uniform color.'

    p_color = 'p_color'

    parameters = {p_color: None}

    def __init__(self, *args, **params):
        visual.PlanarVisual.__init__(self, *args)

        self.plane = plane.XYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        gloo.clear(self.parameters[self.p_color])


class Blank(visual.PlanarVisual):
    description = 'A blank screen of arbitrary uniform color.'

    _vert = """
    attribute vec3 a_position;

    varying vec2 v_position;
    varying vec2 v_nposition;
    
    void main() {
        gl_Position = transform_position(a_position);
        v_position = real_position(a_position);
        v_nposition = norm_position(a_position);
    }
    """

    _frag = """
    //uniform vec3 u_color;
            
    void main() {
        gl_FragColor = vec4(vec3(1.0), 1.0);
    }

    """

    u_color = 'p_color'

    parameters = {u_color: None}

    def __init__(self, *args, **params):
        visual.PlanarVisual.__init__(self, *args)

        self.plane = plane.XYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))
        self.blank = gloo.Program(self.parse_vertex_shader(self._vert),
                                  self._frag)
        self.blank['a_position'] = self.position_buffer

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        self.apply_transform(self.blank)
        self.blank.draw('triangles', self.index_buffer)


class ClearBlack(visual.PlanarVisual):
    description = 'A blank screen of arbitrary uniform color.'

    def __init__(self, *args, **params):
        visual.PlanarVisual.__init__(self, *args)

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        gloo.clear(0., 0., 0.)

class Noise(visual.PlanarVisual):
    description = 'A blank screen of arbitrary uniform color.'

    _vert = """
    attribute vec3 a_position;

    varying vec2 v_position;
    varying vec2 v_nposition;

    void main() {
        gl_Position = transform_position(a_position);
        v_position = real_position(a_position);
        v_nposition = norm_position(a_position);
    }
    """

    _frag = """
    uniform sampler2D u_bg;
    varying vec2 v_nposition;

    void main() {
        gl_FragColor = texture2D(u_bg,v_nposition);
    }

    """

    u_color = 'p_color'

    parameters = {u_color: None}

    def __init__(self, *args, **params):
        visual.PlanarVisual.__init__(self, *args)

        self.plane = plane.XYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))
        self.blank = gloo.Program(self.parse_vertex_shader(self._vert),
                                  self._frag)
        self.blank['a_position'] = self.position_buffer
        np.random.seed(23)
        self.blank['u_bg'] = np.random.rand(100, 100).astype(np.float32)


    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        self.apply_transform(self.blank)
        self.blank.draw('triangles', self.index_buffer)
