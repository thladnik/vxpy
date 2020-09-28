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

from visuals.spherical.Calibration import BlackWhiteCheckerboard, RegularMesh


class Calibration16x16(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)

        self.addVisual(BlackWhiteCheckerboard,
                       {BlackWhiteCheckerboard.u_rows : 16,
                        BlackWhiteCheckerboard.u_cols : 16})


class CalibrationMultiple(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)


        for num in range(5):
            self.newPhase(duration=10)

            self.addVisual(BlackWhiteCheckerboard,
                           {BlackWhiteCheckerboard.u_rows: 4 * (1 + num),
                            BlackWhiteCheckerboard.u_cols: 4 * (1 + num)})

class RegularMesh16x16(StaticProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.newPhase(duration=10**4)

        self.addVisual(RegularMesh,
                       {RegularMesh.u_rows : 16,
                        RegularMesh.u_cols : 16})