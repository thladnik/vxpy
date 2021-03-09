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
from vispy import gloo
import numpy as np

from mappapp.core.visual import PlanarVisual
from mappapp.utils import plane

"""
MappApp ./visuals/planar/calibration.py
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

from mappapp.core.visual import PlanarVisual
from mappapp.utils import plane


class motion_rivalry_1(PlanarVisual):

    u_sf_vertical = 'u_sf_vertical'
    u_sf_horizontal = 'u_sf_horizontal'
    u_checker_pattern = 'u_checker_pattern'
    pat_scale = 'pat_scale'
    mov_speed = 'mov_speed'
    mov_dir   = 'mov_dir'

    parameters = {u_sf_vertical: 0.1,
                  u_sf_horizontal: 0.1,
                  u_checker_pattern: True,
                  pat_scale: 13.,
                  mov_speed: 5.,
                  mov_dir: 0.}
    interface = [
        (pat_scale, 20., 1., 100., dict(step_size=.5)),
        (mov_speed, 5., -20., 20., dict(step_size=.1)),
        (mov_dir, 0, -np.pi, np.pi, dict(step_size=np.pi/180)),
    ]
    def __init__(self, *args, vert_shader=None, **params):
        PlanarVisual.__init__(self, *args)
        # self._utime = 0.
        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mrender = gloo.Program(self.load_vertex_shader('planar/grating.vert'),
                                    self.load_shader('planar/motion_rivalry.frag'))
        self.mrender['a_position'] = self.position_buffer

        self.update(**params)

    def render(self, frame_time):
        # self._utime += frame_time
        self.mrender['u_stime'] = frame_time#time.time() - self.start_time

        myvar = self.parameters[motion_rivalry_1.mov_dir]

        self.apply_transform(self.mrender)
        self.mrender.draw('triangles', self.index_buffer)

class closeloop_grating(PlanarVisual):

    u_sf_vertical = 'u_sf_vertical'
    u_sf_horizontal = 'u_sf_horizontal'
    u_checker_pattern = 'u_checker_pattern'
    u_spfreq = 'u_spfreq'
    u_speed = 'u_speed'
    u_dir   = 'u_dir'

    parameters = {u_sf_vertical: 0.1,
                  u_sf_horizontal: 0.1,
                  u_checker_pattern: True,
                  u_spfreq: 40.,
                  u_speed: 15.,
                  u_dir: 0.}
    interface = [
        (u_spfreq, 40., 1., 100., dict(step_size=.5)),
        (u_speed, 15., -20., 20., dict(step_size=.1)),
        (u_dir, 0, -np.pi, np.pi, dict(step_size=np.pi/180)),
    ]
    def __init__(self, *args, vert_shader=None, **params):
        PlanarVisual.__init__(self, *args)
        # self._utime = 0.
        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mrender = gloo.Program(self.load_vertex_shader('planar/grating.vert'),
                                    self.load_shader('planar/closeloop_grating.frag'))
        self.mrender['a_position'] = self.position_buffer

        self.update(**params)

    def render(self, frame_time):
        # self._utime += frame_time
        self.mrender['u_stime'] = frame_time#time.time() - self.start_time

        self.apply_transform(self.mrender)
        self.mrender.draw('triangles', self.index_buffer)


class closeloop_dotchasing(PlanarVisual):

    u_sf_vertical = 'u_sf_vertical'
    u_sf_horizontal = 'u_sf_horizontal'
    u_checker_pattern = 'u_checker_pattern'
    u_pos = 'u_pos'
    parameters = {u_sf_vertical: 0.1,
                  u_sf_horizontal: 0.1,
                  u_checker_pattern: True,
                  u_pos: (0.,0.)}
    interface = []
    def __init__(self, *args, vert_shader=None, **params):
        PlanarVisual.__init__(self, *args)
        # self._utime = 0.
        self.plane = plane.VerticalXYPlane()
        self.index_buffer = gloo.IndexBuffer(np.ascontiguousarray(self.plane.indices, dtype=np.uint32))
        self.position_buffer = gloo.VertexBuffer(np.ascontiguousarray(self.plane.a_position, dtype=np.float32))

        self.mrender = gloo.Program(self.load_vertex_shader('planar/grating.vert'),
                                    self.load_shader('planar/cl_dotchasing.frag'))
        self.mrender['a_position'] = self.position_buffer

        self.update(**params)

    def render(self, frame_time):
        # self._utime += frame_time


        self.mrender['u_stime'] = frame_time#time.time() - self.start_time

        self.apply_transform(self.mrender)
        self.mrender.draw('triangles', self.index_buffer)