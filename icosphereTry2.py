# -----------------------------------------------------------------------------
# Python and OpenGL for Scientific Visualization
# www.labri.fr/perso/nrougier/python+opengl
# Copyright (c) 2017, Nicolas P. Rougier
# Distributed under the 2-Clause BSD License.
# -----------------------------------------------------------------------------
import numpy as np
import os
from scipy import signal
from glumpy import app, gl, glm, gloo, data

def cen2tri(cen_x = np.array([0]),cen_y = np.array([0]), triangle_size = np.array([1])):
    # Assume the triangle will be equal angle ones
    ct1 = [cen_x-triangle_size/2*np.sqrt(3),cen_y-triangle_size/2]
    ct2 = [cen_x+triangle_size/2*np.sqrt(3),cen_y-triangle_size/2]
    ct3 = [cen_x,cen_y+triangle_size/2*np.sqrt(3)]
    squarePoint = np.array([ct1,ct2,ct3])
    return squarePoint.transpose([2,0,1])

def subdivide_triangle(vertices,faces,subdivide_order):
    subD_faces = faces;
    subD_vertices = vertices;
    for i in range(subdivide_order):
        edges = np.vstack([np.hstack([subD_faces[:,0],subD_faces[:,1],subD_faces[:,2]]),
                          np.hstack([subD_faces[:,1],subD_faces[:,2],subD_faces[:,0]])]).T
        [edges,inverse_order] = np.unique(np.sort(edges,axis =1),axis = 0,return_inverse = 1)
        inverse_order = np.reshape(inverse_order,[3,len(subD_faces)])+len(subD_vertices)
        midPoints = (subD_vertices[edges[:,0],:]+subD_vertices[edges[:,1],:])/2
        midPoints /= np.array([np.sqrt(np.sum(midPoints**2,axis=1))]).T/np.sqrt(np.sum(subD_vertices[0,:]**2))
        subD_vertices = np.vstack([subD_vertices,midPoints]);
        subD_faces = np.vstack([subD_faces,
                        np.array([subD_faces[:,0],inverse_order[0,:],inverse_order[2,:]]).T,
                        np.array([subD_faces[:,1],inverse_order[1,:],inverse_order[0,:]]).T,
                        np.array([subD_faces[:,2],inverse_order[2,:],inverse_order[1,:]]).T,
                        np.array([inverse_order[0,:],inverse_order[1,:],inverse_order[2,:]]).T])
        # print(len(subD_vertices))
    return subD_vertices,subD_faces

vertex = """
uniform mat4   model;      // Model matrix
uniform mat4   view;       // View matrix
uniform mat4   projection; // Projection matrix
attribute vec3 position;   // Vertex position
attribute vec2 texcoord;   // texture coordinate
varying   vec2 v_texcoord;  // output
//attribute vec3 a_color;    // Vertex color
//varying   vec4 v_color;    // Interpolated color (out)

void main()
{
    // Assign varying variables v_color     = vec4(a_color,1.0);
    v_texcoord  = texcoord;

    // Final position
    gl_Position = projection * view * model * vec4(position,1.0);
}
"""

fragment = """
uniform sampler2D texture;    // Texture
varying   vec2 v_texcoord;  // output
//varying vec4 v_color;
void main()
{
    // Final color
    //gl_FragColor = v_color;
    gl_FragColor = texture2D(texture, v_texcoord);
}
"""

def vecNorm(vec,Norm_axis = -1):
    return np.sqrt(np.sum(vec**2,Norm_axis))

def vecAngle(vec1,vec2,Norm_axis = -1):
    v1Norm = vecNorm(vec1,Norm_axis)
    v2Norm = vecNorm(vec2,Norm_axis)
    return np.arccos(np.sum(vec1*vec2,Norm_axis)/(v1Norm*v2Norm))

def sphAngle(vec, r):
     return np.arcsin(vecNorm(vec[:,np.newaxis,:]-vec[np.newaxis,:,:],2)/(2*r))*2


def icoSphere(subdivisionTimes = 1):
    r = (1+np.sqrt(5))/2

    vertices = np.array([
                        [-1.0,   r, 0.0],
                        [ 1.0,   r, 0.0],
                        [-1.0,  -r, 0.0],
                        [ 1.0,  -r, 0.0],
                        [0.0, -1.0,   r],
                        [0.0,  1.0,   r],
                        [0.0, -1.0,  -r],
                        [0.0,  1.0,  -r],
                        [  r, 0.0, -1.0],
                        [  r, 0.0,  1.0],
                        [ -r, 0.0, -1.0],
                        [ -r, 0.0,  1.0]
                        ]);

    faces = np.array([
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
                     ]);
    # [usV,usF] = [vertices,faces]
    [usV,usF] = subdivide_triangle(vertices,faces,subdivisionTimes)
    sphereR = vecNorm(usV[0,:]);
    tileCen = np.mean(usV[usF,:],axis = 1)
    tileDist = sphAngle(tileCen,sphereR)
    vtype = [('position', np.float32, 3),('texcoord', np.float32, 2)]
    # vtype = [('position', np.float32, 3),('a_color', np.float32, 3)]
    usF = np.uint32(usF.flatten())
    Vout = np.zeros(len(usF),vtype)
    Vout['position'] = usV[usF,:]
    Iout = np.arange(usF.size,dtype = np.uint32)
    # Vout['a_color'] = np.random.rand(*(usV.shape))
    # vertices = np.zeros(usV.shape[0], vtype)
    # vertices['position'] = usV
    # vertices['a_color']  = np.random.rand(*(usV.shape))
    # vertices = vertices.view(gloo.VertexBuffer)
    return Vout, Iout, tileDist,tileCen

