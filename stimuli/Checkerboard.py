"""
MappApp ./stimuli/Checkerboard.py - Checkerboard stimuli
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

from glumpy import gl
import numpy as np

from Stimulus import SphericalStimulus
from models import UVSphere

class BlackWhiteCheckerboard(SphericalStimulus):

    _model = UVSphere.UVSphere(theta_lvls=60, phi_lvls=30)
    _fragment_shader = 'f_checkerboard.shader'

    def __init__(self, protocol, display, rows, cols):
        """Black-and-white checkerboard for calibration.

        :param protocol: protocol of which stimulus is currently part of
        :param rows: number of rows on checkerboard
        :param cols: number of columns on checkerboard
        """
        super().__init__(protocol=protocol, display=display)

        self._model.build()
        self._createProgram()

        self.update(cols=cols, rows=rows)

    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.protocol.program['u_checker_cols'] = cols

        if rows is not None and rows > 0:
            self.protocol.program['u_checker_rows'] = rows


####
# TODO: Mapped Checkerboard version (not working yet)

class BlackWhiteCheckerboard_mapped(SphericalStimulus):
    _sphere_model = 'UVSphere>UVSphere_80thetas_40phis'
    _fragment_shader = 'f_uvmap.shader'  # TODO: write f_uvmap.shader

    def __init__(self, protocol, rows, cols):
        """Black-and-white checkerboard for calibration.

        :param protocol: protocol of which stimulus is currently part of
        :param rows: number of rows on checkerboard
        :param cols: number of columns on checkerboard
        """
        super().__init__(protocol)

        self.update(cols=cols, rows=rows)

    def draw_update(self):
        cols = self.protocol.program['u_checker_cols']
        rows = self.protocol.program['u_checker_rows']

        z = np.repeat(np.arange(0., 50*np.pi*2, np.pi/5).reshape((-1,1)), 500, axis=-1)
        tex = np.sin(z/50*rows/2) * np.sin(z.T/50*cols/2)
        tex = (tex > 0.).astype(np.float)
        self.texture = tex

    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.protocol.program['u_checker_cols'] = cols

        if rows is not None and rows > 0:
            self.protocol.program['u_checker_rows'] = rows
