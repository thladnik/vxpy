"""
vxPy ./calib.py
Copyright (C) 2022 Tim Hladnik

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
from typing import List

PRESERVED_ORDER: List[str] = []

CALIB_DISP_WIN_SCREEN_ID: int = 0
CALIB_DISP_WIN_FULLSCREEN: bool = False
CALIB_DISP_WIN_SIZE_HEIGHT: int = 600
CALIB_DISP_WIN_SIZE_WIDTH: int = 600
CALIB_DISP_WIN_POS_X: int = 0
CALIB_DISP_WIN_POS_Y: int = 0

CALIB_DISP_GLOB_POS_X: float = 0.
CALIB_DISP_GLOB_POS_Y: float = 0.

CALIB_DISP_SPH_VIEW_AZIM_ORIENT: float = 0.
CALIB_DISP_SPH_VIEW_AZIM_ANGLE: List[float] = [0., 0., 0., 0.]
CALIB_DISP_SPH_VIEW_ELEV_ANGLE: List[float] = [0., 0., 0., 0.]
CALIB_DISP_SPH_VIEW_DISTANCE: List[float] = [5., 5., 5., 5.]
CALIB_DISP_SPH_VIEW_FOV: List[float] = [40., 40., 40., 40.]
CALIB_DISP_SPH_VIEW_SCALE: List[float] = [1., 1., 1., 1.]
CALIB_DISP_SPH_POS_RADIAL_OFFSET: List[float] = [.75, .75, .75, .75]
CALIB_DISP_SPH_POS_LATERAL_OFFSET: List[float] = [0., 0., 0., 0.]
CALIB_DISP_SPH_LAT_LUM_OFFSET: float = 0.25
CALIB_DISP_SPH_LAT_LUM_GRADIENT: float = 2.

CALIB_DISP_PLA_EXTENT_X: float = 1.
CALIB_DISP_PLA_EXTENT_Y: float = 1.
CALIB_DISP_PLA_SMALL_SIDE: float = 80.
