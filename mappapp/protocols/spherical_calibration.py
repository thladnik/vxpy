"""
MappApp ./protocols/spherical.py - Protocols for calibration of spherical visual stimulation setup.
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

from mappapp.visuals.spherical.calibration import BlackWhiteCheckerboard, RegularMesh


class Calibration16x16(StaticProtocol):

    def __init__(self, *args):
        StaticProtocol.__init__(self, *args)

        self.add_phase(BlackWhiteCheckerboard,10 ** 6,
                       {BlackWhiteCheckerboard.u_elevation_sf: 16,
                        BlackWhiteCheckerboard.u_azimuth_sf: 16})


class CalibrationMultiple(StaticProtocol):

    def __init__(self, *args):
        StaticProtocol.__init__(self, *args)


        for num in range(5):

            self.add_phase(BlackWhiteCheckerboard,10,
                           {BlackWhiteCheckerboard.u_elevation_sf: 4 * (1 + num),
                            BlackWhiteCheckerboard.u_azimuth_sf: 4 * (1 + num)})

class RegularMesh16x16(StaticProtocol):

    def __init__(self, *args):
        StaticProtocol.__init__(self, *args)

        self.add_phase(RegularMesh, 10**6,
                       {RegularMesh.u_rows: 16,
                        RegularMesh.u_cols: 16})


class RegularMesh32x32(StaticProtocol):

    def __init__(self, *args):
        StaticProtocol.__init__(self, *args)

        self.add_phase(RegularMesh, 10**6,
                       {RegularMesh.u_rows: 32,
                        RegularMesh.u_cols: 32})

