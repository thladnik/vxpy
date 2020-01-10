"""
MappApp ./stimuli/Grating.py - Grating stimuli
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
from time import perf_counter

from Stimulus import SphericalStimulus
from models import UVSphere
import Logging


class BlackWhiteGrating(SphericalStimulus):

    _fragment_shader = 'f_grating.shader'
    _model = UVSphere.UVSphere(theta_lvls=70, phi_lvls=35)

    def __init__(self, protocol, display, orientation, shape, velocity, num):
        """
        :param protocol: protocol of which stimulus is currently part of

        :param orientation: orientation of grating; either 'vertical' or 'horizontal'
        :param shape: shape of underlying function; either 'rectangular' or 'sinusoidal'
        :param velocity:
        :param num:
        """
        SphericalStimulus.__init__(self, protocol=protocol, display=display)

        self._model.build()
        self._createProgram()

        self.update(shape=shape, orientation=orientation, velocity=velocity, num=num)

    def parameters(self):
        return dict(orientation = self.protocol.program['u_orientation'],
                    shape = self.protocol.program['u_shape'],
                    velocity = self.protocol.program['u_velocity'],
                    num = self.protocol.program['u_stripes_num']
                    )

    def update(self, shape=None, orientation=None, velocity=None, num=None):

        if shape is not None:
            self._setShape(shape)

        if orientation is not None:
            self._setOrientation(orientation)

        if velocity is not None:
            self.program['u_velocity'] = velocity

        if num is not None and num > 0:
            self.program['u_stripes_num'] = num

    def _setShape(self, shape):
        if shape == 'rectangular':
            self.program['u_shape'] = 1
        elif shape == 'sinusoidal':
            self.program['u_shape'] = 2

    def _setOrientation(self, orientation):
        if orientation == 'vertical':
            self.program['u_orientation'] = 1
        elif orientation == 'horizontal':
            self.program['u_orientation'] = 2