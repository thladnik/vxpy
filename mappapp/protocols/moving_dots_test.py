"""
MappApp ./protocols/spherical_gratings.py - Example protocol for demonstration.
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
from mappapp.core.protocol import StaticProtocol
from mappapp.visuals.planar.moving_dot.moving_dot import SingleMovingDot


class ShowMovingDotsInVaryingSizes(StaticProtocol):

    def __init__(self, *args):
        StaticProtocol.__init__(self, *args)

        for i in range(2):
            self.add_phase(SingleMovingDot, 3,
                           {SingleMovingDot.u_dot_ang_dia: 10. * (i + 1),
                            SingleMovingDot.u_dot_ang_velocity: 100.,
                            SingleMovingDot.u_vertical_offset: 2.,
                            SingleMovingDot.u_dot_lateral_offset: 20.})
