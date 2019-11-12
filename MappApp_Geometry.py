import numpy as np
from numpy import ndarray
from scipy.spatial import Delaunay
from typing import Union


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

class Sphere:

    def getVertices(self): pass
    def getSphericalCoords(self): pass
    def getFaceIdcs(self): pass

gr = 1.61803398874989484820
class IcosahedronSphere(Sphere):

    corners = [
        [-1, gr, 0],
        [1, gr, 0],
        [-1, -gr, 0],
        [1, -gr, 0],
        [0, -1, gr],
        [0, 1, gr],
        [0, -1, -gr],
        [0, 1, -gr],
        [gr, 0, -1],
        [ gr, 0, 1],
        [-gr, 0, -1],
        [-gr, 0, 1],
    ]

    faces = [

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

    cache = dict()

    def __init__(self, subdiv_lvl):

        # Calculate vertices
        self.vertices = [self.vertex(*v) for v in self.corners]

        # Subdivide faces
        self.subdiv_lvl = subdiv_lvl
        self.subdivide()

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

    def getVertices(self):
        return np.array(self.vertices)

    def getFaces(self):
        return np.array(self.faces)

class UVSphere(Sphere):

    def __init__(self, theta_lvls: int, phi_lvls: int, upper_phi: float = np.pi/4, radius: float = 1.0):
        # Set attributes
        self.theta_lvls = theta_lvls
        self.phi_lvls = phi_lvls
        self.upper_phi = upper_phi
        self.radius = radius

        self._construct()

    def _construct(self):
        # Calculate coordinates in azimuth and elevation
        az = np.linspace(-np.pi, np.pi, self.theta_lvls, endpoint=False)
        el = np.linspace(-np.pi/2, self.upper_phi, self.phi_lvls, endpoint=True)
        self.thetas, self.phis = np.meshgrid(az, el)
        self.thetas = self.thetas.flatten()
        self.phis = self.phis.flatten()

    def getSphericalCoords(self):
        return np.array([self.thetas, self.phis]).T

    def getVertices(self) -> np.ndarray:
        return SphereHelper.sph2cart(self.thetas, self.phis, self.radius).T

    def getFaceIndices(self) -> np.ndarray:

        vertices = self.getVertices()

        # Calculate Delaunay tesselation
        delaunay = Delaunay(vertices)
        if delaunay.simplices.shape[1] > 3:
            faceIdcs = delaunay.convex_hull
        else:
            faceIdcs = delaunay.simplices

        return faceIdcs