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

# from mappapp.visuals.spherical.insta360_onex import Calibrated

class Insta360Protocol(StaticProtocol):

    _name = 'insta360'

    def __init__(self, *args, **kwargs):
        super(StaticProtocol, self).__init__(*args, **kwargs)
        self.newPhase(duration=10**4)
        self.addVisual(Calibrated, dict(filename='insta1_virtMapsConverted'))
