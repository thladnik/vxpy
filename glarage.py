import numpy as np
import Q_num as qn

def UVsphere(azi, elv, azitile: int = 30, elvtile: int = 30):
    imgvertice = np.array([np.arange(azitile + 1)]).T + \
                 np.array([np.arange(elvtile + 1) * 1.j])
    sph_azi = np.exp(1.j * np.linspace(-azi / 2, azi / 2, azitile + 1))
    sph_elv = np.linspace(-elv / 2, elv / 2, elvtile + 1)
    sph_xz, sph_yz = np.meshgrid(sph_azi, sph_elv)
    sph_xz = sph_xz * np.sqrt(1 - sph_yz ** 2)
    adding_idx = np.arange(imgvertice.size).reshape(imgvertice.shape)

    # Vertices positions
    p3 = np.stack((np.real(sph_xz.flatten()), np.imag(sph_xz.flatten()), np.real(sph_yz.flatten())), axis=-1)
    p3[np.isnan(p3)] = 0
    p3 = vecNormalize(p3)
    imgV_conn = np.array([np.arange(azitile) + 1, np.arange(azitile), np.arange(azitile + 1, azitile * 2 + 1, 1),
                          np.arange(azitile + 1, azitile * 2 + 1, 1) + 1, np.arange(azitile + 1, azitile * 2 + 1, 1),
                          np.arange(azitile) + 1]
                         , dtype=np.uint32).T.flatten() + np.array([np.arange(0, elvtile + 1, 1)]).T * (azitile + 1)

    return p3, imgV_conn.reshape(-1, 3)


def cylinder(azimuth, height, radius: int = 1, azitile: int = 30, h_tile: int = 8):
    cyl_azi = np.exp(1.j * np.linspace(-azimuth / 2, azimuth / 2, azitile + 1))
    cyl_h = np.linspace(-height / 2, height / 2, h_tile + 1)
    cyl_xy, cyl_h = np.meshgrid(cyl_azi, cyl_h)
    cyl_xy = cyl_xy * radius

    # Vertices positions
    p3 = np.stack((np.real(cyl_xy.flatten()), np.imag(cyl_xy.flatten()), np.real(cyl_h.flatten())), axis=-1)
    # p3 = vecNormalize(p3)
    imgV_conn = np.array([np.arange(azitile) + 1, np.arange(azitile), np.arange(azitile + 1, azitile * 2 + 1, 1),
                          np.arange(azitile + 1, azitile * 2 + 1, 1), np.arange(azitile + 1, azitile * 2 + 1, 1) + 1,
                          np.arange(azitile) + 1]
                         , dtype=np.uint32).T.flatten() + np.array([np.arange(0, h_tile-1, 1)]).T * (azitile + 1)

    return p3, imgV_conn.reshape(-1, 3)

def proj_motmat(tileOri,tileCen,motmat):
    tileCen_Q = qn.qn(tileCen)
    tileOri_Q1 = qn.qn(np.real(tileOri)).normalize[:, None]
    tileOri_Q2 = qn.qn(np.imag(tileOri)).normalize[:, None]
    projected_motmat = qn.projection(tileCen_Q[:, None], motmat)
    motmat_out = qn.qdot(tileOri_Q1, projected_motmat) - 1.j * qn.qdot(tileOri_Q2, projected_motmat)
    return motmat_out

def tile_param(vertex,faces):
    tile_cen = np.mean(vertex[faces,:],1)
    tile_sign = np.sign(np.sum(tile_cen*np.cross(vertex[faces[:, 1], :] - vertex[faces[:, 0], :],vertex[faces[:, 1], :] - vertex[faces[:, 2], :]),axis = 1))
    tile_sign = tile_sign[:,None]
    tileOri = vecNormalize(np.cross(tile_cen, (vertex[faces[:, 1], :] - vertex[faces[:, 0], :]))) + 1.j * vecNormalize(
        (vertex[faces[:, 1], :] - vertex[faces[:, 0], :]))
    return tile_cen, tileOri

def rotation2D(theta):
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])


