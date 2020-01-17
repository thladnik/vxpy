from glumpy import gl
import h5py
import numpy as np
import os
from scipy import io

from Definition import Path
from Stimulus import SphericalStimulus
from models import Insta360OneX
from Shader import Shader

class Calibrated(SphericalStimulus):

    def __init__(self, protocol, display, filename):
        SphericalStimulus.__init__(self, protocol, display)

        self.filename = '{}.mat'.format(filename)

        insta = self.filename.split('_')[0]

        self.model = self.addModel('model',
                                   Insta360OneX.Calibrated,
                                   filename=insta)
        self.program = self.addProgram('program',
                                       Shader().addShaderFile('v_tex.shader').read(),
                                       Shader().addShaderFile('f_tex.shader').read())
        self.program.bind(self.model.vertexBuffer)

        self.file = h5py.File(os.path.join('media', self.filename), 'r')
        self.video = self.file['virtMaps'][:]

        self.i = 0

    def render(self):
        if self.i > 1000:
            self.i = 0
        import IPython
        #IPython.embed()
        #gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        #gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        self.setUniform('u_texture', np.flipud(self.video[self.i, :,:,:].T).copy())
        self.program.draw(gl.GL_TRIANGLES, self.model.indexBuffer)
        self.i += 1