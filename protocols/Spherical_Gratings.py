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

from visuals.spherical.Grating import BlackWhiteGrating as BWG


class StaticGratingDemo(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        for sp in np.arange(10,50,10):

            self.newPhase(5)
            self.addVisual(BWG,
                           {BWG.u_shape: 'vertical',
                            BWG.u_direction:'horizontal',
                            BWG.u_ang_velocity:0,
                            BWG.u_spat_period:sp}
                           )

class MovingGratingDemo(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        for sp in np.arange(10,50,10):
            for v in np.arange(10,50,10):

                self.newPhase(5)
                self.addVisual(BWG,
                               {BWG.u_shape: 'vertical',
                                BWG.u_direction:'horizontal',
                                BWG.u_ang_velocity:v,
                                BWG.u_spat_period:sp}
                               )