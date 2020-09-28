"""
MappApp ./Model.py - Model base classes.
Copyright (C) 2020 Tim Hladnik

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
import logging
from glumpy import gloo
import numpy as np

import Logging

class AbstractModel:

    def __init__(self, **kwargs):
        self.vertexBuffer : gloo.VertexBuffer = None
        self.indexBuffer  : gloo.IndexBuffer  = None
        self.indices      : np.ndarray        = None

        self._built = False

        ### Set default a_position attribute
        self.activeAttributes = [('a_position', np.float32, 3)]
        self.a_position : np.ndarray = None

    @staticmethod
    def reshapeArray(ar):
        if len(ar.shape) == 2 and ar.shape[0] > ar.shape[1]:
            return ar
        return ar.T

    def isBuilt(self):
        return self._built

    def addAttribute(self, attribute):
        if self.isBuilt():
            return
        if isinstance(attribute, tuple) and len(attribute) == 3:
            self.activeAttributes.append(attribute)

    def createBuffers(self):
        if self.isBuilt():
            return
        if self.a_position is None:
            Logging.logger.log_display(logging.WARNING,
                               'Creation of vertex buffer failed in model {}. '
                               'a_position is not set on model.'.format(self.__class__))
            return

        ### Create vertex array
        vArray = np.zeros(AbstractModel.reshapeArray(self.a_position).shape[0], self.activeAttributes)

        ### Create vertex buffer
        self.vertexBuffer = vArray.view(gloo.VertexBuffer)

        ### Set attribute data
        for attribute in self.activeAttributes:
            if not(hasattr(self, attribute[0])):
                Logging.logger.log_display(logging.WARNING, 'Attribute {} not set on model {}'
                                           .format(str(attribute), self.__class__))
                continue
            self.vertexBuffer[attribute[0]] = AbstractModel.reshapeArray(getattr(self, attribute[0]))

        ### Create index buffer
        if self.indices is not None:
            self.indexBuffer = np.uint32(self.indices).view(gloo.IndexBuffer)

        self._built = True

class SphereModel(AbstractModel):
    """Sphere model base class.
    All sphere models should inherit this class.
    """

    def __init__(self, **kwargs):
        AbstractModel.__init__(self, **kwargs)

    def setTextureCoords(self, type='uv_standard'):
        if self.isBuilt():
            return

        texcoord = list()

        poss = AbstractModel.reshapeArray(self.a_position)
        if type == 'uv_standard':
            for i in range(poss.shape[0]):
                pos = poss[i, :]
                texcoord.append([0.5 + np.arctan2(pos[1], pos[0]) / (2 * np.pi),
                                 0.5 + np.arcsin(pos[2]) / np.pi])
        elif type == 'uv_mercator':
            pass

        if bool(texcoord):
            self.addAttribute(('a_texcoord', np.float32, 2))
            self.a_texcoord = np.array(texcoord)


class PlaneModel(AbstractModel):

    def __init__(self, **kwargs):
        AbstractModel.__init__(self, **kwargs)
