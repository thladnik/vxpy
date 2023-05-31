import ctypes
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

import vxpy
from vxpy import configuration
from vxpy import config
from vxpy.configuration.config_manager.config_manager_display import DisplayManager
from vxpy.configuration.config_manager.config_manager_routines import RoutineManager
from vxpy.configuration.config_manager.config_manager_cameras import CameraManager


class ConfigurationWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)

        # Fix icon issues on Windows systems
        if sys.platform == 'win32':
            # Explicitly set app-id as suggested by https://stackoverflow.com/a/1552105
            appid = f'vxpy.application.{vxpy.get_version()}.configure'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        self.setWindowTitle('vxPy - Configuration')
        self.setWindowIcon(QtGui.QIcon(os.path.join(str(vxpy.__path__[0]), 'vxpy_icon_v3_config.svg')))
        self.createWinId()

        self.resize(1200, 800)
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        self.config_path_le = QtWidgets.QLineEdit(config.CONFIG_FILEPATH)
        self.config_path_le.setReadOnly(True)
        self.centralWidget().layout().addWidget(self.config_path_le, 0, 0)

        self.save_config_btn = QtWidgets.QPushButton('Save configuration')
        self.save_config_btn.clicked.connect(configuration.save_configuration)
        self.save_config_btn.setMaximumWidth(150)
        self.centralWidget().layout().addWidget(self.save_config_btn, 0, 1)

        self.tab_widget = QtWidgets.QTabWidget(self)
        self.centralWidget().layout().addWidget(self.tab_widget, 1, 0, 1, 2)

        # Routine manager
        self.routines = RoutineManager(self)
        self._add_tab(self.routines, 'Routines')

        # Camer manager
        self.cameras = CameraManager(self)
        self._add_tab(self.cameras, 'Cameras')

        # Display manager
        self.display = DisplayManager(self)
        self._add_tab(self.display, 'Display')

        self.show()

    def _add_tab(self, widget: QtWidgets.QWidget, name: str):
        self.tab_widget.addTab(widget, name)

