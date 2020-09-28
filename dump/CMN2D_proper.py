# -----------------------------------------------------------------------------
# Python and OpenGL for Scientific Visualization
# www.labri.fr/perso/nrougier/python+opengl
# Copyright (c) 2017, Nicolas P. Rougier
# Distributed under the 2-Clause BSD License.
# -----------------------------------------------------------------------------
import numpy as np
from scipy import signal
from glumpy import app, gl, glm, gloo
from dump import glSti


def cen2square(cen_x = np.array([0]),cen_y = np.array([0]), square_size = np.array([1])):
    square_r    = square_size/2
    squarePoint = np.array([[cen_x-square_r,cen_y-square_r],
                           [cen_x-square_r,cen_y+square_r],
                           [cen_x+square_r,cen_y+square_r],
                           [cen_x+square_r,cen_y-square_r]])
    return squarePoint.transpose([2,0,1])

def patchArray(imgsize = np.array([1,1]),startpoint = np.array([[0, 0], [0, 1], [1, 1], [1, 0]])):
    vtype = [('position', np.float32, 2),
             ('texcoord', np.float32, 2)]
    itype = np.uint32
    imgvertice = np.array([np.arange(imgsize[0]+1)]).T + \
                   np.array([np.arange(imgsize[1]+1)*1.j])
    adding_idx = np.arange(imgvertice.size).reshape(imgvertice.shape)

    # Vertices positions
    p = np.stack((np.real(imgvertice.flatten()),\
                    np.imag(imgvertice.flatten())),axis = -1)

    imgV_conn  = np.array([[0,1,imgvertice.shape[1],1,imgvertice.shape[1],imgvertice.shape[1]+1]], dtype=np.uint32) + \
                   np.array([adding_idx[0:-1,0:-1].flatten()], dtype=itype).T
    faces_t = np.resize(np.array([1, 0, 2, 0, 2, 3],dtype = itype),imgsize.prod()*6)
    faces_t += np.repeat(np.arange(imgsize.prod(),dtype = itype)*4,6)
    vertices = np.zeros(imgV_conn.size, vtype)
    vertices['position'] = p[imgV_conn.flatten()]
    vertices['texcoord'] = startpoint[faces_t]


    filled = np.arange(imgV_conn.size,dtype = itype)

    vertices = vertices.view(gloo.VertexBuffer)
    filled = filled.view(gloo.IndexBuffer)

    return vertices, filled, faces_t



vertex = """
uniform mat4   model;      // Model matrix
uniform mat4   view;       // View matrix
uniform mat4   projection; // Projection matrix
attribute vec2 position;   // Vertex position
attribute vec2 texcoord;   // Vertex texture coordinates red
varying vec2   v_texcoord;   // Interpolated fragment texture coordinates (out)
//attribute vec2 texcoord_G;   // Vertex texture coordinates red
//varying vec2   v_texcoord_G;   // Interpolated fragment texture coordinates (out)
//attribute vec2 texcoord_B;   // Vertex texture coordinates red
//varying vec2   v_texcoord_B;   // Interpolated fragment texture coordinates (out)

void main()
{
    // Assign varying variables
    v_texcoord  = texcoord;

    // Final position
    gl_Position = projection * view * model * vec4(position,0.0,1.0);
}
"""

fragment = """
uniform sampler2D texture;    // Texture
varying vec2      v_texcoord; // Interpolated fragment texture coordinates (in)
void main()
{
    // Final color
    gl_FragColor = texture2D(texture, v_texcoord);
}
"""

def on_draw(dt):
    self.window.clear()
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_DEPTH_TEST)
    tempsize = int(self.V['texcoord'].shape[0]/6)
    tidx = np.mod(self.t,99)
    motmat_R   = cen2square(self.motmat_x_R[:,tidx],self.motmat_y_R[:,tidx],0).reshape([-1,2])
    self.V['texcoord'] += motmat_R[textface]/300
    self.patchMat.trigger_on_draw(gl.GL_TRIANGLES, I)
    self.t+=1
    print(dt)

def on_resize(width, height):
    self.patchMat['projection'] = glm.perspective(45.0, width / float(height), 2.0, 100.0)

patchArray_size = np.array([200,200])
startpoint = cen2square(np.random.rand(patchArray_size.prod()),
                        np.random.rand(patchArray_size.prod()),
                        np.ones(patchArray_size.prod())/10).reshape([-1,2])
# first build the smoothing kernel
sigma = np.array([1,1,5])/2     # width of kernel
x = np.linspace(-10,10,50)   # coordinate arrays -- make sure they contain 0!
y = np.linspace(-10,10,50)
z = np.linspace(-10,10,50)
xx, yy, zz = np.meshgrid(x,y,z)
kernel = np.exp(-(xx**2/(2*sigma[0]**2) + yy**2/(2*sigma[1]**2) + zz**2/(2*sigma[2]**2)))
motmat_angle_R = np.exp(np.random.rand(*patchArray_size,100)*2.j*np.pi)
motmat_x_R = signal.convolve(motmat_angle_R.real,kernel,mode='same').reshape(patchArray_size.prod(),-1)
motmat_y_R = signal.convolve(motmat_angle_R.imag,kernel,mode='same').reshape(patchArray_size.prod(),-1)
V,I,textface = patchArray(patchArray_size,startpoint)
patchMat = gloo.Program(vertex, fragment)
patchMat.bind(V)
patchMat['texture'] = np.uint8(np.round((np.random.rand(100,100,1)>.5)*155+100)*np.array([[[1,1,1]]]))
patchMat['texture'].wrapping = gl.GL_REPEAT
patchMat['model'] = np.eye(4, dtype=np.float32)
patchMat['view'] = glm.translation(*patchArray_size*-.5, -50)

StiProgram = glSti.glSti()
StiProgram.t = 0
StiProgram.motmat_x_R = motmat_x_R
StiProgram.motmat_y_R = motmat_y_R
StiProgram.patchMat   = patchMat
StiProgram.V          = V
StiProgram.set_ondraw(on_draw)
StiProgram.set_onresize(on_resize)
StiProgram.backend = app.use("pyglet")
# StiProgram.window = app.Window(width=512, height=512, color=(0,0,0,1))
# StiProgram.window.dispatch_event('on_draw')
# app.run(framerate=60)
#%%
