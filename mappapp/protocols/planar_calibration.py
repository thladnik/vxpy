"""
MappApp ./protocols/spherical_calibration.py - Protocols for calibration of spherical visual stimulation setup.
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

from mappapp.visuals.planar.calibration import Sinusoid2d

class Checkerboard_sp10xsp10(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 10, Sinusoid2d.u_sf_vertical: 1. / 10, Sinusoid2d.u_checker_pattern: True})

class Checkerboard_sp20xsp20(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 20, Sinusoid2d.u_sf_vertical: 1. / 20, Sinusoid2d.u_checker_pattern: True})

class Checkerboard_sp20xsp40(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 20, Sinusoid2d.u_sf_vertical: 1. / 40, Sinusoid2d.u_checker_pattern: True})

class Checkerboard_sp40xsp40(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 40, Sinusoid2d.u_sf_vertical: 1. / 40, Sinusoid2d.u_checker_pattern: True})

class Checkerboard_sp80xsp40(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 80, Sinusoid2d.u_sf_vertical: 1. / 40, Sinusoid2d.u_checker_pattern: True})

class Checkerboard_sp80xsp80(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 80, Sinusoid2d.u_sf_vertical: 1. / 80, Sinusoid2d.u_checker_pattern: True})


class Sinusoid2d_sp10xsp10(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 10, Sinusoid2d.u_sf_vertical: 1. / 10, Sinusoid2d.u_checker_pattern: False})

class Sinusoid2d_sp20xsp20(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Sinusoid2d,10 ** 8,
                       {Sinusoid2d.u_sf_horizontal: 1. / 20, Sinusoid2d.u_sf_vertical: 1. / 20, Sinusoid2d.u_checker_pattern: False})