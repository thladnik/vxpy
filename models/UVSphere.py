"""
MappApp ./models/UVSphere.py - Sphere based on a UV azimuth-elevation map.
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

from glumpy import gloo
import numpy as np
from scipy.spatial import Delaunay

from helper import Geometry
import Model

#####
# UV Sphere base Class
class UVSphere(Model.SphereModel):

    def __repr__(self):
        return 'UVSphere(theta_lvls={}, phi_lvls={}, upper_phi={}, radius={})'\
            .format(self.theta_lvls, self.phi_lvls, self.upper_phi, self.radius)

    def __init__(self, theta_lvls: int, phi_lvls: int,
                 theta_range : float = 2 * np.pi, upper_phi: float = np.pi/4, radius: float = 1.0, **kwargs):
        Model.SphereModel.__init__(self, **kwargs)

        ### Add vertex attributes for this particular model
        self.addVertexAttribute(('a_azimuth', np.float32, 1))
        self.addVertexAttribute(('a_elevation', np.float32, 1))

        ### Set parameters
        self.theta_lvls = theta_lvls
        self.phi_lvls = phi_lvls
        self.upper_phi = upper_phi
        self.radius = radius

        ### Calculate coordinates in azimuth and elevation
        az = np.linspace(0, theta_range, self.theta_lvls, endpoint=True)
        el = np.linspace(-np.pi/2, self.upper_phi, self.phi_lvls, endpoint=True)
        self.thetas, self.phis = np.meshgrid(az, el)
        self.thetas = self.thetas.flatten()
        self.phis = self.phis.flatten()

        ### Set vertex attributes
        self.a_azimuth = self.thetas
        self.a_elevation = self.phis
        self.a_position = Geometry.SphereHelper.sph2cart(self.thetas, self.phis, self.radius)

        ### Set indices
        if False:
            # Calculate Delaunay tesselation
            delaunay = Delaunay(self.a_position.T)
            if delaunay.simplices.shape[1] > 3:
                faceIdcs = delaunay.convex_hull
            else:
                faceIdcs = delaunay.simplices
                self.indices = faceIdcs
        else:
            self.indices = (np.array(
                [np.arange(self.theta_lvls) + 1, np.arange(self.theta_lvls), np.arange(self.theta_lvls + 1, self.theta_lvls * 2 + 1, 1),
                 np.arange(self.theta_lvls + 1, self.theta_lvls * 2 + 1, 1) + 1, np.arange(self.theta_lvls + 1, self.theta_lvls * 2 + 1, 1),
                 np.arange(self.theta_lvls) + 1]).T.flatten()
                            + np.array([np.arange(0, self.phi_lvls + 1, 1)]).T * (self.theta_lvls + 1)).flatten().astype(np.uint32)

        ### Create buffers
        self.createBuffers()

        import IPython
        #IPython.embed()

