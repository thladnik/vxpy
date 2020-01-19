"""
MappApp ./gui/DisplaySettings.py - GUI widget for adjustment of display settings.
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

from PyQt5 import QtCore, QtWidgets

import Config
import Definition
from Definition import DisplayConfig
from helper.Basic import Conversion
from process import GUI

if Definition.Env == Definition.EnvTypes.Dev:
    pass

class DisplaySettings(QtWidgets.QWidget):

    def __init__(self, _main):
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)
        self._main : GUI.Main = _main

        self._setupUi()


    def _setupUi(self):
        self.setMinimumSize(400, 400)

        ## Setup widget
        self.setWindowTitle('Display settings')
        self.setLayout(QtWidgets.QVBoxLayout())

        ## Setup position
        self._grp_position = QtWidgets.QGroupBox('Position')
        self._grp_position.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_position)
        # X Position
        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setMinimum(-1.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(.001)
        self._dspn_x_pos.setValue(Config.Display[DisplayConfig.float_pos_glob_x_pos])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('X-position'), 0, 0)
        self._grp_position.layout().addWidget(self._dspn_x_pos, 0, 1)
        # Y position
        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setMinimum(-1.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(.001)
        self._dspn_y_pos.setValue(Config.Display[DisplayConfig.float_pos_glob_y_pos])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('Y-position'), 1, 0)
        self._grp_position.layout().addWidget(self._dspn_y_pos, 1, 1)
        # Distance from center
        self._dspn_vp_center_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_offset.setDecimals(3)
        self._dspn_vp_center_offset.setMinimum(-1.0)
        self._dspn_vp_center_offset.setMaximum(1.0)
        self._dspn_vp_center_offset.setSingleStep(.001)
        self._dspn_vp_center_offset.setValue(Config.Display[DisplayConfig.float_pos_glob_radial_offset])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('Radial offset'), 2, 0)
        self._grp_position.layout().addWidget(self._dspn_vp_center_offset, 2, 1)

        ## Setup view
        self._grp_view = QtWidgets.QGroupBox('View')
        self._grp_view.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_view)
        # Elevation
        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._dspn_elev_angle.setValue(Config.Display[DisplayConfig.float_view_elev_angle])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 0, 0)
        self._grp_view.layout().addWidget(self._dspn_elev_angle, 0, 1)
        # Offset of view from axis towards origin of sphere
        self._dspn_view_axis_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_view_axis_offset.setSingleStep(.001)
        self._dspn_view_axis_offset.setValue(Config.Display[DisplayConfig.float_view_axis_offset])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Origin offset'), 1, 0)
        self._grp_view.layout().addWidget(self._dspn_view_axis_offset, 1, 1)
        # Distance from origin of sphere
        self._dspn_view_origin_distance = QtWidgets.QDoubleSpinBox()
        self._dspn_view_origin_distance.setSingleStep(.01)
        self._dspn_view_origin_distance.setValue(Config.Display[DisplayConfig.float_view_origin_distance])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Origin distance'), 2, 0)
        self._grp_view.layout().addWidget(self._dspn_view_origin_distance, 2, 1)
        # Field of view
        self._dspn_fov = QtWidgets.QDoubleSpinBox()
        self._dspn_fov.setSingleStep(0.01)
        self._dspn_fov.setValue(Config.Display[DisplayConfig.float_view_fov])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('FOV [deg]'), 3, 0)
        self._grp_view.layout().addWidget(self._dspn_fov, 3, 1)
        ## Setup display
        self._grp_disp = QtWidgets.QGroupBox('Display')
        self._grp_disp.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_disp)
        # Screen ID
        self._spn_screen_id = QtWidgets.QSpinBox()
        self._grp_disp.layout().addWidget(QtWidgets.QLabel('Screen'), 0, 0)
        self._grp_disp.layout().addWidget(self._spn_screen_id, 0, 1)
        # Use fullscreen
        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setTristate(False)
        self._grp_disp.layout().addWidget(self._check_fullscreen, 0, 2)

        ##
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(250)
        self._tmr_updateGUI.timeout.connect(self.updateGUI)
        self._tmr_updateGUI.start()

        ### Make connections between config and gui
        self._dspn_x_pos.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_pos_glob_x_pos, self._dspn_x_pos.value()))
        self._dspn_y_pos.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_pos_glob_y_pos, self._dspn_y_pos.value()))
        self._dspn_elev_angle.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_view_elev_angle, self._dspn_elev_angle.value()))
        self._dspn_view_axis_offset.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_view_axis_offset, self._dspn_view_axis_offset.value()))
        self._dspn_vp_center_offset.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_pos_glob_radial_offset, self._dspn_vp_center_offset.value()))
        self._dspn_view_origin_distance.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_view_origin_distance, self._dspn_view_origin_distance.value()))
        self._check_fullscreen.stateChanged.connect(
            lambda: self.setConfig(DisplayConfig.bool_window_fullscreen, Conversion.QtCheckstateToBool(self._check_fullscreen.checkState())))
        self._dspn_fov.valueChanged.connect(
            lambda: self.setConfig(DisplayConfig.float_view_fov, self._dspn_fov.value()))

    def setConfig(self, name, val):
        Config.Display[name] = val

    def updateGUI(self):
        _config = Config.Display

        if DisplayConfig.float_pos_glob_x_pos in _config \
                and _config[DisplayConfig.float_pos_glob_x_pos] != self._dspn_x_pos.value():
            self._dspn_x_pos.setValue(_config[DisplayConfig.float_pos_glob_x_pos])

        if DisplayConfig.float_pos_glob_y_pos in _config \
                and _config[DisplayConfig.float_pos_glob_y_pos] != self._dspn_y_pos.value():
            self._dspn_y_pos.setValue(_config[DisplayConfig.float_pos_glob_y_pos])

        if DisplayConfig.float_view_elev_angle in _config \
                and _config[DisplayConfig.float_view_elev_angle] != self._dspn_elev_angle.value():
            self._dspn_elev_angle.setValue(_config[DisplayConfig.float_view_elev_angle])

        if DisplayConfig.float_view_axis_offset in _config \
                and _config[DisplayConfig.float_view_axis_offset] != self._dspn_view_axis_offset.value():
            self._dspn_view_axis_offset.setValue(_config[DisplayConfig.float_view_axis_offset])

        if DisplayConfig.float_pos_glob_radial_offset in _config \
                and _config[DisplayConfig.float_pos_glob_radial_offset] != self._dspn_vp_center_offset.value():
            self._dspn_vp_center_offset.setValue(_config[DisplayConfig.float_pos_glob_radial_offset])

        if DisplayConfig.float_view_origin_distance in _config \
                and _config[DisplayConfig.float_view_origin_distance] != self._dspn_view_origin_distance.value():
            self._dspn_view_origin_distance.setValue(_config[DisplayConfig.float_view_origin_distance])

        if DisplayConfig.float_view_fov in _config \
                and _config[DisplayConfig.float_view_fov] != self._dspn_fov.value():
            self._dspn_fov.setValue(_config[DisplayConfig.float_view_fov])

        if DisplayConfig.int_window_screen_id in _config \
                and _config[DisplayConfig.int_window_screen_id] != self._spn_screen_id.value():
            self._spn_screen_id.setValue(_config[DisplayConfig.int_window_screen_id])

        if DisplayConfig.float_pos_glob_x_pos in _config \
                and _config[DisplayConfig.bool_window_fullscreen] != \
                Conversion.QtCheckstateToBool(self._check_fullscreen.checkState()):
            self._check_fullscreen.setCheckState(
                Conversion.boolToQtCheckstate(_config[DisplayConfig.bool_window_fullscreen]))




