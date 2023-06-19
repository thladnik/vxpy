"""Visual transform calibration module
"""
from typing import List

PRESERVED_ORDER: List[str] = []
CALIB_FILEPATH: str = ''

CALIB_DISP_GLOB_POS_X: float = 0.
CALIB_DISP_GLOB_POS_Y: float = 0.

# vxpy.core.transform.Spherical4ChannelProjectionTransform
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

# vxpy.core.transform.PlanarTransform
CALIB_DISP_PLA_EXTENT_X: float = 1.
CALIB_DISP_PLA_EXTENT_Y: float = 1.
CALIB_DISP_PLA_SMALL_SIDE: float = 80.  # mm

# vxpy.core.transform.Spherical4ScreenCylindricalTransform
CALIB_DISP_CYL_VIEW_AZIM_ORIENT: float = 0.0
CALIB_DISP_CYL_SIDE_WIDTH_MM: 100  # mm
CALIB_DISP_CYL_SCREEN_WIDTH_MM: 90  # mm
CALIB_DISP_CYL_SCREEN_HEIGHT_MM: 60  # mm
CALIB_DISP_CYL_CENTER_X_OFFSET: 0  # mm
CALIB_DISP_CYL_CENTER_Y_OFFSET: 0  # mm
CALIB_DISP_CYL_CENTER_Z_OFFSET: 0  # mm
