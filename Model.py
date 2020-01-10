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
from time import perf_counter

import Logging

class AbstractModel:
    ####
    ## Vertex buffer
    vertexBuffer : gloo.VertexBuffer
    # Should contain
    #   a_cart_pos   -> for spherical and planar models
    #   a_color      -> for spherical and planar models
    #   a_sph_pos    -> for spherical models
    #   a_channel    -> for spherical models

    ####
    ## Index buffer
    indexBuffer  : gloo.IndexBuffer

    def build(self):
        NotImplementedError('')


class SphereModel(AbstractModel):
    """Sphere model base class.
    All sphere models should inherit this class.
    """

    def __init__(self):
        self._built = False

    def build(self):
        if self._built:
            return

        t = perf_counter()
        ### Construct sphere and prepare it for spherical projection
        self._construct()
        self._prepareChannels()
        self._built = True

        Logging.logger.log(logging.INFO, 'Built SphereModel {}. Time {:.5f}s'.format(self.__class__, perf_counter()-t))

    def _construct(self):
        NotImplementedError('_construct of SphereModel class is not implemented in {}'.format(self.__class__.__name__))

    def _prepareChannels(self):
        NotImplementedError('_prepareChannels of SphereModel class is not implemented in {}'.format(self.__class__.__name__))
