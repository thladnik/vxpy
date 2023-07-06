from __future__ import annotations
import ctypes
import importlib
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

import vxpy
from vxpy import calibration
from vxpy import config
from vxpy.modules.display import Canvas

calibration_widget_import_paths = {
    'Spherical4ChannelProjectionTransform': 'vxpy.calibration.calib_manager.calib_manager_spherical_4_channel_projection.Spherical4ChannelProjectionCalibration',
    'Spherical4ScreenCylinderTransform': 'vxpy.calibration.calib_manager.calib_manager_spherical_4_screen_cylinder.Spherical4ScreenCylinderCalibration'
}


class CalibrationWindow(QtWidgets.QMainWindow):

    instance: CalibrationWindow = None
    # Create canvas
    canvas = Canvas(always_on_top=False)

    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)

        CalibrationWindow.instance = self

        # Fix icon issues on Windows systems
        if sys.platform == 'win32':
            # Explicitly set app-id as suggested by https://stackoverflow.com/a/1552105
            appid = f'vxpy.application.{vxpy.get_version()}.calibrate'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        self.setWindowTitle('vxPy - Calibration')
        self.setWindowIcon(QtGui.QIcon(os.path.join(str(vxpy.__path__[0]), 'vxpy_icon_v3_config.svg')))
        self.createWinId()

        self.resize(1200, 800)
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        self.calib_path_le = QtWidgets.QLineEdit(config.PATH_CALIBRATION)
        self.calib_path_le.setReadOnly(True)
        self.centralWidget().layout().addWidget(self.calib_path_le, 0, 0)

        self.save_calib_btn = QtWidgets.QPushButton('Save calibration')
        self.save_calib_btn.clicked.connect(calibration.save_calibration)
        self.save_calib_btn.setMaximumWidth(150)
        self.centralWidget().layout().addWidget(self.save_calib_btn, 0, 1)

        # Load calibration widget for configured DISPLAY_TRANSFORM
        import_path = calibration_widget_import_paths[config.DISPLAY_TRANSFORM]
        import_path_parts = import_path.split('.')
        _module = importlib.import_module('.'.join(import_path_parts[:-1]))
        _widget_cls = getattr(_module, import_path_parts[-1])

        # Create calibration widget
        self.calibration_widget = _widget_cls(parent=self)
        self.centralWidget().layout().addWidget(self.calibration_widget, 1, 0, 1, 2)

        # Create timer for canvas
        self.canvas_timer = QtCore.QTimer(self)
        self.canvas_timer.setInterval(20)
        self.canvas_timer.timeout.connect(self.trigger_on_draw)
        self.canvas_timer.start()

        self.update_canvas()

        self.show()

    @classmethod
    def update_canvas(cls):
        if cls.instance.canvas is None:
            print('ERROR: no canvas set')
            return
        cls.instance.canvas.clear()
        cls.instance.canvas.update_dimensions()
        cls.instance.canvas.update(None)

    def trigger_on_draw(self):
        self.canvas.on_draw(event=None)
