import h5py
import numpy as np
import os
from scipy.spatial import Delaunay

import Model
from Definition import Path
from helper import Geometry

#####
# UV Sphere base Class
class Calibrated(Model.SphereModel):

    def __repr__(self):
        return 'Calibrated()'\
            .format()

    def __init__(self, filename, **kwargs):
        Model.SphereModel.__init__(self, **kwargs)

        self.addVertexAttribute(('a_texcoord', np.float32, 2))

        self.filename = '{}.mat'.format(filename)

        self.file = h5py.File(os.path.join(Path.Model, 'LUTs', self.filename), 'r')
        data = self.file['xyz0'][:]
        self.validIdcs = np.arange(data.shape[0])[np.isfinite(data[:,0])]

        x = (self.validIdcs / 315) / 630
        y = (self.validIdcs % 315) / 315

        self.a_texcoord = np.array([x,y])
        vertices = Geometry.vecNormalize(data[self.validIdcs,:])
        vertices = Geometry.qn(vertices)

        vertices = Geometry.rotate(Geometry.qn([1, 0, 0]), vertices, np.pi / 2)
        #vertices = Geometry.rotate(Geometry.qn([0, 1, 0]), vertices, -np.pi / 2)
        #vertices = Geometry.rotate(Geometry.qn([0, 1, 0]), vertices, np.pi / 2)

        vertices = vertices.matrixform[:,1:]
        self.a_position = vertices

        self.indices = Delaunay(self.a_texcoord.T).simplices


        self.createBuffers()