def load_shaderfile(fn):
    with open(fn, 'r') as shaderfile:
        return (shaderfile.read())

def cart2sph(cx,cy,cz):
    cxy = cx+cy*1.j
    azi = np.angle(cxy)
    elv = np.angle(np.abs(cxy)+cz*1.j)
    return azi, elv

def cen2tri(cen_x=np.array([0]), cen_y=np.array([0]), triangle_size=np.array([1])):
    # Assume the triangle will be equal angle ones
    ct1 = [cen_x - triangle_size / 2 * np.sqrt(3), cen_y - triangle_size / 2]
    ct2 = [cen_x + triangle_size / 2 * np.sqrt(3), cen_y - triangle_size / 2]
    ct3 = [cen_x, cen_y + triangle_size / 2 * np.sqrt(3)]
    squarePoint = np.array([ct1, ct2, ct3])
    return squarePoint.transpose([2, 0, 1])


def subdivide_triangle(vertices, faces, subdivide_order):
    subD_faces = faces
    subD_vertices = vertices
    for i in range(subdivide_order):
        edges = np.vstack([np.hstack([subD_faces[:, 0], subD_faces[:, 1], subD_faces[:, 2]]),
                           np.hstack([subD_faces[:, 1], subD_faces[:, 2], subD_faces[:, 0]])]).T
        [edges, inverse_order] = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True)
        inverse_order = np.reshape(inverse_order, [3, len(subD_faces)]) + len(subD_vertices)
        midPoints = (subD_vertices[edges[:, 0], :] + subD_vertices[edges[:, 1], :]) / 2
        midPoints /= np.array([np.sqrt(np.sum(midPoints ** 2, axis=1))]).T / np.sqrt(np.sum(subD_vertices[0, :] ** 2))
        subD_vertices = np.vstack([subD_vertices, midPoints])
        subD_faces = np.vstack([subD_faces,
                                np.array([subD_faces[:, 0], inverse_order[0, :], inverse_order[2, :]]).T,
                                np.array([subD_faces[:, 1], inverse_order[1, :], inverse_order[0, :]]).T,
                                np.array([subD_faces[:, 2], inverse_order[2, :], inverse_order[1, :]]).T,
                                np.array([inverse_order[0, :], inverse_order[1, :], inverse_order[2, :]]).T])
        # print(len(subD_vertices))
    return subD_vertices, subD_faces


def vecNorm(vec, Norm_axis=-1):
    return np.sqrt(np.sum(vec ** 2, Norm_axis))


def vecNormalize(vec, Norm_axis=-1):
    return vec / np.expand_dims(np.sqrt(np.sum(vec ** 2, Norm_axis)), Norm_axis)


def vecAngle(vec1, vec2, Norm_axis=-1):
    v1Norm = vecNorm(vec1, Norm_axis)
    v2Norm = vecNorm(vec2, Norm_axis)
    return np.arccos(np.sum(vec1 * vec2, Norm_axis) / (v1Norm * v2Norm))


def sphAngle(vec, r):
    return np.arcsin(vecNorm(vec[:, np.newaxis, :] - vec[np.newaxis, :, :], 2) / (2 * r)) * 2


def icoSphere(subdivisionTimes=1):
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

    [usV, usF] = subdivide_triangle(vertices, faces, subdivisionTimes)
    sphereR = vecNorm(usV[0, :])
    tileCen = np.mean(usV[usF, :], axis=1)
    tileOri = vecNormalize(np.cross(tileCen, usV[usF[:, 1], :] - usV[usF[:, 0], :])) + 1.j * vecNormalize(
        usV[usF[:, 1], :] - usV[usF[:, 0], :])
    tileDist = sphAngle(tileCen, sphereR)
    vtype = [('position', np.float32, 3), ('texcoord', np.float32, 2)]
    usF = np.uint32(usF.flatten())
    Vout = np.zeros(len(usF), vtype)
    Vout['position'] = usV[usF, :]
    Iout = np.arange(usF.size, dtype=np.uint32)

    return Vout, Iout, tileDist, tileCen, tileOri
