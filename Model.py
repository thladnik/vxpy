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

    def __init__(self, shader_attributes : list = None):
        self.vertexBuffer : gloo.VertexBuffer = None
        self.indexBuffer  : gloo.IndexBuffer  = None
        self.indices      : np.ndarray        = None

        ### Set shader attributes
        self.activeAttributes = [('a_position', np.float32, 3)]
        if shader_attributes is not None:
            self.activeAttributes.extend(shader_attributes)

    @staticmethod
    def reshapeArray(ar):
        if len(ar.shape) == 2 and ar.shape[0] > ar.shape[1]:
            return ar
        return ar.T

    def addVertexAttribute(self, attribute):
        if isinstance(attribute, tuple) and len(attribute) == 3:
            self.activeAttributes.append(attribute)

    def setAttribute(self, attribute_name, data=None):
        if data is None:
            data = getattr(self, attribute_name)
        else:
            setattr(self, attribute_name, data)
        self.vertexBuffer[attribute_name] = AbstractModel.reshapeArray(data)

    def initVertexAttributes(self):
        for attribute in self.activeAttributes:
            if not(hasattr(self, attribute[0])):
                Logging.logger.log(logging.WARNING, 'Attribute {} not set on model {}'
                                   .format(str(attribute), self.__class__))
                return
            self.setAttribute(attribute[0])

    def createBuffers(self):
        if not(hasattr(self, 'a_position')):
            Logging.logger.log(logging.WARNING,
                               'Creation of vertex buffer failed in model {}. '
                               'a_position is not set on model.'.format(self.__class__))
            return

        ### Create vertex array
        vArray = np.zeros(AbstractModel.reshapeArray(getattr(self, 'a_position')).shape[0],
                          self.activeAttributes)

        ### Create vertex buffer
        self.vertexBuffer = vArray.view(gloo.VertexBuffer)

        ### Set attribute data
        self.initVertexAttributes()

        ### Create index buffer
        if self.indices is not None:
            self.indexBuffer = np.uint32(self.indices).view(gloo.IndexBuffer)

class SphereModel(AbstractModel):
    """Sphere model base class.
    All sphere models should inherit this class.
    """

    def __init__(self, **kwargs):
        AbstractModel.__init__(self, **kwargs)