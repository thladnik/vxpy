"""
MappApp ./protocols/Example01.py - Example protocol for demonstration.
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

from visuals.Checkerboard import BlackWhiteCheckerboard
from visuals.Grating import BlackWhiteGrating

class Example01(StaticProtocol):

    _name = 'Example01'

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        for num in range(4):
            for v in range(5):

                self.newPhase(5)
                self.addVisual(BlackWhiteGrating,
                               dict(orientation='vertical',
                                    shape='rectangular',
                                    num=10+num*4,
                                    velocity=v+1)
                               )