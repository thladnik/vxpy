"""
MappApp ./protocols/WaterRipplesProtocol.py - Example protocol for demonstration.
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


from Protocol import StaticStimulationProtocol

from stimuli.WaterRipples import RipplesOnStaticBackground

class Test(StaticStimulationProtocol):

    _name = 'WRP_Test'

    def __init__(self, _glWindow):
        StaticStimulationProtocol.__init__(self, _glWindow)
        import numpy as np

        for depth in [0.7, 0.2]:
            for width in [0.01, 0.02]:
                for shape in ['normal', 'rect']:
                        for sign in [1, -1]:
                            for vel in [4.0, 8.0]:
                                self.addStimulus(RipplesOnStaticBackground,
                                                 dict(u_mod_sign=sign,
                                                     u_mod_depth=depth,
                                                     u_mod_shape=shape,
                                                     u_mod_vel=vel,
                                                     u_mod_width=width,
                                                     u_mod_max_elev=-np.pi/8),
                                                 duration=10)
