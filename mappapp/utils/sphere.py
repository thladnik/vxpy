"""
MappApp ./utils/sphere.py
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

from mappapp.utils import geometry

########
# !!! BE EXTREMELY CAREFUL WHEN EDITING THESE MODELS !!!
# Any changes will affect all visuals associated with the models!
#
########

class UVSphere:

    def __init__(self,
                 azim_lvls: int,
                 elev_lvls: int,
                 azimuth_range: float = 2 * np.pi,
                 upper_elev: float = np.pi / 4,
                 radius: float = 1.0):

        # Set parameters
        self.azim_lvls = azim_lvls
        self.elev_lvls = elev_lvls
        self.azimuth_range = azimuth_range
        self.upper_elev = upper_elev
        self.radius = radius

        # Calculate coordinates in azimuth and elevation
        az = np.linspace(0, self.azimuth_range, self.azim_lvls, endpoint=True)
        el = np.linspace(-np.pi / 2, self.upper_elev, self.elev_lvls, endpoint=True)
        self.azims, self.elevs = np.meshgrid(az, el)

        # Set vertex attributes
        self.a_azimuth = np.ascontiguousarray(self.azims.flatten(), dtype=np.float32)
        self.a_elevation = np.ascontiguousarray(self.elevs.flatten(), dtype=np.float32)
        self.a_position = geometry.SphereHelper.sph2cart(self.a_azimuth,self.a_elevation,self.radius)
        self.a_position = np.ascontiguousarray(self.a_position.T, dtype=np.float32)

        # Set indices
        idcs = list()
        for i in np.arange(self.elev_lvls):
            for j in np.arange(self.azim_lvls):
                idcs.append([i * azim_lvls + j, i * azim_lvls + j + 1, (i + 1) * azim_lvls + j + 1])
                idcs.append([i * azim_lvls + j, (i + 1) * azim_lvls + j, (i + 1) * azim_lvls + j + 1])
        self.indices = np.ascontiguousarray(np.array(idcs).flatten(), dtype=np.uint32)


class IcosahedronSphere:
    """
    !!! DOESN'T WORK CURRENTLY
    TODO: fix Icosphere
    """
    gr = 1.61803398874989484820

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
        return np.array(geometry.SphereHelper.cart2sph(self.a_position[0,:],self.a_position[1,:],self.a_position[2,:]))


class CMNIcoSphere:

    def __init__(self, subdivisionTimes : int = 1):

        ### Create sphere
        self.r = 1#(1 + np.sqrt(5)) / 2
        self.init_vertices = np.array([
                    [-1.0, self.r, 0.0],
                    [1.0, self.r, 0.0],
                    [-1.0, -self.r, 0.0],
                    [1.0, -self.r, 0.0],
                    [0.0, -1.0, self.r],
                    [0.0, 1.0, self.r],
                    [0.0, -1.0, -self.r],
                    [0.0, 1.0, -self.r],
                    [self.r, 0.0, -1.0],
                    [self.r, 0.0, 1.0],
                    [-self.r, 0.0, -1.0],
                    [-self.r, 0.0, 1.0]
                ])
        self.init_faces = np.array([
                    [0, 11, 5],
                    [0, 5, 1],
                    [0, 1, 7],
                    [0, 7, 10],
                    [0, 10, 11],
                    [1, 5, 9],
                    [5, 11, 4],
                    [11, 10, 2],
                    [10, 7, 6],
                    [7, 1, 8],
                    [3, 9, 4],
                    [3, 4, 2],
                    [3, 2, 6],
                    [3, 6, 8],
                    [3, 8, 9],
                    [4, 9, 5],
                    [2, 4, 11],
                    [6, 2, 10],
                    [8, 6, 7],
                    [9, 8, 1]
                ])
        self.sdtimes = subdivisionTimes
        [usV, usF] = geometry.subdivide_triangle(self.init_vertices,self.init_faces,self.sdtimes) # Compute the radius of all the vertices
        sphereR = geometry.vecNorm(usV[0,:])  # Compute the radius of all the vertices
        tileCen = np.mean(usV[usF, :], axis=1)  # Compute the center of each triangle tiles

        # Create index buffer
        Iout = np.arange(usF.size, dtype=np.uint32)
        self.indices = Iout

        # Create vertex buffer
        # The orientation of each triangle tile is defined as the direction perpendicular to the first edge of the triangle;
        # Here each orientation vector is represented by a complex number for the convenience of later computation
        tileOri = geometry.vecNormalize(np.cross(tileCen,usV[usF[:,1],:] - usV[usF[:,0],:])) \
                  + 1.j * geometry.vecNormalize(usV[usF[:,1],:] - usV[usF[:,0],:])
        tileDist = geometry.sphAngle(tileCen,sphereR)  # Spherical distance for each tile pair
        usF = np.uint32(usF.flatten())
        # Triangles must not share edges/vertices while doing texture mapping, this line duplicate the shared vertices for each triangle
        self.a_position = geometry.vecNormalize(usV[usF,:])
        self.a_texcoord = geometry.cen2tri(np.random.rand(np.int(Iout.size / 3)),np.random.rand(np.int(Iout.size / 3)),.1).reshape([Iout.size,2])

        self.tile_orientation = tileOri
        self.tile_center      = tileCen
        self.intertile_distance = tileDist

class Insta360Calibrated:
    """
    !!! DOESN'T WORK CURRENTLY !!!
    """

    def __init__(self, filename):

        self.addAttribute(('a_texcoord', np.float32, 2))

        self.filename = '{}.mat'.format(filename)

        self.file = h5py.File(os.path.join(Path.Model, 'LUTs', self.filename), 'r')
        data = self.file['xyz0'][:]
        self.validIdcs = np.arange(data.shape[0])[np.isfinite(data[:,0])]

        x = (self.validIdcs / 315) / 630
        y = (self.validIdcs % 315) / 315

        self.a_texcoord = np.array([x,y])
        vertices = geometry.vecNormalize(data[self.validIdcs,:])
        vertices = geometry.qn(vertices)

        vertices = geometry.rotate(geometry.qn([1,0,0]),vertices,np.pi / 2)
        #vertices = Geometry.rotate(Geometry.qn([0, 0, 1]), vertices, -np.pi / 4)
        #vertices = Geometry.rotate(Geometry.qn([0, 1, 0]), vertices, np.pi / 2)

        vertices = vertices.matrixform[:,1:]
        self.a_position = vertices

        self.indices = Delaunay(self.a_texcoord.T).simplices


        self.createBuffers()