app.use("pyglet")
window = app.Window(width=512, height=512, color=(0.30, 0.30, 0.35, 1.00))
keypressed = 0
keycontrol_increment = 1
p_dist = 0.687
@window.event
def on_draw(dt):
    global keypressed,model,z_distance,keycontrol_increment,t,motmat_x,motmat_y
    window.clear()
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_DEPTH_TEST)
    tidx = np.mod(t,499)
    motmat   = cen2tri(spsmooth_azi[:,tidx],spsmooth_elv[:,tidx],.01).reshape([-1,2])
    if keypressed == 97:
        patchMat['view'] = glm.translation(0,0,-z_distance)
        glm.rotate(model,-5*keycontrol_increment,*model[2,:3])
    elif keypressed == 100:
        patchMat['view'] = glm.translation(0,0,-z_distance)
        glm.rotate(model,5*keycontrol_increment,*model[2,:3])
    elif keypressed == 119:
        patchMat['view'] = glm.translation(0,0,-z_distance)
        glm.rotate(model,5*keycontrol_increment,1,0,0)
    elif keypressed == 115:
        patchMat['view'] = glm.translation(0,0,-z_distance)
        glm.rotate(model,-5*keycontrol_increment,1,0,0)
    elif keypressed == 113:
        z_distance -= .5*keycontrol_increment
        print(z_distance)
    elif keypressed == 101:
        z_distance += .5*keycontrol_increment
        print(z_distance)
    elif keypressed == 65507:
        model = np.eye(4, dtype=np.float32)
        z_distance = -3
    elif keypressed == 105:
        if keycontrol_increment <=.1:
            keycontrol_increment *= 2
        else:
            keycontrol_increment += .1
        print(keycontrol_increment)
    elif keypressed == 111:
        if keycontrol_increment <=.1:
            keycontrol_increment /= 2
        else:
            keycontrol_increment -= .1
        print(keycontrol_increment)
    else:
        V['texcoord'] += motmat/1000
    keycontrol_increment = min(max(keycontrol_increment,0.00001),10)
    patchMat['model'] = model
    patchMat['view'] = glm.translation(0,0,z_distance)
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthMask(gl.GL_TRUE)
    gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
    # patchMat['u_color'] = 1, 1, 1, 1
    patchMat.draw(gl.GL_TRIANGLES,I)
    t+=1
    print("FPS = %f " % app.clock.get_fps())

@window.event
def on_resize(width, height):
    ratio = width / float(height)
    patchMat['projection'] =  glm.perspective(45.0, ratio, 2.0, 100.0)

@window.event
def on_init():
    gl.glEnable(gl.GL_DEPTH_TEST)

@window.event
def on_key_press(symbol, modifiers):
    global keypressed
    if keypressed != 0:
        keypressed = np.mod(symbol,10)*np.mod(keypressed,10)
    else:
        keypressed = symbol

@window.event
def on_key_release(symbol, modifiers):
    global keypressed
    keypressed = 0

V,I,tileDist,tileCen = icoSphere(3)
sp_sigma = 1     # width of kernel
tp_sigma = 5
spkernel = np.exp(-(tileDist**2)/(2*sp_sigma**2))
spkernel *= spkernel>.001
tp_min_length = np.int(np.ceil(np.sqrt(-2*tp_sigma**2*np.log(.01*tp_sigma*np.sqrt(2*np.pi)))))
tpkernel = np.linspace(-tp_min_length,tp_min_length,num=2*tp_min_length+1)
tpkernel = 1/(tp_sigma*np.sqrt(2*np.pi))*np.exp(-(tpkernel)**2/(2*tp_sigma**2))
tpkernel *= tpkernel>.001
flowvec  = np.random.normal(size = [np.int(I.size/3),500,3])
flowvec  /= vecNorm(flowvec)[:,:,None]
tpsmooth_x = signal.convolve(flowvec[:,:,0],tpkernel[np.newaxis,:],mode='same')
tpsmooth_y = signal.convolve(flowvec[:,:,1],tpkernel[np.newaxis,:],mode='same')
tpsmooth_z = signal.convolve(flowvec[:,:,2],tpkernel[np.newaxis,:],mode='same')
spsmooth_x = np.dot(spkernel,tpsmooth_x)
spsmooth_y = np.dot(spkernel,tpsmooth_y)
spsmooth_z = np.dot(spkernel,tpsmooth_z)
tileDist.shape
spsmooth_azi = np.angle(spsmooth_x+spsmooth_y*1.j)*0
spsmooth_elv = np.angle(np.abs(spsmooth_x+spsmooth_y*1.j)+spsmooth_z*1.j)*0+1
### Just realize the way you define each triangle will affect their texture direction.
startpoint = cen2tri(np.random.rand(np.int(I.size/3)),np.random.rand(np.int(I.size/3)),.05)
V['texcoord'] = startpoint.reshape([-1,2])
V = V.view(gloo.VertexBuffer)
I = I.view(gloo.IndexBuffer)
t = 1
patchMat = gloo.Program(vertex, fragment)
patchMat.bind(V)
############### Need to solve the shared points problem ######## vertices['texcoord_R'] = startpoint[faces_t]

patchMat['texture'] = np.uint8(np.round((np.random.rand(100,100,1)>.5)*200+55)*np.array([[[1,1,1]]]))
patchMat['texture'].wrapping = gl.GL_REPEAT
model = np.eye(4, dtype=np.float32)
patchMat['model'] = model
patchMat['view']  = glm.translation(0,0,-6)

z_distance = -6


app.run(framerate=60)
