import numpy as np
from glarage import *
from glumpy import app, gl, glm, gloo

shader_folder = './shaderfile/'
vertex_shader_fn = 'VS_tex_1511.glsl'
frag_shader_fn = 'FS_tex_1511.glsl'

vertex = load_shaderfile(shader_folder + vertex_shader_fn)
fragment = load_shaderfile(shader_folder + frag_shader_fn)
sphV, sphI = cylinder(np.pi * 2.001, 10, 1, 30, 300)

tile_cen, tile_ori = tile_param(sphV,sphI)
# sphV -= np.mean(sphV, 0)
# sphV /= vecNorm(sphV)[:, None]

app.use("qt5")
window = app.Window(width=512, height=512,
                    color=(0.30, 0.30, 0.35, 1.00))


@window.event
def on_draw(dt):
    global t, projectMat, translateMat, mot2d, inputV
    t += 1
    V['texcoord'] += np.repeat(np.hstack([np.real(mot2d),np.imag(mot2d)]),3, axis=0)/ 80 # update texture coordinate based on the current motion matrix
    tempV = inputV + np.array([np.sin(t/20), np.cos(t/20),0])/5
    temp_azi, temp_elv = cart2sph(tempV[:, 0], tempV[:, 1], tempV[:, 2])
    temp_azi = temp_azi.reshape(-1, 3)
    temp_ptest = (d_range(temp_azi, rangeaxis=1)[:, None] * np.ones([1, 3]) > np.pi) & (temp_azi< 0) & (temp_azi > -np.pi)
    temp_azi[temp_ptest] += (np.pi * 2)
    temp_azi = temp_azi.flatten()
    V["texcoord"] = np.hstack([temp_azi[:, None]*40/2/np.pi, temp_elv[:, None]])/40
    # translateMat = glm.translation(np.sin(t/20)/5, np.cos(t/20)/5, -1+t/100)
    rotateMat = glm.rotate(np.eye(4), t / 16, 0.5, .25, 0)
    Shape['u_transformation'] = rotateMat @ translateMat @ projectMat
    Shape['u_scale'] = 1, 1
    # Shape['u_color'] = 0.1, .2, .2, 1

    window.clear()
    Shape.draw(gl.GL_TRIANGLES, I)


@window.event
def on_resize(width, height):
    global projectMat
    projectMat = glm.perspective(90.0, width / float(height), 0.1, 100.0)


@window.event
def on_init():
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_STENCIL_TEST)

t = 0
V = np.zeros(sphV[sphI.flatten(),:].shape[0], [("position", np.float32, 3),
                             ("texcoord", np.float32, 2)])
inputV = sphV[sphI.flatten(),:]
inputazi,inputelv = cart2sph(inputV[:,0],inputV[:,1],inputV[:,2])
inputazi_ptest = inputazi.reshape(-1,3)
def d_range(data,rangeaxis = 0):
    return np.max(data,axis = rangeaxis)-np.min(data,axis = rangeaxis)

inputazi_ptest[(d_range(inputazi_ptest,rangeaxis = 1)[:,None]*np.ones([1,3])>np.pi) & (inputazi_ptest<0)] = np.pi*2 - inputazi_ptest[(d_range(inputazi_ptest,rangeaxis = 1)[:,None]*np.ones([1,3])>np.pi) & (inputazi_ptest<0)]
V["position"] = vecNormalize(inputV)
I = np.arange(sphV[sphI.flatten(),:].shape[0]).astype(np.uint32)
startpoint = cen2tri(np.random.rand(np.int(I.size / 3)), np.random.rand(np.int(I.size / 3)), .05)
V["texcoord"] = np.hstack([inputazi[:,None],inputelv[:,None]])/1 #startpoint.reshape([-1,2])
V = V.view(gloo.VertexBuffer)
I = I.view(gloo.IndexBuffer)

tileCen_Q = qn.qn(tile_cen)
motionmat = qn.qn(np.array([0,0,1]))
mot2d = proj_motmat(tile_ori,tile_cen,motionmat)/4
mot2d *= 0
mot2d -= 1.j*.05
# mot2d *= 1.j**1.0
Shape = gloo.Program(vertex, fragment)
Shape.bind(V)
rotateMat = np.eye(4)#glm.rotate(np.eye(4), 0, 0, 0, 0)
translateMat = glm.translation(0, 0, -2)
projectMat = glm.perspective(45.0, 1, 2.0, 100.0)
Shape['u_transformation'] = rotateMat @ translateMat @ projectMat
Shape['u_rotate'] = rotation2D(np.pi / 2)
Shape['u_shift'] = np.array([.5, .5]) * 0
Shape['texture'] = np.uint8(np.random.randint(0, 2, [1000, 100, 1]) * np.array([[[1, 1, 1]]]) * 255)
Shape['texture'].wrapping = gl.GL_REPEAT
app.run()
