from __future__ import annotations
from typing import Union
from PySide6 import QtWidgets

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vxpy.calibration_manager import CalibrationWindow

application: Union[None, QtWidgets.QApplication] = None
window: Union[None, CalibrationWindow] = None
