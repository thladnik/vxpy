from glumpy import gloo
import numpy as np
from helper.nash_helper import *
import Model
class mask_UVsphere(Model.SphereModel):
    def __init__(self,azi,elv,r,azitile:int = 30,elvtile:int = 30):
        Model.SphereModel.__init__ (self)
        self.azi = azi
        self.elv = elv
        self.r   = r
        self.azitile = azitile
        self.elvtile = elvtile

    def _construct(self) :
        sphV, sphI = UVsphere (self.azi, self.elv, self.azitile, self.elvtile)
        mask_V = np.zeros (sphV.shape[0], [("position", np.float32, 3)])
        mask_V["position"] = sphV * np.mean (self.r)
        self.vertexBuffer = mask_V.view (gloo.VertexBuffer)
        mask_I = sphI.astype (np.uint32)
        self.indexBuffer = mask_I.view (gloo.IndexBuffer)

    def _prepareChannels(self) :
        pass


class diviable_icosphere(Model.SphereModel):

    def __init__(self, subdivisionTimes:int =1):
        # Set attributes
        Model.SphereModel.__init__ (self)
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

        # Construct sphere and prepare for projection
        # self._construct()

    def _construct(self):
        [usV, usF] = subdivide_triangle(self.init_vertices, self.init_faces, self.sdtimes) # Compute the radius of all the vertices
        sphereR = vecNorm(usV[0, :])  # Compute the radius of all the vertices
        tileCen = np.mean(usV[usF, :], axis=1)  # Compute the center of each triangle tiles

        # The orientation of each triangle tile is defined as the direction perpendicular to the first edge of the triangle;
        # Here each orientation vector is represented by a complex number for the convenience of later computation
        tileOri = vecNormalize(np.cross(tileCen, usV[usF[:, 1], :] - usV[usF[:, 0], :])) \
                  + 1.j * vecNormalize(usV[usF[:, 1], :] - usV[usF[:, 0], :])
        tileDist = sphAngle(tileCen, sphereR)  # Spherical distance for each tile pair

        usF = np.uint32(usF.flatten())
        vtype = [('position', np.float32, 3), ('texcoord', np.float32, 2)]  # Data type for the vertex buffer
        Vout = np.zeros(len(usF), vtype)  # Create the vertex array for vertex buffer
        Vout['position'] = usV[usF,:]  # Triangles must not share edges/vertices while doing texture mapping, this line duplicate the shared vertices for each triangle
        Iout = np.arange(usF.size, dtype=np.uint32)  # Construct the face indices array
        Vout['texcoord'] = cen2tri(np.random.rand(np.int(Iout.size / 3)), np.random.rand(np.int(Iout.size / 3)), .1).reshape([Iout.size,2])

        self.tile_orientation = tileOri
        self.tile_center      = tileCen
        self.intertile_distance = tileDist
        self.vertexBuffer = Vout.view(gloo.VertexBuffer)
        self.indexBuffer  = Iout.view(gloo.IndexBuffer)

    def _prepareChannels(self):
        pass

#####
# icoSphere subclasses

class diviable_icosphere_sd1(diviable_icosphere):

    def __init__(self):
        super().__init__(subdivisionTimes=1)