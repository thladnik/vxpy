"""
MappApp ./Geometry.py - Helper class for geometric operations.
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

class SphereHelper:

    @staticmethod
    def getAzElLimitedMask(theta_low, theta_high, phi_low, phi_high, verts=None, theta=None, phi=None):
        if verts is not None:
            theta, phi, _ = SphereHelper.cart2sph(verts[:, 0], verts[:, 1], verts[:, 2])
        else:
            if theta is None or phi is None:
                raise Exception('If <verts> is undefined, function requires <theta> and <phi> to be specified')

        mask = np.zeros(verts.shape[0]).astype(bool)
        mask[(theta_low <= theta) & (theta <= theta_high)
             & (phi_low <= phi) & (phi <= phi_high)] = True

        return mask

    @staticmethod
    def cart2sph(x, y, z):
        hxy = np.hypot(x, y)
        r = np.hypot(hxy, z)
        el = np.arctan2(z, hxy)
        az = np.arctan2(y, x)
        return az, el, r

    @staticmethod
    def sph2cart(theta, phi, r):
        rcos_theta = r * np.cos(phi)
        x = rcos_theta * np.cos(theta)
        y = rcos_theta * np.sin(theta)
        z = r * np.sin(phi)
        return np.array([x, y, z])

