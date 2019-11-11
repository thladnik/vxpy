import numpy as np
from numpy import ndarray
from scipy.spatial import Delaunay
from typing import Union

class SphericalArena:


    def __init__(self, theta_lvls: int, phi_lvls: int, upper_phi: float = 40.0, radius: float = 1.0):

        # Set attributes
        self.theta_lvls = theta_lvls
        self.phi_lvls = phi_lvls
        self.upper_phi = upper_phi
        self.radius = radius

        self._construct()

    def _construct(self):
        # Set parameters
        self.d_azim = 360.0/self.theta_lvls
        self.d_elev = (90.0 - self.upper_phi) / self.phi_lvls

        # Calculate coordinates in azimuth and elevation
        az = np.linspace(0.0, 360.0, self.theta_lvls, endpoint=False)
        el = np.linspace(-84.9, self.upper_phi, self.phi_lvls, endpoint=True)
        self.thetas, self.phis = np.meshgrid(az, el)
        self.thetas = self.thetas.flatten()
        self.phis = self.phis.flatten()

    def sph2cart(self, theta: Union[float, np.ndarray], phi: Union[float, np.ndarray]) -> np.ndarray:
        """ Calculate cartesian coordinates on unit sphere
        for given combination of azimuth and elevation

        :param theta: azimuth in degree
        :param phi: elevation in degree
        :return: x,y,z coordinates on a unit sphere in cartesian space
        """

        # Convert to radians
        phi = (phi + 90.0) / 360 * 2 * np.pi
        theta = theta / 360 * 2 * np.pi

        # Return cartesian coordinates
        return np.asarray([
            self.radius * np.sin(phi) * np.cos(theta),  # x
            self.radius * np.sin(phi) * np.sin(theta),  # y
            self.radius * -np.cos(phi)  # z
        ]).T


    def mercator2DTexture(self, theta: Union[float, ndarray], phis: Union[float, ndarray]):

        x = theta/360
        latrad = phis*np.pi/180
        mercn = np.log(np.tan((np.pi/4) + (latrad/2)))
        y = 0.5 - mercn/(2*np.pi)

        return np.asarray([x, y])

    def ortho2DTexture(self, verts):

        w = verts[:,0]

        x = verts[:,1]
        y = verts[:,2]

        # Normalize x
        x[w >= 0.5] /= x[w >= 0.5].max() - x[w >= 0.5].min()
        x[w >= 0.5] /= 2

        x[w < 0.5] /= x[w < 0.5].max() - x[w < 0.5].min()
        x[w < 0.5] /= 2
        x[w < 0.5] += 0.5

        # Normalize y
        y /= y.max() - y.min()
        y -= y.min()


        return np.array([x, y])

    def getThetaSubset(self, theta_low: float, theta_high: float, return_bool: bool = False) -> tuple:
        """Returns the vertices which have an theta (azimuth) in between
        a lower and an upper boundary.

        :param theta_low: lower azimuth boundary in degree
        :param theta_high: upper azimuth boundary in degree
        :return:
        """

        # Check boundaries
        if theta_low > theta_high:
            Exception('Higher azimuth has to exceed lower azimuth.')

        # Adjust boundaries which exceed [0.0, 360.0]
        while theta_low < 0.0:
            theta_low += 360.0
        while theta_high > 360.0:
            theta_high -= 360.0

        # Filter theta
        bools = None
        if theta_high > theta_low:
            bools = (self.thetas >= theta_low) & (self.thetas <= theta_high)
        elif theta_high < theta_low:
            bools = (self.thetas >= theta_low) | (self.thetas <= theta_high)
        else:
            Exception('Higher azimuth has to exceed lower azimuth.')

        if return_bool:
            return bools

        return self.thetas[bools], self.phis[bools]


    def getFaceIndices(self, vertices: ndarray = None) -> ndarray:

        if vertices is None:
            vertices = self.vertices

        # Calculate Delaunay tesselation
        delaunay = Delaunay(vertices)
        if delaunay.simplices.shape[1] > 3:
            faceIdcs = delaunay.convex_hull
        else:
            faceIdcs = delaunay.simplices

        return faceIdcs