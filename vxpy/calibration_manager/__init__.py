import os.path
from typing import Union

import qdarktheme
from PySide6 import QtCore, QtGui, QtWidgets

from vxpy.definitions import *
from vxpy import config
from vxpy.calibration_manager import access
from vxpy.calibration_manager.display.display_calibration import DisplayCalibration
from vxpy.core import calibration
from vxpy.core import configuration


def run_calibration(calib_filepath: str = None):

    if access.application is None:
        _app = QtWidgets.QApplication.instance()
        if _app is None:
            _app = QtWidgets.QApplication([])
        access.application = _app

    # Set theme
    qdarktheme.setup_theme('dark')

    if access.window is None:
        access.window = CalibrationWindow(calib_filepath)
        access.window.setup_ui()

    access.application.exec()


class CalibrationWindow(QtWidgets.QMainWindow):

    sig_window_closed = QtCore.Signal()
    sig_reload_calibration = QtCore.Signal()

    def __init__(self, filepath: Union[None, str]):
        QtWidgets.QMainWindow.__init__(self)
        self.calibration_filepath = filepath

        if self.calibration_filepath is not None:
            calibration.load_calibration(filepath)

    def setup_ui(self):

        self.widget = QtWidgets.QWidget()
        self.setCentralWidget(self.widget)
        self.widget.setLayout(QtWidgets.QVBoxLayout())

        self.topbar = QtWidgets.QWidget()
        self.topbar.setLayout(QtWidgets.QHBoxLayout())
        self.widget.layout().addWidget(self.topbar)
        self.current_filepath_le = QtWidgets.QLineEdit()
        if self.calibration_filepath is not None:
            self.current_filepath_le.setText(self.calibration_filepath)
        self.current_filepath_le.setDisabled(True)
        self.topbar.layout().addWidget(self.current_filepath_le)
        self.save_calibration_btn = QtWidgets.QPushButton('Save to file')
        self.save_calibration_btn.clicked.connect(self.save_calibration)
        self.topbar.layout().addWidget(self.save_calibration_btn)

        self.display = DisplayCalibration(self)
        self.widget.layout().addWidget(self.display)

        self.resize(1400, 900)

        self.show()
        self.sig_reload_calibration.emit()

    def save_calibration(self):
        calibration.save_calibration(self.calibration_filepath)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.sig_window_closed.emit()
        event.accept()
