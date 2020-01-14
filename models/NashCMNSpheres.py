from glumpy import gloo
import numpy as np
from helper import NashHelper
import Model


class UVSphere(Model.SphereModel):
    def __init__(self, azi, elv, r, azitile : int = 30, elvtile : int = 30, **kwargs):
        Model.SphereModel.__init__ (self, **kwargs)

        ## Set parameters
        self.azi = azi
        self.elv = elv
        self.r   = r
        self.azitile = azitile
        self.elvtile = elvtile

        sphV, sphI = NashHelper.createUVSphere(self.azi, self.elv, self.azitile, self.elvtile)

        ### Set position shader attribute (for vertex buffer)
        self.a_position = sphV * np.mean(self.r)


        ### Create the vertex buffer and initialize with current values
        self.createVertexBuffer()

        ### Set index buffer
        mask_I = sphI.astype(np.uint32)
        self.indexBuffer = mask_I.view(gloo.IndexBuffer)


class IcoSphere(Model.SphereModel):

    def __init__(self, subdivisionTimes : int = 1, **kwargs):
        Model.SphereModel.__init__ (self, **kwargs)

        ### Add a_texcoord to the list of shader attributes
        self.addVertexAttribute(('a_texcoord', np.float32, 2))

        ### Create sphere
        self.r = (1 + np.sqrt(5)) / 2
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
        [usV, usF] = NashHelper.subdivide_triangle(self.init_vertices, self.init_faces, self.sdtimes) # Compute the radius of all the vertices
        sphereR = NashHelper.vecNorm(usV[0, :])  # Compute the radius of all the vertices
        tileCen = np.mean(usV[usF, :], axis=1)  # Compute the center of each triangle tiles

        ### Create index buffer
        Iout = np.arange(usF.size, dtype=np.uint32)
        self.indexBuffer = Iout.view(gloo.IndexBuffer)

        ### Create vertex buffer
        # The orientation of each triangle tile is defined as the direction perpendicular to the first edge of the triangle;
        # Here each orientation vector is represented by a complex number for the convenience of later computation
        tileOri = NashHelper.vecNormalize(np.cross(tileCen, usV[usF[:, 1], :] - usV[usF[:, 0], :])) \
                  + 1.j * NashHelper.vecNormalize(usV[usF[:, 1], :] - usV[usF[:, 0], :])
        tileDist = NashHelper.sphAngle(tileCen, sphereR)  # Spherical distance for each tile pair
        usF = np.uint32(usF.flatten())
        # Triangles must not share edges/vertices while doing texture mapping, this line duplicate the shared vertices for each triangle
        self.a_position = usV[usF,:]
        self.a_texcoord = NashHelper.cen2tri(np.random.rand(np.int(Iout.size / 3)), np.random.rand(np.int(Iout.size / 3)), .1).reshape([Iout.size,2])

        self.createVertexBuffer()

        self.tile_orientation = tileOri
        self.tile_center      = tileCen
        self.intertile_distance = tileDist


#####
# icoSphere subclasses

class diviable_icosphere_sd1(IcoSphere):

    def __init__(self):
        super().__init__(subdivisionTimes=1)