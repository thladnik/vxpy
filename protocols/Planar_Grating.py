"""
MappApp ./protocols/Spherical_Gratings.py - Example protocol for demonstration.
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

import numpy as np

from Protocol import StaticProtocol

from visuals.planar.Grating import BlackAndWhiteGrating

class ShowSFRange(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)

        for sf in range(1,5):

            self.newPhase(10)
            self.addVisual(BlackAndWhiteGrating,
                           dict(u_direction='horizontal',
                                u_shape='rectangular',
                                u_spat_period=sf,
                                u_lin_velocity=0))


class Stresstest(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)

        for sp in np.arange(1.0, 20.0, 4.0):

            for v in range(10,11):
                self.newPhase(5)
                self.addVisual(BlackAndWhiteGrating,
                               dict(u_direction='horizontal',
                                    u_shape='rectangular',
                                    u_spat_period=sp,
                                    u_lin_velocity=v/10))