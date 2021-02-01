"""
MappApp ./protocols/Spherical_Calibration.py - Protocols for calibration of spherical visual stimulation setup.
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

from core.protocol import StaticProtocol

from visuals.planar.Calibration import Checkerboard

class Checkerboard_2x2(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 2, Checkerboard.u_rows: 2})

class Checkerboard_3x3(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 3, Checkerboard.u_rows: 3})

class Checkerboard_4x4(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 4, Checkerboard.u_rows: 4})

class Checkerboard_6x6(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 6, Checkerboard.u_rows: 6})

class Checkerboard_8x8(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 8, Checkerboard.u_rows: 8})

class Checkerboard_16x16(StaticProtocol):

    def __init__(self, canvas):
        StaticProtocol.__init__(self, canvas)
        self.add_phase(Checkerboard, 10 ** 8,
                       {Checkerboard.u_cols: 16, Checkerboard.u_rows: 16})