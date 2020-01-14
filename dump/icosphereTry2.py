# -----------------------------------------------------------------------------
# Spherical Contiguous Motion Noise (sphCMN) stimulus
# Author: Yue Zhang - AG Arrenberg
# CIN,Tuebingen  14.11.2019
# -----------------------------------------------------------------------------
import numpy as np
from scipy import signal
from helper.NashHelper import *
from glumpy import app, gl, glm, gloo

## Define vertex and fragment shaders

vertex = """
uniform mat4   model;      // Model matrix
uniform mat4   view;       // View matrix
uniform mat4   projection; // Projection matrix
attribute vec3 position;   // Vertex position
attribute vec2 texcoord;   // texture coordinate
varying   vec2 v_texcoord;  // output

void main()
{
    // Assign varying texture coordinate
    v_texcoord  = texcoord;
    
    // Vetex position
    gl_Position = projection * view * model * vec4(position,1.0);
}
"""

fragment = """
uniform sampler2D texture;    // Texture
varying   vec2 v_texcoord;  // output
void main()
{
    // 2D textuer mapping
    gl_FragColor = texture2D(texture, v_texcoord);
}
"""


def cen2tri(cen_x=np.array([0]), cen_y=np.array([0]), triangle_size=np.array([1])):
    """
    :param cen_x: (optional) ndarray; x coordinate of the triangle center; default = 0
    :param cen_y: (optional)ndarray; y coordinate of the triangle center; default = 0
    :param triangle_size: (optional) ndarray; size of the triangle defined as the distance from each vertex to the triangle center; default = 1
    :return: ndarray (shape = [...,2]) of the 3 triangle vertices coordinates for each triangle center entered
    """

    ct1 = [cen_x - triangle_size / 2 * np.sqrt(3), cen_y - triangle_size / 2]
    ct2 = [cen_x + triangle_size / 2 * np.sqrt(3), cen_y - triangle_size / 2]
    ct3 = [cen_x, cen_y + triangle_size / 2 * np.sqrt(3)]
    squarePoint = np.array([ct1, ct2, ct3])
    return squarePoint.transpose([2, 0, 1])


def subdivide_triangle(vertices, faces, subdivide_order):
    """
    :param vertices: N*3 ndarray, vertices of the triangulated sphere
    :param faces: N*3 ndarray, indices for the sphere vertices
    :param subdivide_order: number of times of subdivision
    :return: subdivided vertices and indices
    """
    for i in range(subdivide_order):
        edges = np.vstack([np.hstack([faces[:, 0], faces[:, 1], faces[:, 2]]),
                           np.hstack([faces[:, 1], faces[:, 2], faces[:, 0]])]).T
        [edges, inverse_order] = np.unique(np.sort(edges, axis=1), axis=0,
                                           return_inverse=True)  # Compute all edges linking the vertices
        inverse_order = np.reshape(inverse_order, [3, len(faces)]) + len(
            vertices)  # Since some edges are redundant, this and the line above deal with the redundancy
        midPoints = (vertices[edges[:, 0], :] + vertices[edges[:, 1], :]) / 2  # Find the middle point for all edges
        midPoints /= np.array([np.sqrt(np.sum(midPoints ** 2, axis=1))]).T / np.sqrt(
            np.sum(vertices[0, :] ** 2))  # Normalize them to the given sphere radius
        vertices = np.vstack([vertices, midPoints])  # Combine the old and new vertices
        faces = np.vstack([faces,
                           np.array([faces[:, 0], inverse_order[0, :], inverse_order[2, :]]).T,
                           np.array([faces[:, 1], inverse_order[1, :], inverse_order[0, :]]).T,
                           np.array([faces[:, 2], inverse_order[2, :], inverse_order[1, :]]).T,
                           np.array([inverse_order[0, :], inverse_order[1, :], inverse_order[2,
                                                                               :]]).T])  # Directly compute the subdivided indices without doing another tessellation
    return vertices, faces


def vecNorm(vec, Norm_axis=-1):  # Comput the norm of the vectors or tensors in ndarray
    return np.sqrt(np.sum(vec ** 2, Norm_axis))


