"""
MappApp ./models/BasicSphere.py - Basic sphere models for re-use.
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
########
## !!! BE EXTREMELY CAREFUL WHEN EDITING THESE MODELS !!!
## Any changes will affect all stimuli associated with the models!
####
########

import numpy as np

from helper import Geometry
from Model import SphereModel

################################
# UV Sphere
class UVSphere(SphereModel):

    def __repr__(self):
        return 'UVSphere(theta_lvls={}, phi_lvls={}, theta_range={}, upper_phi={}, radius={})'\
            .format(self.theta_lvls, self.phi_lvls, self.theta_range, self.upper_phi, self.radius)

    def __init__(self, theta_lvls: int, phi_lvls: int,
                 theta_range : float = 2*np.pi, upper_phi: float = np.pi/4,
                 radius: float = 1.0, **kwargs):
        SphereModel.__init__(self, **kwargs)

        ### Add vertex attributes for this particular model
        self.addAttribute(('a_azimuth', np.float32, 1))
        self.addAttribute(('a_elevation', np.float32, 1))

        ### Set parameters
        self.theta_lvls = theta_lvls
        self.phi_lvls = phi_lvls
        self.theta_range = theta_range
        self.upper_phi = upper_phi
        self.radius = radius

        ### Calculate coordinates in azimuth and elevation
        az = np.linspace(0, self.theta_range, self.theta_lvls, endpoint=True)
        el = np.linspace(-np.pi/2, self.upper_phi, self.phi_lvls, endpoint=True)
        self.thetas, self.phis = np.meshgrid(az, el)
        self.thetas = self.thetas.flatten()
        self.phis = self.phis.flatten()

        ### Set vertex attributes
        self.a_azimuth = self.thetas
        self.a_elevation = self.phis
        self.a_position = Geometry.SphereHelper.sph2cart(self.thetas, self.phis, self.radius)

        ### Set indices
        idcs = list()
        for i in np.arange(self.phi_lvls):
            for j in np.arange(self.theta_lvls):
                idcs.append([i * theta_lvls + j, i * theta_lvls + j + 1, (i+1) * theta_lvls + j + 1])
                idcs.append([i * theta_lvls + j, (i+1) * theta_lvls + j, (i+1) * theta_lvls + j + 1])
        self.indices = np.array(idcs).flatten()




################################
# ICO SPHERE
gr = 1.61803398874989484820
class IcosahedronSphere(SphereModel):

    corners = [
        [-1, gr,  0],
        [1,  gr,  0],
        [-1, -gr, 0],
        [1,  -gr, 0],
        [0,  -1,  gr],
        [0,  1,   gr],
        [0,  -1,  -gr],
        [0,  1,   -gr],
        [gr, 0,   -1],
        [gr, 0,   1],
        [-gr, 0,  -1],
        [-gr, 0,  1],
    ]

    _faces = [

        [0, 11, 5],
        [0, 5, 1],
        [0, 1, 7],
        [0, 7, 10],
        [0, 10, 11],

        [3, 9, 4],
        [3, 4, 2],
        [3, 2, 6],
        [3, 6, 8],
        [3, 8, 9],

        [1, 5, 9],
        [5, 11, 4],
        [11, 10, 2],
        [10, 7, 6],
        [7, 1, 8],

        [4, 9, 5],
        [2, 4, 11],
        [6, 2, 10],
        [8, 6, 7],
        [9, 8, 1],
    ]

    def __repr__(self):
        return 'IcosahedronSphere(subdiv_lvl={})'\
            .format(self.subdiv_lvl)

    def __init__(self, subdiv_lvl, **kwargs):
        SphereModel.__init__(self, **kwargs)

        ### Add vertex attributes for this particular model
        self.addAttribute(('a_azimuth', np.float32, 1))
        self.addAttribute(('a_elevation', np.float32, 1))

        self.faces = self._faces
        self.cache = dict()

        ### Calculate initial vertices
        self.vertices = [self.vertex(*v) for v in self.corners]

        ### Subdivide faces
        self.subdiv_lvl = subdiv_lvl
        self.subdivide()

        ### Set vertices
        self.a_position = np.array(self.vertices).T
        self.indices = np.array(self.faces).flatten()

        ### Set spherical coordinates
        self.a_azimuth, self.a_elevation, _ = self.getSphericalCoords()

    def vertex(self, x, y, z):
        vlen = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        return [i/vlen for i in (x, y, z)]

    def midpoint(self, p1, p2):
        key = '%i/%i' % (min(p1, p2), max(p1, p2))

        if key in self.cache:
            return self.cache[key]

        v1 = self.vertices[p1]
        v2 = self.vertices[p2]
        middle = [sum(i)/2 for i in zip(v1, v2)]

        self.vertices.append(self.vertex(*middle))
        index = len(self.vertices) - 1

        self.cache[key] = index

        return index

    def subdivide(self):
        for i in range(self.subdiv_lvl):
            new_faces = []
            for face in self.faces:
                v = [self.midpoint(face[0], face[1]),
                     self.midpoint(face[1], face[2]),
                     self.midpoint(face[2], face[0])]

                new_faces.append([face[0], v[0], v[2]])
                new_faces.append([face[1], v[1], v[0]])
                new_faces.append([face[2], v[2], v[1]])
                new_faces.append([v[0], v[1], v[2]])

            self.faces = new_faces

    def getSphericalCoords(self):
        return np.array(Geometry.SphereHelper.cart2sph(self.a_position[0,:], self.a_position[1,:], self.a_position[2,:]))
