from glumpy import gloo
import numpy as np
from scipy.spatial import Delaunay

from MappApp_Geometry import SphereHelper

#####
# UV Sphere base Class

class UVSphere:

    def __init__(self, theta_lvls: int, phi_lvls: int, upper_phi: float = np.pi/4, radius: float = 1.0):
        # Set attributes
        self.theta_lvls = theta_lvls
        self.phi_lvls = phi_lvls
        self.upper_phi = upper_phi
        self.radius = radius

        # Construct sphere and prepare for projection
        self._construct()
        self._prepareChannels()

    def _construct(self):
        # Calculate coordinates in azimuth and elevation
        az = np.linspace(-np.pi, np.pi, self.theta_lvls, endpoint=False)
        el = np.linspace(-np.pi/2, self.upper_phi, self.phi_lvls, endpoint=True)
        self.thetas, self.phis = np.meshgrid(az, el)
        self.thetas = self.thetas.flatten()
        self.phis = self.phis.flatten()

    def _prepareChannels(self):
        """
        This method separates the sphere into 4 different channels, according to their azimuth.
        This step is crucial for the actual projection and MappApp requires each vertex to be assigned
        a channel ID between 1 nad 4 (1: SW, 2: SE, 3: NE, 4: NW). Vertices that do NOT have a channel ID
        will be disregarded during rendering.

        """

        all_verts = self.getVertices()
        all_sph_pos = self.getSphericalCoords()

        orientations = ['sw', 'se', 'ne', 'nw']
        verts = dict()
        faces = dict()
        sph_pos = dict()
        channel = dict()
        for i, orient in enumerate(orientations):
            theta_center = -3 * np.pi / 4 + i * np.pi / 2
            vert_mask = SphereHelper.getAzElLimitedMask(theta_center - np.pi / 4, theta_center + np.pi / 4,
                                                        -np.inf, np.inf, all_verts)

            verts[orient] = all_verts[vert_mask]
            sph_pos[orient] = all_sph_pos[vert_mask]
            channel[orient] = (i + 1) * np.ones((verts[orient].shape[0], 2))
            faces[orient] = Delaunay(verts[orient]).convex_hull

        ## CREATE BUFFERS
        v = np.concatenate([verts[orient] for orient in orientations], axis=0)
        # Vertex buffer
        self.vertexBuffer = np.zeros(v.shape[0],
                                     [('a_cart_pos', np.float32, 3),
                             ('a_sph_pos', np.float32, 2),
                             ('a_channel', np.float32, 2)])
        self.vertexBuffer['a_cart_pos'] = v.astype(np.float32)
        self.vertexBuffer['a_sph_pos'] = np.concatenate([sph_pos[orient] for orient in orientations], axis=0).astype(np.float32)
        self.vertexBuffer['a_channel'] = np.concatenate([channel[orient] for orient in orientations], axis=0).astype(np.float32)
        self.vertexBuffer = self.vertexBuffer.view(gloo.VertexBuffer)
        # Index buffer
        self.indexBuffer = np.zeros((0, 3))
        startidx = 0
        for orient in orientations:
            self.indexBuffer = np.concatenate([self.indexBuffer, startidx + faces[orient]], axis=0)
            startidx += verts[orient].shape[0]
        self.indexBuffer = self.indexBuffer.astype(np.uint32).view(gloo.IndexBuffer)

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

#####
# UV Sphere subclasses

class UVSphere_80thetas_40phis(UVSphere):

    def __init__(self):
        super().__init__(theta_lvls=80, phi_lvls=40)