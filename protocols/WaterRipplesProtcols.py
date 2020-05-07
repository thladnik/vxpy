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


from Protocol import StaticProtocol

from stimuli.WaterRipples import RipplesOnStaticBackground

class Example(StaticProtocol):

    _name = 'WRP_Example'

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        import numpy as np

        for depth in [0.7, 0.2]:
            for width in [0.01, 0.02]:
                for shape in ['normal', 'rect']:
                        for sign in [1, -1]:
                            for vel in [4.0, 8.0]:
                                self.newPhase(duration=10)
                                self.addVisual(RipplesOnStaticBackground,
                                               dict(u_mod_sign=sign,
                                                     u_mod_depth=depth,
                                                     u_mod_shape=shape,
                                                     u_mod_vel=vel,
                                                     u_mod_width=width,
                                                     u_mod_max_elev=-np.pi/8),
                                               duration=10)

class ElevationsExample(StaticProtocol):

    _name = 'WRP_ElevationsExample'

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        import numpy as np

        for depth in [0.7, 0.2]:
            for sign in [1, -1]:
                for elev in [np.pi/8, 0.0, -np.pi/8, -np.pi/4]:
                    self.newPhase(duration=10)
                    self.addVisual(RipplesOnStaticBackground,
                                   dict(u_mod_sign=sign,
                                         u_mod_depth=depth,
                                         u_mod_shape='normal',
                                         u_mod_vel=4.0,
                                         u_mod_width=0.03,
                                         u_mod_max_elev=elev),
                                   duration=10)

class UpperFlashesExample(StaticProtocol):

    _name = 'WRP_UpperFlashesExample'

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        import numpy as np


        for depth in [0.7, 0.2]:
                for vel in [1.0, 3.0, 5.0, 8.0]:
                    self.newPhase(duration=10)
                    self.addVisual(RipplesOnStaticBackground,
                                   dict(u_mod_sign=1,
                                         u_mod_depth=depth,
                                         u_mod_shape='normal',
                                         u_mod_vel=4.0,
                                         u_mod_width=0.03,
                                         u_mod_max_elev=0.0,
                                         u_upper_field_flash=1),
                                   duration=10)