def vecNormalize(vec, Norm_axis=-1):  # Normalize the ndarray vectors or tensors to norm = 1
    return vec / np.expand_dims(np.sqrt(np.sum(vec ** 2, Norm_axis)), Norm_axis)


# def vecAngle(vec1, vec2, Norm_axis=-1): # Compute the angle between two vectors.
#     v1Norm = vecNorm(vec1, Norm_axis)
#     v2Norm = vecNorm(vec2, Norm_axis)
#     return np.arccos(np.sum(vec1 * vec2, Norm_axis) / (v1Norm * v2Norm))

def sphAngle(vec, r):  # Compute the angle between two spherical coordinates as their distances on a unit sphere
    return np.arcsin(vecNorm(vec[:, np.newaxis, :] - vec[np.newaxis, :, :], 2) / (2 * r)) * 2


def icoSphere(subdivisionTimes=1):  # Subdividing 20-face icosahedron to icosphere with more faces

    # Defined the radius, vertices and faces for the icosahedron

    r = (1 + np.sqrt(5)) / 2

    vertices = np.array([
        [-1.0, r, 0.0],
        [1.0, r, 0.0],
        [-1.0, -r, 0.0],
        [1.0, -r, 0.0],
        [0.0, -1.0, r],
        [0.0, 1.0, r],
        [0.0, -1.0, -r],
        [0.0, 1.0, -r],
        [r, 0.0, -1.0],
        [r, 0.0, 1.0],
        [-r, 0.0, -1.0],
        [-r, 0.0, 1.0]
    ])

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
    ])

    [usV, usF] = subdivide_triangle(vertices, faces, subdivisionTimes)  # subdivision


    sphereR = vecNorm(usV[0, :])  # Compute the radius of all the vertices

    tileCen = np.mean(usV[usF, :], axis=1)  # Compute the center of each triangle tiles

    # The orientation of each triangle tile is defined as the direction perpendicular to the first edge of the triangle;
    # Here each orientation vector is represented by a complex number for the convenience of later computation
    tileOri = vecNormalize(np.cross(tileCen, usV[usF[:, 1], :] - usV[usF[:, 0], :]))\
                        + 1.j * vecNormalize(usV[usF[:, 1], :] - usV[usF[:, 0], :])

    tileDist = sphAngle(tileCen, sphereR)  # Spherical distance for each tile pair


    usF = np.uint32(usF.flatten())
    vtype = [('position', np.float32, 3), ('texcoord', np.float32, 2)]# Data type for the vertex buffer
    Vout = np.zeros(len(usF), vtype)  # Create the vertex array for vertex buffer
    Vout['position'] = usV[usF, :]    # Triangles must not share edges/vertices while doing texture mapping, this line duplicate the shared vertices for each triangle
    Iout = np.arange(usF.size, dtype=np.uint32)  # Construct the face indices array

    return Vout, Iout, tileDist, tileCen, tileOri


app.use("qt5")
window = app.Window(width=512, height=512, color=(0.30, 0.30, 0.35, 1.00))

@window.event
def on_draw(dt):
    global t, motmatFull
    window.clear()
    tidx = np.mod(t, 499)  # Loop every 500 frames
    motmat = np.repeat(motmatFull[:, tidx], 3, axis=0)  # updating the motion matrix
    V['texcoord'] += np.array([np.real(motmat), np.imag(motmat)]).T / 80 #  update texture coordinate based on the current motion matrix
    patchMat.draw(gl.GL_TRIANGLES, I)
    t += 1
    print("FPS = %f " % app.clock.get_fps())


@window.event
def on_resize(width, height):
    ratio = width / float(height)
    patchMat['projection'] = glm.perspective(45.0, ratio, 2.0, 100.0)


@window.event
def on_init():
    gl.glEnable(gl.GL_DEPTH_TEST)

