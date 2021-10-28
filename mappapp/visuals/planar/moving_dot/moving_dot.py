"""
MappApp ./visuals/planar/grating.py
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
from __future__ import annotations
from vispy import gloo
import numpy as np

from mappapp import Config
from mappapp import Def
from mappapp.core import visual
from mappapp.utils import plane


class SingleMovingDot(visual.PlanarVisual):
    description = ''

    u_dot_lateral_offset = 'u_dot_lateral_offset'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_time = 'u_time'  # s

    parameters = {
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mov_dot = gloo.Program(self.load_vertex_shader('./single_moving_dot.vert'),
                                    self.load_shader('./single_moving_dot.frag'))
        self.mov_dot['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        # gloo.set_clear_color('white')
        self.mov_dot['u_time'] = 0.

    def render(self, dt):
        self.mov_dot['u_time'] += dt

        self.apply_transform(self.mov_dot)
        self.mov_dot.draw('triangles', self.index_buffer)

    interface = [
        (u_dot_lateral_offset, 10.0, -100.0, 100.0, dict(step_size=1.0)),
        (u_dot_ang_dia, 20.0, 1.0, 50.0, dict(step_size=1.0)),
        (u_dot_ang_velocity, 10.0, -200.0, 200.0, dict(step_size=1.0)),
        (u_vertical_offset, 20., 0.0, 50., dict(step_size=1.0)),
        ('Start trigger', initialize)
    ]

class SingleMoving2ndDot(visual.PlanarVisual):
    description = ''

    u_dot_lateral_offset = 'u_dot_lateral_offset'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_time = 'u_time'  # s

    parameters = {
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mov_dot = gloo.Program(self.load_vertex_shader('./single_moving_dot.vert'),
                                    self.load_shader('./single_moving_2nd_dot.frag'))
        self.mov_dot['a_position'] = self.position_buffer
        np.random.seed(23)
        self.mov_dot['u_background'] = np.random.rand(100, 100).astype(np.float32)
        self.mov_dot['u_foreground'] = np.random.rand(100,100).astype(np.float32)


    def initialize(self, **parameters):
        # gloo.set_clear_color('white')
        self.mov_dot['u_time'] = 0.

    def render(self, dt):
        self.mov_dot['u_time'] += dt

        self.apply_transform(self.mov_dot)
        self.mov_dot.draw('triangles', self.index_buffer)

    interface = [
        (u_dot_lateral_offset, 10.0, -100.0, 100.0, dict(step_size=1.0)),
        (u_dot_ang_dia, 20.0, 1.0, 50.0, dict(step_size=1.0)),
        (u_dot_ang_velocity, 10.0, -200.0, 200.0, dict(step_size=1.0)),
        (u_vertical_offset, 20., 0.0, 50., dict(step_size=1.0)),
        ('Start trigger', initialize)
    ]

class MultipleMovingDots(visual.PlanarVisual):
    description = ''

    _bgfrag = """
    void main() {
        gl_FragColor = vec4(vec3(1.0), 1.0);
    }
    """

    u_dot_lateral_offset = 'u_dot_lateral_offset'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_time = 'u_time'  # s

    parameters = {
        u_dot_lateral_offset: 10.0,
        u_dot_ang_dia: 20.,
        u_dot_ang_velocity: 80.,
        u_vertical_offset: 20.,
        u_time: 0.,
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        # Universal vert
        _vert = self.load_vertex_shader('./single_moving_dot.vert')

        # Background
        self.background = gloo.Program(_vert, self._bgfrag)
        self.background['a_position'] = self.position_buffer

        # Dot
        self.mov_dot = gloo.Program(_vert, self.load_shader('moving_dot_dir_startpos.frag'))
        self.mov_dot['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        self.mov_dot['u_time'] = 0.

    def render(self, dt):
        self.mov_dot['u_time'] += dt

        # Draw background
        self.apply_transform(self.background)
        self.background.draw('triangles', self.index_buffer)

        # Apply default transforms
        self.apply_transform(self.mov_dot)

        # Draw dots
        self.mov_dot['u_dot_lateral_offset'] = 5.
        self.mov_dot.draw('triangles', self.index_buffer)

        self.mov_dot['u_dot_lateral_offset'] = 10.
        self.mov_dot.draw('triangles', self.index_buffer)

        self.mov_dot['u_dot_lateral_offset'] = 15.
        self.mov_dot.draw('triangles', self.index_buffer)

        self.mov_dot['u_dot_lateral_offset'] = 20.
        self.mov_dot.draw('triangles', self.index_buffer)


class RandomMovingDots(visual.PlanarVisual):
    description = ''

    _bgfrag = """
    void main() {
        gl_FragColor = vec4(vec3(1.0), 1.0);
    }
    """

    p_dot_count = 'p_dot_count'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_mov_direction = 'u_mov_direction'  # norm
    u_time = 'u_time'  # s

    parameters = {
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        # Universal vert
        _vert = self.load_vertex_shader('./single_moving_dot.vert')

        # Background
        self.background = gloo.Program(_vert, self._bgfrag)
        self.background['a_position'] = self.position_buffer

        # Dot
        self.mov_dot = gloo.Program(_vert, self.load_shader('./moving_dot_dir_startpos.frag'))
        self.mov_dot['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        self.mov_dot['u_time'] = 0.

        # Get dims
        xextent = Config.Display[Def.DisplayCfg.pla_xextent]
        yextent = Config.Display[Def.DisplayCfg.pla_yextent]
        mm = Config.Display[Def.DisplayCfg.pla_small_side]

        self.dots = {}
        for i in range(self.parameters[self.p_dot_count]):
            self.dots[i] = {}
            direction = np.random.rand(2) - .5
            self.dots[i]['mov_direction'] = direction / np.linalg.norm(direction)
            start_pos = (np.random.rand(2) - .5) * np.array([xextent, yextent]) * mm
            self.dots[i]['start_position'] = start_pos

    def render(self, dt):
        self.mov_dot['u_time'] += dt

        # Draw background
        self.apply_transform(self.background)
        self.background.draw('triangles', self.index_buffer)

        # Apply default transforms
        self.apply_transform(self.mov_dot)

        # Draw dots
        for dot in self.dots.values():
            self.mov_dot['u_mov_direction'] = dot['mov_direction']
            self.mov_dot['u_start_position'] = dot['start_position']
            self.mov_dot.draw('triangles', self.index_buffer)

    interface = [
        (p_dot_count, 5, 1, 20, dict(step_size=1)),
        (u_dot_ang_dia, 10.0, 1.0, 50.0, dict(step_size=1.0)),
        (u_dot_ang_velocity, 40.0, 1.0, 200.0, dict(step_size=1.0)),
        (u_vertical_offset, 10., 0.0, 50., dict(step_size=1.0)),
        ('Start trigger', initialize)
    ]


class MultipleMovingDotsInGrid(visual.PlanarVisual):
    description = ''

    _bgfrag = """
    void main() {
        gl_FragColor = vec4(vec3(1.0), 1.0);
    }
    """

    p_dot_count = 'p_dot_count'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_mov_direction = 'u_mov_direction'  # norm
    u_time = 'u_time'  # s

    parameters = {
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        # Universal vert
        _vert = self.load_vertex_shader('./single_moving_dot.vert')

        # Dot
        self.mov_dot = gloo.Program(_vert, self.load_shader('./moving_dots_in_grid.frag'))
        self.mov_dot['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        self.mov_dot['u_time'] = 0.

    def render(self, dt):
        self.mov_dot['u_time'] += dt

        # Draw background
        self.apply_transform(self.mov_dot)
        self.mov_dot.draw('triangles', self.index_buffer)

    interface = [
        ('Start trigger', initialize)
    ]

class SingleMovingDotYZ(visual.PlanarVisual):
    description = ''

    u_x_offset = 'u_x_offset'  # mm
    u_y_offset = 'u_y_offset'  # deg
    u_dot_lateral_offset = 'u_dot_lateral_offset'  # mm
    u_dot_ang_dia = 'u_dot_ang_dia'  # deg
    u_dot_ang_velocity = 'u_dot_ang_velocity'  # deg / s
    u_vertical_offset = 'u_vertical_offset'  # mm
    u_time = 'u_time'  # s

    parameters = {
        u_x_offset: 10.0,
        u_y_offset: 20.,
        u_dot_lateral_offset: 10.0,
        u_dot_ang_dia: 20.,
        u_dot_ang_velocity: 80.,
        u_vertical_offset: 20.,
        u_time: 0.,
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mov_dot = gloo.Program(self.load_vertex_shader('./single_moving_dot.vert'),
                                    self.load_shader('./single_moving_dot_YZ.frag'))
        self.mov_dot['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        self.mov_dot['u_time'] = 0.

    def render(self, dt):
        self.mov_dot['u_time'] += dt
        self.apply_transform(self.mov_dot)
        self.mov_dot.draw('triangles', self.index_buffer)

    interface = [
        (u_x_offset, 0., -1.0, 1.0, dict(step_size=0.001,decimals=4)),
        (u_y_offset, 0., -1.0, 1.0, dict(step_size=0.001,decimals=4)),
        (u_dot_lateral_offset, 0.1, -1., 1.0, dict(step_size=.001,decimals=3)),
        (u_dot_ang_dia, 20.0, 1.0, 50.0, dict(step_size=1.0)),
        (u_dot_ang_velocity, 80.0, 1.0, 200.0, dict(step_size=1.0)),
        (u_vertical_offset, 20., 1.0, 50., dict(step_size=1.0)),
        ('Start trigger', initialize)
    ]


class Crosshair(visual.PlanarVisual):
    description = ''

    u_x_offset = 'u_x_offset'  # mm
    u_y_offset = 'u_y_offset'  # deg
    u_linewidth = 'u_linewidth'  # deg

    parameters = {
        u_x_offset: 10.0,
        u_y_offset: 20.,
        u_linewidth: .1,
    }

    def __init__(self, *args, **kwargs):
        visual.PlanarVisual.__init__(self, *args, **kwargs)

        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.crosshair = gloo.Program(self.load_vertex_shader('./single_moving_dot.vert'),
                                      self.load_shader('./crosshair.frag'))
        self.crosshair['a_position'] = self.position_buffer

    def initialize(self, **parameters):
        self.crosshair['u_time'] = 0.

    def render(self, dt):
        self.apply_transform(self.crosshair)
        self.crosshair.draw('triangles', self.index_buffer)

    interface = [
        (u_x_offset, 0., -1.0, 1.0, dict(step_size=0.001,decimals=4)),
        (u_y_offset, 0., -1.0, 1.0, dict(step_size=0.001,decimals=4)),
        (u_linewidth, 0.01, 0., 0.1, dict(step_size=0.001,decimals=4)),
    ]