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
from Definition import Display
from helper.Basic import Conversion
from process import GUI

if Definition.Env == Definition.EnvTypes.Dev:
    pass

class SphericalDisplaySettings(QtWidgets.QWidget):

    def __init__(self, _main):
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)
        self._main : GUI.Main = _main

        self._setupUi()

    def _setupUi(self):

        ## Setup widget
        self.setWindowTitle('Spherical display settings')
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
        self._dspn_x_pos.setValue(Config.Display[Display.pos_glob_x_pos])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('X-position'), 0, 0)
        self._grp_position.layout().addWidget(self._dspn_x_pos, 0, 1)
        # Y position
        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setMinimum(-1.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(.001)
        self._dspn_y_pos.setValue(Config.Display[Display.pos_glob_y_pos])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('Y-position'), 1, 0)
        self._grp_position.layout().addWidget(self._dspn_y_pos, 1, 1)
        # Distance from center
        self._dspn_vp_center_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_offset.setDecimals(3)
        self._dspn_vp_center_offset.setMinimum(-1.0)
        self._dspn_vp_center_offset.setMaximum(1.0)
        self._dspn_vp_center_offset.setSingleStep(.001)
        self._dspn_vp_center_offset.setValue(Config.Display[Display.pos_glob_radial_offset])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('Radial offset'), 2, 0)
        self._grp_position.layout().addWidget(self._dspn_vp_center_offset, 2, 1)

        ## Setup view
        self._grp_view = QtWidgets.QGroupBox('View')
        self._grp_view.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_view)
        # Elevation
        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setValue(Config.Display[Display.view_elev_angle])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 0, 0)
        self._grp_view.layout().addWidget(self._dspn_elev_angle, 0, 1)
        # Azimuth
        self._dspn_azim_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_azim_angle.setDecimals(1)
        self._dspn_azim_angle.setSingleStep(0.1)
        self._dspn_azim_angle.setMinimum(-90.0)
        self._dspn_azim_angle.setMaximum(90.0)
        self._dspn_azim_angle.setValue(Config.Display[Display.view_azim_angle])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Azimuth [deg]'), 1, 0)
        self._grp_view.layout().addWidget(self._dspn_azim_angle, 1, 1)
        # View distance(from origin of sphere)
        self._dspn_view_distance = QtWidgets.QDoubleSpinBox()
        self._dspn_view_distance.setDecimals(1)
        self._dspn_view_distance.setSingleStep(.1)
        self._dspn_view_distance.setValue(Config.Display[Display.view_distance])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Distance [a.u.]'), 2, 0)
        self._grp_view.layout().addWidget(self._dspn_view_distance, 2, 1)
        # View scale
        self._dspn_scale = QtWidgets.QDoubleSpinBox()
        self._dspn_scale.setDecimals(3)
        self._dspn_scale.setSingleStep(0.001)
        self._dspn_scale.setValue(Config.Display[Display.view_scale])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Scale [a.u.]'), 3, 0)
        self._grp_view.layout().addWidget(self._dspn_scale, 3, 1)

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

        ## Set timer for GUI settings update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(250)
        self._tmr_updateGUI.timeout.connect(self.updateGUI)
        self._tmr_updateGUI.start()

        ### Make connections between config and gui
        self._dspn_x_pos.valueChanged.connect(
            lambda: self.setConfig(Display.pos_glob_x_pos, self._dspn_x_pos.value()))
        self._dspn_y_pos.valueChanged.connect(
            lambda: self.setConfig(Display.pos_glob_y_pos, self._dspn_y_pos.value()))
        self._dspn_elev_angle.valueChanged.connect(
            lambda: self.setConfig(Display.view_elev_angle, self._dspn_elev_angle.value()))
        self._dspn_azim_angle.valueChanged.connect(
            lambda: self.setConfig(Display.view_azim_angle, self._dspn_azim_angle.value()))
        self._dspn_vp_center_offset.valueChanged.connect(
            lambda: self.setConfig(Display.pos_glob_radial_offset, self._dspn_vp_center_offset.value()))
        self._dspn_view_distance.valueChanged.connect(
            lambda: self.setConfig(Display.view_distance, self._dspn_view_distance.value()))
        self._spn_screen_id.valueChanged.connect(
            lambda: self.setConfig(Display.window_screen_id, self._spn_screen_id.value()))
        self._check_fullscreen.stateChanged.connect(
            lambda: self.setConfig(Display.window_fullscreen, Conversion.QtCheckstateToBool(self._check_fullscreen.checkState())))
        self._dspn_scale.valueChanged.connect(
            lambda: self.setConfig(Display.view_scale, self._dspn_scale.value()))

    def setConfig(self, name, val):
        Config.Display[name] = val

    def updateGUI(self):
        _config = Config.Display

        if Display.pos_glob_x_pos in _config \
                and _config[Display.pos_glob_x_pos] != self._dspn_x_pos.value():
            self._dspn_x_pos.setValue(_config[Display.pos_glob_x_pos])

        if Display.pos_glob_y_pos in _config \
                and _config[Display.pos_glob_y_pos] != self._dspn_y_pos.value():
            self._dspn_y_pos.setValue(_config[Display.pos_glob_y_pos])

        if Display.view_elev_angle in _config \
                and _config[Display.view_elev_angle] != self._dspn_elev_angle.value():
            self._dspn_elev_angle.setValue(_config[Display.view_elev_angle])

        if Display.view_azim_angle in _config \
                and _config[Display.view_azim_angle] != self._dspn_azim_angle.value():
            self._dspn_azim_angle.setValue(_config[Display.view_azim_angle])

        if Display.pos_glob_radial_offset in _config \
                and _config[Display.pos_glob_radial_offset] != self._dspn_vp_center_offset.value():
            self._dspn_vp_center_offset.setValue(_config[Display.pos_glob_radial_offset])

        if Display.view_distance in _config \
                and _config[Display.view_distance] != self._dspn_view_distance.value():
            self._dspn_view_distance.setValue(_config[Display.view_distance])

        if Display.view_scale in _config \
                and _config[Display.view_scale] != self._dspn_scale.value():
            self._dspn_scale.setValue(_config[Display.view_scale])

        if Display.window_screen_id in _config \
                and _config[Display.window_screen_id] != self._spn_screen_id.value():
            self._spn_screen_id.setValue(_config[Display.window_screen_id])

        if Display.pos_glob_x_pos in _config \
                and _config[Display.window_fullscreen] != \
                Conversion.QtCheckstateToBool(self._check_fullscreen.checkState()):
            self._check_fullscreen.setCheckState(
                Conversion.boolToQtCheckstate(_config[Display.window_fullscreen]))


class PlanarDisplaySettings(QtWidgets.QWidget):

    def __init__(self, _main):
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)
        self._main : GUI.Main = _main

        self._setupUi()

    def _setupUi(self):

        ## Setup widget
        self.setWindowTitle('Planar display settings')
        self.setLayout(QtWidgets.QVBoxLayout())




