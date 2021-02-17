from glumpy import gl
import h5py
import numpy as np
import os

from mappapp.core.visual import SphericalVisual
from models import Insta360OneX

class Calibrated(SphericalVisual):

    def __init__(self, *args, filename):
        SphericalVisual.__init__(self, *args)

        self.filename = '{}.mat'.format(filename)

        insta = self.filename.split('_')[0]

        self.model = self.addModel('model',
                                   Insta360OneX.Calibrated,
                                   filename=insta)
        self.program = self.addProgram('program',
                                       self.load_vertex_shader('v_tex.glsl', subdir='spherical'),
                                       self.load_shader('f_tex.glsl'))
        self.program.bind(self.model.vertexBuffer)

        self.file = h5py.File(os.path.join('media', self.filename), 'r')
        self.video = self.file['virtMaps'][:]

        self.i = 0

    def render(self):
        if self.i > 1000:
            self.i = 0
        #IPython.embed()
        #gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        #gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        self.setGlobalUniform('u_texture', np.flipud(self.video[self.i, :, :, :].T).copy())
        self.program.draw(gl.GL_TRIANGLES, self.model.indexBuffer)
        self.i += 1