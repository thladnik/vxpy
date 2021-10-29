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

import numpy as np

from mappapp.core.protocol import StaticProtocol

from mappapp.visuals.planar.moving_dot.moving_dot import SingleMovingDot,SingleMoving2ndDot
from mappapp.visuals.planar.blank import Blank,Noise


class MovingDotsTestProtocol1(StaticProtocol):

    def __init__(self, *args, **kwargs):
        StaticProtocol.__init__(self, *args, **kwargs)

        # np.random.seed(20)
        # dot_sizes = []
        # for i in range(9):
        #     dot_sizes.append(np.random.permutation([2., 5., 10., 20.]))
        # dot_sizes = np.array(dot_sizes).flatten()

        dot_sizes = np.array([20., 2., 5., 10., 5., 10., 20., 2., 20., 5., 10., 2., 2.,
                              20., 5., 10., 5., 2., 10., 20., 2., 10., 5., 20., 20., 2.,
                              5., 10., 5., 10., 2., 20., 2., 5., 20., 10.])

        self.add_phase(Blank, 30,
                       {})
        for s in dot_sizes:
            self.add_phase(Blank, 4,
                           {})
            self.add_phase(SingleMovingDot, 4,
                           {SingleMovingDot.u_dot_ang_dia: s,
                            SingleMovingDot.u_vertical_offset: 0.,
                            SingleMovingDot.u_dot_lateral_offset: 15.,
                            SingleMovingDot.u_dot_ang_velocity: 42.})
        self.add_phase(Blank, 30,
                       {})


class MovingDotsTestProtocol_YZ1(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)

        np.random.seed(20)
        dot_sizes = []
        for i in range(9):
            dot_sizes.append(np.random.permutation([1., 3., 5., 10., 20.]))
        dot_sizes = np.array(dot_sizes).flatten()

        # dot_sizes = np.array([20., 2., 3., 5., 10.,
        #                       5., 10., 20., 3., 2.,
        #                       2., 20., 5., 10., 3.])

        # dot_sizes = np.array([20., 5., 10.,
        #                       5., 10., 20.,
        #                       20., 10., 5.])

        dot_sizes = np.array([3., 20.,  1.,  5., 10.,
                              10., 20.,  5.,  1.,  3.,
                              3., 10., 20., 1.,  5.])


        self.add_phase(Blank, 30,
                       {})
        for s in dot_sizes:
            self.add_phase(Blank, 7,
                           {})
            self.add_phase(SingleMovingDot, 12,
                           {SingleMovingDot.u_dot_ang_dia: s,
                            SingleMovingDot.u_vertical_offset: 6.,
                            SingleMovingDot.u_dot_lateral_offset: 10.,
                            # SingleMovingDot.u_dot_ang_velocity: 7.8})
                            SingleMovingDot.u_dot_ang_velocity: 60})
        self.add_phase(Blank, 30,
                       {})

class Moving2ndDotsTest(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)

        np.random.seed(20)
        dot_sizes = []
        for i in range(9):
            dot_sizes.append(np.random.permutation([1., 3., 5., 10., 20.]))
        dot_sizes = np.array(dot_sizes).flatten()

        # dot_sizes = np.array([20., 2., 3., 5., 10.,
        #                       5., 10., 20., 3., 2.,
        #                       2., 20., 5., 10., 3.])

        # dot_sizes = np.array([20., 5., 10.,
        #                       5., 10., 20.,
        #                       20., 10., 5.])

        dot_sizes = np.array([3., 20.,  1.,  5., 10.,
                              10., 20.,  5.,  1.,  3.,
                              3., 10., 20., 1.,  5.])


        self.add_phase(Noise, 30,
                       {})
        for s in dot_sizes:
            self.add_phase(Noise, 7,
                           {})
            self.add_phase(SingleMoving2ndDot, 12,
                           {SingleMoving2ndDot.u_dot_ang_dia: s,
                            SingleMoving2ndDot.u_vertical_offset: 6.,
                            SingleMoving2ndDot.u_dot_lateral_offset: 10.,
                            SingleMoving2ndDot.u_dot_ang_velocity: 60})
        self.add_phase(Noise, 30,
                       {})