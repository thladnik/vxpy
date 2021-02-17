"""
MappApp ./utils/geometry.py
Copyright (C) 2020 Yue Zhang, Tim Hladnik

* The "qn" class was originally created by Yue Zhang and is also available
   at https://github.com/nash-yzhang/Q_numpy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import numpy as np
import warnings

def createUVSphere(azi, elv, azitile = 30, elvtile = 30):
    sph_azi = np.exp(1.j * np.linspace(-azi / 2, azi / 2, azitile + 1))
    sph_elv = np.linspace(-elv / 2, elv / 2, elvtile + 1)
    sph_xz, sph_yz = np.meshgrid(sph_azi, sph_elv)
    sph_xz = sph_xz * np.sqrt(1 - sph_yz ** 2)

    # Vertices positions
    p3 = np.stack((np.real(sph_xz.flatten()), np.imag(sph_xz.flatten()), np.real(sph_yz.flatten())), axis=-1)
    p3[np.isnan(p3)] = 0
    p3 = vecNormalize(p3)
    imgV_conn = np.array([np.arange(azitile) + 1, np.arange(azitile), np.arange(azitile + 1, azitile * 2 + 1, 1),
                          np.arange(azitile + 1, azitile * 2 + 1, 1) + 1, np.arange(azitile + 1, azitile * 2 + 1, 1),
                          np.arange(azitile) + 1]
                         , dtype=np.uint32).T.flatten() + np.array([np.arange(0, elvtile + 1, 1)]).T * (azitile + 1)

    return p3, imgV_conn.reshape(-1, 3)

def rotation2D(theta):
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])

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

def sphAngle(vec, r):  # Compute the angle between two spherical coordinates as their distances on a unit sphere
    return np.arcsin(vecNorm(vec[:, np.newaxis, :] - vec[np.newaxis, :, :], 2) / (2 * r)) * 2

def cart2sph(cx,cy,cz):
    cxy = cx + cy * 1.j
    azi = np.angle(cxy)
    elv = np.angle(np.abs(cxy)+cz * 1.j)
    return azi, elv

class qn(np.ndarray):
    """
    Created on Fri Aug 9 10:11:32 2019
    Last update: Fri Nov 8 17:14:32 2019
    @author: Yue Zhang
    """

    qn_dtype = [('w', np.double), ('x', np.double), ('y', np.double), ('z', np.double)]

    def __new__(cls, compact_mat):
        """
        Override the __new__ function of ndarray for generating new instance of quaternion array
        ----------------------------------
        :param compact_mat: M x ... x N x 4 ndarray or list. The slices of the last dimension will be assigned as the 4 parts of quaternion. If the last dimension of the input array only have 3 slices, then the input
                                array is assumed to be the coordinates of 3D cartesian space, the slices in
                                such an array will be assigned the field x, y, z respectively, the field w
                                will be filled with 0. A warning message will be returned to remind the
                                assumption of the input data structure.
        :return: M x ... x N quaternion structured array.
        """
        mattype = type(compact_mat)
        if mattype == list:  # Check if input is ndarray or list, else return a type error
            compact_mat = np.asarray(compact_mat)
        elif mattype == np.ndarray:
            pass
        else:
            raise Exception('Input array should be a list or ndarray, instead its type is %s\n' % mattype)
        matshape = compact_mat.shape  # Shape checking: should be M x ... x 4 or x 3 ndarray, otherwise return error
        qn_compact = np.zeros([*matshape[:-1]], dtype=qn.qn_dtype)  # Preallocate space
        qn_compact = np.full_like(qn_compact, np.nan)  # filled with nan for debugging.
        if matshape[-1] == 4:
            compactMat_r = compact_mat.reshape([-1, 4])
            qn_compact['w'] = compactMat_r[:, 0].reshape(matshape[:-1])
            qn_compact['x'] = compactMat_r[:, 1].reshape(matshape[:-1])
            qn_compact['y'] = compactMat_r[:, 2].reshape(matshape[:-1])
            qn_compact['z'] = compactMat_r[:, 3].reshape(matshape[:-1])
        elif matshape[-1] == 3:
            targetshape = list(matshape)
            targetshape[-1] = 4
            compactMat_r = compact_mat.reshape([-1, 3])
            qn_compact['w'] = np.zeros(matshape[:-1])
            qn_compact['x'] = compactMat_r[:, 0].reshape(matshape[:-1])
            qn_compact['y'] = compactMat_r[:, 1].reshape(matshape[:-1])
            qn_compact['z'] = compactMat_r[:, 2].reshape(matshape[:-1])
            warningmsg = "Input array %s is set to %s" % (matshape, tuple(targetshape))
            warnings.warn(warningmsg)
        else:
            raise Exception('Input array should be a N x ... x 4 matrix, instead its shape is %s\n' % (matshape,))
        obj = qn_compact.view(cls)  # Convert to quaternion ndarray object
        if obj.shape == ():  # Convert 1 element array (has 0 dim) to 1-d array
            obj = np.expand_dims(obj, -1)
        return obj

    ###################################  Method  ###################################

    def __getitem__(self, keys):
        """
        Custom indexing for structured quaternion ndarray
        """
        if type(keys) == int:  # If index is integer, converted to slices; otherwise cause error
            keys = slice(keys, keys + 1)
        sub_self = self.view(np.ndarray)[keys]
        # sub_self = super(qn,self).__getitem__(keys)
        if type(keys) != str:
            return sub_self.view(qn)
        else:
            return sub_self.view(np.ndarray)

    def __repr__(self):
        """
        Custom representation for the quaternion array. each quaternion number will be
        show as "a+bi+cj+dk". The printed string are organized in the same way
        as the quaternion ndarray
        """
        concate_qArray = self.compact
        stringArray = []
        for ci in range(concate_qArray.shape[0]):
            stringArray.append("%+.4g%+.4gi%+.4gj%+.4gk" % tuple(concate_qArray[ci, :]))
        stringOutput = np.array2string(np.asarray(stringArray).reshape(self['w'].shape))
        if len(stringOutput) > 1000 // 4 * 4:
            stringOutput = stringOutput[:1000 // 4 * 4] + '...'

        return '\n'.join(["Quaternion Array " + str(self.shape) + ": ", stringOutput])

    def __neg__(self):
        # Elementary arithmetic: qn * -1
        compactProduct = -self.matrixform
        return np.reshape(compactProduct.view(self.qn_dtype).view(qn), compactProduct.shape[:-1])

    def __add__(self, qn2):
        # Elementary arithmetic: qn1 + qn2 or qn1 + r (real number). Same as the elementary arithmetic for real number
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.ndarray, np.float64, np.float32, np.int)]):
            compactProduct = self.matrixform + qn2
        elif qn2.__class__ == self.__class__:
            compactProduct = self.matrixform + qn2.matrixform
        else:
            raise ValueError('Invalid type of input')
        return np.reshape(compactProduct.view(self.qn_dtype).view(qn), compactProduct.shape[:-1])

    def __iadd__(self, qn2):
        # Elementary arithmetic: qn1 += qn2 or qn1 += r
        return self.__add__(qn2)

    def __radd__(self, qn2):
        # Elementary arithmetic: qn2 + qn1 or r + qn1
        return self.__add__(qn2)

    def __sub__(self, qn2):
        # Elementary arithmetic: qn1 - qn2. Same as the elementary arithmetic for real number
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.ndarray, np.float64, np.float32, np.int)]):
            compactProduct = self.matrixform - qn2
        elif qn2.__class__ == qn:
            compactProduct = self.matrixform - qn2.matrixform
        else:
            raise ValueError('Invalid type of input')
        return np.reshape(compactProduct.view(self.qn_dtype).view(qn), compactProduct.shape[:-1])

    def __isub__(self, qn2):
        # Elementary arithmetic: qn1 -= qn2 or qn1 -= r
        return self.__sub__(qn2)

    def __rsub__(self, qn2):
        # Elementary arithmetic: qn2 - qn1 or r - qn1
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.ndarray, np.float64, np.float32, np.int)]):
            compactProduct = qn2 - self.matrixform
        elif qn2.__class__ == qn:
            compactProduct = qn2.matrixform - self.matrixform
        else:
            raise ValueError('Invalid type of input')
        return np.reshape(compactProduct.view(self.qn_dtype).view(qn), compactProduct.shape[:-1])

    def __mul__(self, qn2):
        # Elementary arithmetic: qn1 * qn2; check https://en.wikipedia.org/wiki/Quaternion#Algebraic_properties for
        # details
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.ndarray, np.float64, np.float32, np.int)]):
            # if qn1 * r, then the same as real number calculation
            compactProduct = self.matrixform * qn2
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == self.__class__:
            temp_shape = (self['w'] * qn2['w']).shape
            if not temp_shape:
                compactProduct = np.zeros([(self['w'] * qn2['w']).size], dtype=self.qn_dtype)
            else:
                compactProduct = np.zeros([*temp_shape], dtype=self.qn_dtype)
            compactProduct = np.full_like(compactProduct, np.nan)
            compactProduct['w'] = self['w'] * qn2['w'] - self['x'] * qn2['x'] - self['y'] * qn2['y'] - self['z'] * qn2[
                'z']
            compactProduct['x'] = self['w'] * qn2['x'] + self['x'] * qn2['w'] + self['y'] * qn2['z'] - self['z'] * qn2[
                'y']
            compactProduct['y'] = self['w'] * qn2['y'] - self['x'] * qn2['z'] + self['y'] * qn2['w'] + self['z'] * qn2[
                'x']
            compactProduct['z'] = self['w'] * qn2['z'] + self['x'] * qn2['y'] - self['y'] * qn2['x'] + self['z'] * qn2[
                'w']
        else:
            raise ValueError('Invalid type of input')
        return compactProduct.view(qn)

    def __rmul__(self, qn2):
        # Elementary arithmetic: qn2 * qn1; Note the result of _rmul_ and _mul_ are not equal for quaternion
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.ndarray, np.float64, np.float32, np.int)]):
            compactProduct = self.matrixform * qn2
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == self.__class__:
            temp_shape = (self['w'] * qn2['w']).shape
            if not temp_shape:
                compactProduct = np.zeros([(self['w'] * qn2['w']).size], dtype=self.qn_dtype)
            else:
                compactProduct = np.zeros([*temp_shape], dtype=self.qn_dtype)
            compactProduct = np.full_like(compactProduct, np.nan)
            compactProduct['w'] = qn2['w'] * self['w'] - qn2['x'] * self['x'] - qn2['y'] * self['y'] - qn2['z'] * self[
                'z']
            compactProduct['x'] = qn2['w'] * self['x'] + qn2['x'] * self['w'] + qn2['y'] * self['z'] - qn2['z'] * self[
                'y']
            compactProduct['y'] = qn2['w'] * self['y'] - qn2['x'] * self['z'] + qn2['y'] * self['w'] + qn2['z'] * self[
                'x']
            compactProduct['z'] = qn2['w'] * self['z'] + qn2['x'] * self['y'] - qn2['y'] * self['x'] + qn2['z'] * self[
                'w']
        else:
            raise ValueError('Invalid type of input')
        return compactProduct.view(qn)

    def __imul__(self, qn2):
        # Elementary arithmetic: qn1 *= qn2; check https://en.wikipedia.org/wiki/Quaternion#Algebraic_properties for
        # details
        return self.__mul__(qn2)

    def __truediv__(self, qn2):
        # Elementary arithmetic: qn1 / qn2; Note the result of __truediv__ and __rtruediv__ are not equal for quaternion
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.float64, np.float32, np.int)]):
            compactProduct = self.matrixform / qn2
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == np.ndarray:
            compactProduct = self.matrixform / qn2[..., None]
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == self.__class__:
            inv_qn2 = qn2.inv
            temp_shape = (self['w'] * inv_qn2['w']).shape
            if not temp_shape:
                compactProduct = np.zeros([(self['w'] * inv_qn2['w']).size], dtype=self.qn_dtype)
            else:
                compactProduct = np.zeros([*temp_shape], dtype=self.qn_dtype)
            compactProduct = np.full_like(compactProduct, np.nan)
            compactProduct['w'] = self['w'] * inv_qn2['w'] - self['x'] * inv_qn2['x'] - self['y'] * inv_qn2['y'] - self[
                'z'] * inv_qn2['z']
            compactProduct['x'] = self['w'] * inv_qn2['x'] + self['x'] * inv_qn2['w'] + self['y'] * inv_qn2['z'] - self[
                'z'] * inv_qn2['y']
            compactProduct['y'] = self['w'] * inv_qn2['y'] - self['x'] * inv_qn2['z'] + self['y'] * inv_qn2['w'] + self[
                'z'] * inv_qn2['x']
            compactProduct['z'] = self['w'] * inv_qn2['z'] + self['x'] * inv_qn2['y'] - self['y'] * inv_qn2['x'] + self[
                'z'] * inv_qn2['w']
        else:
            raise ValueError('Invalid type of input')
        return compactProduct.view(qn)

    def __rtruediv__(self, qn2):
        """
        Elementary arithmetic: qn2 / qn1; Note the result of __truediv__ and __rtruediv__ are not equal for quaternion

        :param qn2: quaternion or real number ndarray
        :return: quaternion ndarray; qn2 / qn1
        """
        inv_self: qn = self.inv
        if any([1 if (qn2.__class__ == k) else 0 for k in (int, float, np.float64, np.float32, np.int)]):
            compactProduct = inv_self.matrixform / qn2
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == np.ndarray:
            compactProduct = inv_self.matrixform / qn2[..., None]
            compactProduct = np.reshape(compactProduct.view(self.qn_dtype), compactProduct.shape[:-1])
        elif qn2.__class__ == self.__class__:
            temp_shape = (qn2['w'] * inv_self['w']).shape
            if not temp_shape:
                compactProduct = np.zeros([(qn2['w'] * inv_self['w']).size], dtype=self.qn_dtype)
            else:
                compactProduct = np.zeros([*temp_shape], dtype=self.qn_dtype)
            compactProduct = np.full_like(compactProduct, np.nan)
            compactProduct['w'] = qn2['w'] * inv_self['w'] - qn2['x'] * inv_self['x'] - qn2['y'] * inv_self['y'] - qn2[
                'z'] * inv_self['z']
            compactProduct['x'] = qn2['w'] * inv_self['x'] + qn2['x'] * inv_self['w'] + qn2['y'] * inv_self['z'] - qn2[
                'z'] * inv_self['y']
            compactProduct['y'] = qn2['w'] * inv_self['y'] - qn2['x'] * inv_self['z'] + qn2['y'] * inv_self['w'] + qn2[
                'z'] * inv_self['x']
            compactProduct['z'] = qn2['w'] * inv_self['z'] + qn2['x'] * inv_self['y'] - qn2['y'] * inv_self['x'] + qn2[
                'z'] * inv_self['w']
        else:
            raise ValueError('Invalid type of input')
        return compactProduct.view(qn)

    def __itruediv__(self, qn2):
        """
        Elementary arithmetic: qn1 /= qn2 (or real number);

        :param qn2: quaternion or real number ndarray
        :return: quaternion ndarray;
        """
        # Elementary arithmetic:
        return self.__truediv__(qn2)

    ########### Properties ###########
    @property
    def matrixform(self):
        """
        Converted to the double M x ... x 4 unstructured ndarray

        :return:  M x ... x 4 ndarray
        """
        compact_dtype = np.dtype([('wxyz', 'double', 4)])
        return self.view(compact_dtype)['wxyz']

    @property
    def compact(self):
        """
        Converted to double (Mx...xN) x 4 unstructured ndarray

        :return:  (Mx...xN) x 4 ndarray
        """
        #
        return self.matrixform.reshape(-1, 4)

    @property
    def conj(self):
        """
        Conjugate: conj(a+bi+cj+dk) = a-bi-cj-dk

        :return: conjugate quaternion ndarray
        """
        conj_num = self.view(np.ndarray)
        conj_num['x'] *= -1
        conj_num['y'] *= -1
        conj_num['z'] *= -1
        return conj_num.view(qn)

    @property
    def inv(self):
        """

        :return: inverse number of quaternion ndarray
        """
        # 1/qn
        qconj = self.conj
        Q_innerproduct = self * qconj
        Q_ip_inv = 1 / Q_innerproduct['w']
        # The broadcast calculation is necessary here, but need to take care of the redundant dimension otherwise will run into dimensionality expansion problem all the time
        return np.squeeze(qconj * Q_ip_inv[..., None]).view(qn)

    @property
    def qT(self):
        """
        Transposition of quaternion array returns the conjugated quaternions
        If want transposition without getting the conjugate number, use .T

        :return: transposed quaternion ndarray
        """

        return self.conj.T

    @property
    def imag(self):
        """

        :return: quatenrion ndarray with real part set to 0;
        """
        imagpart = np.copy(self)
        imagpart['w'] = 0
        return imagpart.view(qn)

    @property
    def real(self):
        """

         :return: quatenrion ndarray with imag part set to 0;
         """

        realpart = np.copy(self)
        realpart['x'] = 0
        realpart['y'] = 0
        realpart['z'] = 0
        return realpart.view(qn)

    @property
    def imagpart(self):
        # Return the double real number matrix (M x ... x 3) of the imaginary part
        return self.matrixform[..., 1:]

    @property
    def realpart(self):
        # Return the double real number matrix (M x ... x1) of the real part
        return self['w']

    @property
    def norm(self):
        # Return the norm (or the absolute value) of the quaternion number
        return np.sqrt(np.sum(self.matrixform ** 2, axis=-1))

    @property
    def normalize(self):
        # Return the normalized quaternion number (norm = 1)
        return self / self.norm

    @property
    def leftmul_matrix(self):
        # Return the corresponding matrix for quaternion left multiplication
        # See http://www.euclideanspace.com/maths/algebra/realNormedAlgebra/quaternions/transforms/
        matself = self.view(np.ndarray)
        lm_mat = np.array([[matself['w'], matself['x'], matself['y'], matself['z']],
                           [matself['x'], -matself['w'], matself['z'], -matself['y']],
                           [matself['y'], -matself['z'], -matself['w'], matself['x']],
                           [matself['z'], matself['y'], -matself['x'], -matself['w']]])
        return lm_mat

    @property
    def conj_sandwich_mat(self):
        # Return the corresponding matrix QN so (qn1*qn2*qn.conj).matrixform = QN*[qn2.w;qn2.x,qn2.y;qn2.z]
        # Equal to rotation matrix
        return sliceDot(self.leftmul_matrix, self.leftmul_matrix)

    @property
    def sandwich_mat(self):
        # Return the corresponding matrix QN so (qn1*qn2*qn).matrixform = QN*[qn2.w;qn2.x,qn2.y;qn2.z]
        # Equal to reflection matrix
        return sliceDot(-self.leftmul_matrix, self.leftmul_matrix)

    def sum(self, **kwargs):
        # Not recommended, use the Q_num.sum function instead
        sum_axis = kwargs.pop('axis', None)
        if sum_axis:
            if sum_axis < 0:
                sum_axis -= 1
            elif sum_axis > self.ndim:
                raise np.AxisError('axis %d is out of bounds for array of dimension %d' % (sum_axis, self.ndim))
        else:
            sum_axis = 0
        kwargs['axis'] = sum_axis
        if not self.shape:
            qmatSum = self.matrixform
        else:
            qmatSum = np.sum(self.matrixform, **kwargs)
        return qmatSum.view(self.qn_dtype).view(qn)


################################### Functions ###################################
def sliceDot(mat1, mat2):
    """

    :param mat1: ndarray with ndim >= 2
    :param mat2: ndarray with ndim >= 2
    :return: inner product of each 2D slice of the two N-D matrices
    """
    ein_char = 'abcdefghijklmnopqrstuvwxyz'
    mat1string = ein_char[:mat1.ndim]
    mat2string = ein_char[1] + ein_char[mat1.ndim] + ein_char[2:mat1.ndim]
    outputstring = ein_char[0] + ein_char[mat1.ndim] + ein_char[2:mat1.ndim]
    ein_string = '%s,%s -> %s' % (mat1string, mat2string, outputstring)
    return np.einsum(ein_string, mat1, mat2)


def stack(*qn_array, **kwargs):
    # Same as np.stack
    stack_axis = kwargs.pop('axis', None)
    if stack_axis == 0:
        qmatStack = np.hstack([x.matrixform for x in qn_array], **kwargs)
    elif stack_axis == 1:
        qmatStack = np.vstack([x.matrixform for x in qn_array], **kwargs)
    else:
        qmatStack = np.stack([x.matrixform for x in qn_array], **kwargs)
    return qmatStack.view(qn.qn_dtype).view(qn)


def sum(*qn_array, **kwargs):
    # Same as np.sum
    sum_axis = kwargs.pop('axis', None)
    if sum_axis:
        if sum_axis < 0:
            sum_axis -= 1
        elif sum_axis > qn_array[0].ndim:
            raise np.AxisError('axis %d is out of bounds for array of dimension %d' % (sum_axis, qn_array[0].ndim))
    else:
        sum_axis = 0
    kwargs['axis'] = sum_axis

    qmatStack = np.squeeze(np.stack([x for x in qn_array], **kwargs))
    if not qmatStack.shape:
        qmatSum = qmatStack.view(qn).matrixform
    else:
        qmatSum = np.sum(qmatStack.view(qn).matrixform, **kwargs)
    return qmatSum.view(qn_array[0].qn_dtype).view(qn)


def nansum(*qn_array, **kwargs):
    # Same as np.nansum, calculate the sum but ignore nan numbers
    sum_axis = kwargs.pop('axis', None)
    if sum_axis:
        if sum_axis < 0:
            sum_axis -= 1
        elif sum_axis > qn_array[0].ndim:
            raise np.AxisError('axis %d is out of bounds for array of dimension %d' % (sum_axis, qn_array[0].ndim))
    else:
        sum_axis = 0
    kwargs['axis'] = sum_axis
    qmatStack = np.squeeze(np.stack([x for x in qn_array], **kwargs))
    if not qmatStack.shape:
        qmatSum = qmatStack.view(qn).matrixform
    else:
        qmatSum = np.nansum(qmatStack.view(qn).matrixform, **kwargs)
    return qmatSum.view(qn_array[0].qn_dtype).view(qn)


def mean(*qn_array, **kwargs):
    # Same as np.mean
    sum_axis = kwargs.pop('axis', None)
    if sum_axis:
        if sum_axis < 0:
            sum_axis -= 1
        elif sum_axis > qn_array[0].ndim:
            raise np.AxisError('axis %d is out of bounds for array of dimension %d' % (sum_axis, qn_array[0].ndim))
    else:
        sum_axis = 0
    kwargs['axis'] = sum_axis
    qmatStack = np.squeeze(np.stack([x for x in qn_array], **kwargs))
    if not qmatStack.shape:
        qmatSum = qmatStack.view(qn).matrixform
    else:
        qmatSum = np.mean(qmatStack.view(qn).matrixform, **kwargs)
    return qmatSum.view(qn_array[0].qn_dtype).view(qn)


def exp(qn1):
    # Exponetial calculation for quaternion numbers. Note the qn**2 is still not implemented
    coeff_real = np.exp(qn1['w'])
    coeff_imag_base = qn1.imag.norm
    coeff_imag = np.sin(coeff_imag_base) / coeff_imag_base
    temp_shape = qn1['w'].shape
    if not temp_shape:
        compactProduct = np.zeros([qn1['w'].size], dtype=qn1.qn_dtype)
    else:
        compactProduct = np.zeros([*temp_shape], dtype=qn1.qn_dtype)
    compactProduct = np.full_like(compactProduct, np.nan)
    compactProduct['w'] = coeff_real * np.cos(coeff_imag_base)
    compactProduct['x'] = qn1['x'] * coeff_imag
    compactProduct['y'] = qn1['y'] * coeff_imag
    compactProduct['z'] = qn1['z'] * coeff_imag
    return compactProduct.view(qn)


def qdot(qn1, qn2):
    # Return the dot product of two quaternion number (as real number ndarray object)
    return -(qn1 * qn2).realpart


def qcross(qn1, qn2):
    # Return the cross product of two quaternion number (as quaternion ndarray object)
    return (qn1 * qn2).imag


def anglebtw(qn1, qn2):
    # Calculate the angle between 3d vectors represented with two quaternions whose real part = 0
    return np.arcsin((qn1.normalize - qn2.normalize).norm / 2) * 2
    # return np.arccos(qdot(qn1,qn2)/(qn1.norm*qn2.norm)) # deprecated, too slow


def reflect(surf_normal, points):
    """
    Calculate the reflected 3d vectors representing with quaternions whose real part = 0

    :param surf_normal: normal vector for the reflection surface (quaternion)
    :param points: qn vectors or points to be reflected
    :return: reflected qn vectors/points
    """
    surf_normal /= surf_normal.norm
    return surf_normal * points * surf_normal


def reflect_matrix(surf_norm_vector):
    """

    :param surf_norm_vector: normal vector for the reflection surface (1 x 3 ndarray)
    :return: 4x4 ndarray matrix which perform reflection transformation
    """
    normtype = type(surf_norm_vector)
    if normtype == np.ndarray:
        surf_norm = qn(surf_norm_vector)
    elif normtype == qn:
        surf_norm = surf_norm_vector.imag.normalize  # The real part of the  orientation quaternion should always be 0
    else:
        raise Exception("Camera orientation should be a ndarray or a quaternion, instead its type is %s\n" % normtype)
    return surf_norm.sandwich_mat


def rotate(rot_axis, rot_point, rot_angle=None):
    """
    Perform 3D rotation
    Input:
        rot_axis: rotation axis (in quatennion ndarray form).
        rot_point: qn vectors or points to be rotated
        rot_angle (optional): if exist, it will update the qn number of the rot_axis
         with its value, if not applied, the rotation will be calculated only based on
         the rotation axis qn number
    Output:
        rotated qn vector/points
    """
    if rot_angle is not None:
        rot_axis = np.squeeze(exp(rot_angle / 2 * rot_axis.normalize))
    # rot_axis[np.isnan(rot_axis.norm)] *= 0
    return rot_axis * rot_point * rot_axis.conj


def rotation_matrix(rotation_axis, rot_angle=None):
    """

    :param rotation_axis:  rotation axis (1 x 3 ndarray)
    :param rot_angle: optional, real number defines the rotation angle
    :return:  4x4 ndarray matrix which perform rotation transformation
    """
    axistype = type(rotation_axis)
    if axistype == np.ndarray:
        rot_axis = qn(rotation_axis)
    elif axistype == qn:
        rot_axis = rotation_axis  # The real part of the  orientation quaternion should always be 0
    else:
        raise Exception('Camera orientation should be a ndarray or a quaternion, instead its type is %s\n' % axistype)
    if rot_angle is not None:
        rot_axis = np.squeeze(exp(rot_angle / 2 * rot_axis.normalize))
    return rot_axis.conj_sandwich_mat


def rotTo(fromQn, toQn):
    """
    Given the qn representing the current 3D orientation represented and the qn
    for the target 3D orientation, compute the rotation vectors to transform the
    current orienttaion to the target orientation
    Input:
        fromQn: current orientation qn vectors
        toQn:   target orientation qn vectors
    Output:
        the rotation quaternion number for the rotation transform
    """
    transVec = fromQn * toQn.normalize
    transVec = transVec.imag - transVec.real
    transVec += transVec.norm
    return transVec.normalize


def projection(surf_normal_qn, proj_pnt_qn, on_plane=True):
    """
    Computing the projected quaternion
    ------------
    :param  surf_normal_qn: normal vector of the projection surface (quaternion)
    :param  proj_pnt_qn: qn vectors to be projected
    :param  on_plane: If true, project points onto the surface defined by the normal vector, otherwise projected on to the vector
    :return:  projected qn vectors
    """
    if on_plane:
        return (proj_pnt_qn + reflect(surf_normal_qn, proj_pnt_qn)) / 2
    else:
        return (proj_pnt_qn - reflect(surf_normal_qn, proj_pnt_qn)) / 2


def projection_matrix(projection_normal, flat_output=True):
    """
    Calculate the orthogonal projection transformation
    ------------
    :param projection_normal: 1 x 3 ndarray or a quaternion number; the camera's pointing direction
    :param flat_output: boolean, optional; if True (default), the output transformation quternion number or matrix will project the target point to the xy planar
    :return: transformation matrix or quaternion number for the corresponding orthogonal projection
    """
    normaltype = type(projection_normal)
    if normaltype == np.ndarray:
        projection_normal = qn(projection_normal)
    elif normaltype == qn:
        pass
    else:
        raise Exception('Camera orientation should be a ndarray or a quaternion, instead its type is %s\n' % normaltype)

    if all(projection_normal.imagpart.flatten() == 0):
        raise Exception('Input projection normal vector is a zero vector')
    else:
        reflect_mat = reflect_matrix(projection_normal)
        projection_mat = (np.eye(4) + np.squeeze(reflect_mat)) / 2

        if flat_output:
            xynorm = qn(np.array([0, 0, 1]))  # The normal quaternion number for x-y planar
            if all(projection_normal.imagpart.flatten()[:2] == 0):
                backrot = rotTo(projection_normal, xynorm)
            else:
                projection_xy = np.copy(projection_normal).view(
                    qn)  # Intermediate quaternnion for rotate the projected result to the x-y planar
                projection_xy['z'] *= 0
                backrot = rotTo(projection_xy, xynorm) * rotTo(projection_normal, projection_xy)
            backrot_mat = rotation_matrix(backrot)
            return np.dot(np.squeeze(backrot_mat), projection_mat)
        else:
            return projection_mat


class SphereHelper:

    @staticmethod
    def getAzElLimitedMask(theta_low, theta_high, phi_low, phi_high, verts=None, theta=None, phi=None):
        if verts is not None:
            theta, phi, _ = SphereHelper.cart2sph(verts[:, 0], verts[:, 1], verts[:, 2])
        else:
            if theta is None or phi is None:
                raise Exception('If <verts> is undefined, func requires <theta> and <phi> to be specified')

        mask = np.zeros(verts.shape[0]).astype(bool)
        mask[(theta_low <= theta) & (theta <= theta_high)
             & (phi_low <= phi) & (phi <= phi_high)] = True

        return mask

    @staticmethod
    def cart2sph(x, y, z):
        hxy = np.hypot(x, y)
        r = np.hypot(hxy, z)
        el = np.arctan2(z, hxy)
        az = np.arctan2(y, x)
        return az, el, r

    @staticmethod
    def sph2cart(theta, phi, r):
        rcos_theta = r * np.cos(phi)
        x = rcos_theta * np.cos(theta)
        y = rcos_theta * np.sin(theta)
        z = r * np.sin(phi)
        return np.array([x, y, z])