V, I, tileDist, tileCen, tileOri = icoSphere(2)  # Generate
sp_sigma = .3  # spatial CR
tp_sigma = 15  # temporal CR
spkernel = np.exp(-(tileDist ** 2) / (2 * sp_sigma ** 2))
spkernel *= spkernel > .001
tp_min_length = np.int(np.ceil(np.sqrt(-2 * tp_sigma ** 2 * np.log(.01 * tp_sigma * np.sqrt(2 * np.pi)))))
tpkernel = np.linspace(-tp_min_length, tp_min_length, num=2 * tp_min_length + 1)
tpkernel = 1 / (tp_sigma * np.sqrt(2 * np.pi)) * np.exp(-(tpkernel) ** 2 / (2 * tp_sigma ** 2))
tpkernel *= tpkernel > .001

flowvec = np.random.normal(size=[np.int(I.size / 3), 500, 3]) # Random white noise motion vector
flowvec /= vecNorm(flowvec)[:, :, None]
tpsmooth_x = signal.convolve(flowvec[:, :, 0], tpkernel[np.newaxis, :], mode='same')
tpsmooth_y = signal.convolve(flowvec[:, :, 1], tpkernel[np.newaxis, :], mode='same')
tpsmooth_z = signal.convolve(flowvec[:, :, 2], tpkernel[np.newaxis, :], mode='same')
spsmooth_x = np.dot(spkernel, tpsmooth_x)
spsmooth_y = np.dot(spkernel, tpsmooth_y)
spsmooth_z = np.dot(spkernel, tpsmooth_z) # 
spsmooth_Q = qn(np.array([spsmooth_x, spsmooth_y, spsmooth_z]).transpose([1, 2, 0]))

tileCen_Q = qn(tileCen)
tileOri_Q1 = qn(np.real(tileOri)).normalize[:, None]
tileOri_Q2 = qn(np.imag(tileOri)).normalize[:, None]
projected_motmat = projection(tileCen_Q[:, None], spsmooth_Q)
motmatFull = qdot(tileOri_Q1, projected_motmat) - 1.j * qdot(tileOri_Q2, projected_motmat)


# projected_motmat = qn.ortho_project(tileCen_Q,spsmooth_Q)
# motAngle = qn.anglebtw(np.squeeze(projected_motmat),tileOri_Q[:,None]);
# motmatFull   = np.exp((np.pi/2-np.squeeze(motAngle))*1.j)#*spsmooth_Q.norm()

def cart2sph(cx, cy, cz):
    cxy = cx + cy * 1.j
    azi = np.angle(cxy)
    elv = np.angle(np.abs(cxy) + cz * 1.j)
    return azi, elv


spsmooth_azi = np.angle(spsmooth_x + spsmooth_y * 1.j) * 0 + 1
spsmooth_elv = np.angle(np.abs(spsmooth_x + spsmooth_y * 1.j) + spsmooth_z * 1.j) * 0
### Just realize the way you define each triangle will affect their texture direction.
startpoint = cen2tri(np.random.rand(np.int(I.size / 3)), np.random.rand(np.int(I.size / 3)), .1)
V_azi, V_elv = cart2sph(*V['position'].T)
############### Need to solve the shared points problem ########
V['texcoord'] = startpoint.reshape([-1, 2])
V = V.view(gloo.VertexBuffer)
I = I.view(gloo.IndexBuffer)
t = 1
patchMat = gloo.Program(vertex, fragment)
patchMat.bind(V)

### rgb noise texture
# saturation = np.random.rand(100,100)
# rgbnoise = np.eye(3)[np.random.randint(0,3,[100,100]),:]
# patchMat['texture'] = np.uint8(np.round(rgbnoise*200+55))

### grating texture
# texturemat = np.zeros([100,100,1]);
# texturemat[::2,:,:] = 1;
# patchMat['texture'] = np.uint8(texturemat*np.array([[[1,1,1]]])*255)

patchMat['texture'] = np.uint8(np.random.randint(0, 2, [100, 100, 1]) * np.array([[[1, 1, 1]]]) * 255)
patchMat['texture'].wrapping = gl.GL_REPEAT

model = np.eye(4, dtype=np.float32)
patchMat['model'] = model
patchMat['view'] = glm.translation(0, 0, -6)

z_distance = -6

app.run(framerate=60)
