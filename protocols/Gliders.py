"""
MappApp ./protocols/Gliders.py - Example protocol for demonstration.
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

from visuals.spherical.Glider import Glider2Point, Glider3Point

class Glider2PPos(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider2Point, dict(p_parity=1))

class Glider2PNeg(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider2Point, dict(p_parity=-1))

class Glider3PPosDiv(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider3Point, dict(p_parity=1, p_mode='div'))

class Glider3PNegDiv(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider3Point, dict(p_parity=-1, p_mode='div'))

class Glider3PPosConv(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider3Point, dict(p_parity=1, p_mode='conv'))


class Glider3PNegConv(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)
        self.addVisual(Glider3Point, dict(p_parity=-1, p_mode='conv'))