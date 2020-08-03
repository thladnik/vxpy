"""
MappApp ./protocols/Calibration.py - Protocols for calibration of spherical visual stimulation setup.
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

from visuals.planar.Calibration import Checkerboard

class Checkerboard_1Period(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period : 1})

class Checkerboard_1_5Period(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period : 1.5})

class Checkerboard_2Periods(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period : 2})

class Checkerboard_3Periods(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period: 3})

class Checkerboard_4Periods(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period: 4})

class Checkerboard_8Periods(StaticProtocol):

    def __init__(self, _glWindow):
        StaticProtocol.__init__(self, _glWindow)
        self.newPhase(10 ** 8)
        self.addVisual(Checkerboard, {Checkerboard.u_spat_period: 8})