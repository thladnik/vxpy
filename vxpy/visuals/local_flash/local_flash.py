"""
vxpy ./visuals/spherical/grating.py
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
import numpy as np
from vispy import gloo
from vispy import scene

from vxpy.core import visual
from vxpy.utils import sphere


class BrightFlash(visual.SphericalVisual):

    bg_frag = """
    void main() {
        gl_FragColor = vec4(vec3(.2), .2);
    }
    """

    u_dot_diameter = 'u_dot_diameter' # Diameter in deg
    p_dot_locations = 'p_dot_locations'
    u_dot_location = 'u_dot_location'

    interface = [
        # (u_dot_location, [1., 0., 0.], [-1., -1., -1], [1., 1., 1.]),
        (u_dot_diameter, 30., 1., 89., {'step_size': 1.})]

    def __init__(self, *args):
        visual.SphericalVisual.__init__(self, *args)

        # Set up sphere
        self.ico_sphere = sphere.IcosahedronSphere(subdiv_lvl=3)
        self.index_buffer = gloo.IndexBuffer(self.ico_sphere.get_indices())
        self.position_buffer = gloo.VertexBuffer(self.ico_sphere.get_vertices())

        # Set up programs
        vert = self.load_vertex_shader('./bright_flash.vert')
        frag = self.load_shader('./bright_flash.frag')
        # Set background
        self.background = gloo.Program(vert, self.bg_frag)
        self.background['a_position'] = self.position_buffer
        # Set dot
        self.dot = gloo.Program(vert, frag)
        self.dot['a_position'] = self.position_buffer

        dots = np.random.randn(25, 3)
        dots_n = np.apply_along_axis(lambda v: v/np.linalg.norm(v), 1, dots)
        self.parameters[self.p_dot_locations] = dots_n

    def initialize(self, **params):
        self.dot['u_time'] = 0.0

    def render(self, dt):
        self.dot['u_time'] += dt

        dot_locations = self.parameters.get(self.p_dot_locations)
        if dot_locations is None:
            print('AAAAAH')
            return


        # Draw dots
        self.apply_transform(self.dot)
        for dot in dot_locations:
            self.dot[self.u_dot_location] = dot
            self.dot.draw('triangles', self.index_buffer)

        # Draw bg
        self.apply_transform(self.background)
        self.background.draw('triangles', self.index_buffer)
