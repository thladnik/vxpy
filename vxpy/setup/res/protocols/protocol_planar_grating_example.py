"""
vxpy ./protocols/spherical_gratings.py - Example protocol for demonstration.
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

from vxpy.core.protocol import StaticPhasicProtocol

from visuals.planar_grating import BlackAndWhiteGrating as BWG

class ShowSFRange(StaticPhasicProtocol):

    def __init__(self, *args, **kwargs):
        StaticPhasicProtocol.__init__(self, *args, **kwargs)

        for sp in np.arange(1,4):
            self.add_phase(BWG, 5,
                           {BWG.p_direction: 'horizontal',
                            BWG.p_shape: 'rectangular',
                            BWG.u_spat_period: sp,
                            BWG.u_lin_velocity: 1})


class Stresstest(StaticPhasicProtocol):

    def __init__(self, *args, **kwargs):
        StaticPhasicProtocol.__init__(self, *args, **kwargs)

        for sp in np.arange(10.0, 30.0, 4.0):
            for v in np.arange(2, 10, 2):
                self.add_phase(BWG, 5,
                               {BWG.p_direction: 'horizontal',
                                BWG.p_shape: 'rectangular',
                                BWG.u_spat_period: sp,
                                BWG.u_lin_velocity: v})