"""
MappApp ./gui/Controls.py - GUI widget for selection and execution of stimulation protocols.
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
import Def
from helper.Basic import Conversion
import IPC
from process import Controller, Display, GUI


class DisplaySettingsGlobal(QtWidgets.QGroupBox):

    def __init__(self):
        QtWidgets.QGroupBox.__init__(self, 'Global')

        self.setLayout(QtWidgets.QGridLayout())

        # Reset button
        self.btn_reset = QtWidgets.QPushButton('RESET')
        #self.btn_reset.
        self.layout().addWidget(self.btn_reset, 0, 2, 4, 1)

        # Window x pos
        self.spn_win_x = QtWidgets.QSpinBox()
        self.spn_win_x.setMinimum(1)
        self.spn_win_x.setMaximum(9999)
        self.spn_win_x.setSingleStep(1)
        self.spn_win_x.setValue(Config.Display[Def.DisplayCfg.window_pos_x])
        self.layout().addWidget(QtWidgets.QLabel('Window x-Position'), 0, 0)
        self.layout().addWidget(self.spn_win_x, 0, 1)

        # Window y pos
        self.spn_win_y = QtWidgets.QSpinBox()
        self.spn_win_y.setMinimum(1)
        self.spn_win_y.setMaximum(9999)
        self.spn_win_y.setSingleStep(1)
        self.spn_win_y.setValue(Config.Display[Def.DisplayCfg.window_pos_y])
        self.layout().addWidget(QtWidgets.QLabel('Window y-Position'), 1, 0)
        self.layout().addWidget(self.spn_win_y, 1, 1)

        # Window width
        self.spn_win_width = QtWidgets.QSpinBox()
        self.spn_win_width.setMinimum(1)
        self.spn_win_width.setMaximum(9999)
        self.spn_win_width.setSingleStep(1)
        self.spn_win_width.setValue(Config.Display[Def.DisplayCfg.window_width])
        self.layout().addWidget(QtWidgets.QLabel('Window width'), 20, 0)
        self.layout().addWidget(self.spn_win_width, 20, 1)

        # Window height
        self.spn_win_height = QtWidgets.QSpinBox()
        self.spn_win_height.setMinimum(1)
        self.spn_win_height.setMaximum(9999)
        self.spn_win_height.setSingleStep(1)
        self.spn_win_height.setValue(Config.Display[Def.DisplayCfg.window_height])
        self.layout().addWidget(QtWidgets.QLabel('Window height'), 21, 0)
        self.layout().addWidget(self.spn_win_height, 21, 1)

        # Screen ID
        self.spn_screen_id = QtWidgets.QSpinBox()
        self.layout().addWidget(QtWidgets.QLabel('Screen'), 30, 0)
        self.layout().addWidget(self.spn_screen_id, 30, 1)
        # Fullscreen toggle
        self.check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self.check_fullscreen.setTristate(False)
        self.layout().addWidget(self.check_fullscreen, 30, 2)

        # X Position
        self.dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_x_pos.setDecimals(3)
        self.dspn_x_pos.setMinimum(-1.0)
        self.dspn_x_pos.setMaximum(1.0)
        self.dspn_x_pos.setSingleStep(.001)
        self.dspn_x_pos.setValue(Config.Display[Def.DisplayCfg.glob_x_pos])
        self.layout().addWidget(QtWidgets.QLabel('X-position'), 40, 0)
        self.layout().addWidget(self.dspn_x_pos, 40, 1)

        # Y position
        self.dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_y_pos.setDecimals(3)
        self.dspn_y_pos.setMinimum(-1.0)
        self.dspn_y_pos.setMaximum(1.0)
        self.dspn_y_pos.setSingleStep(.001)
        self.dspn_y_pos.setValue(Config.Display[Def.DisplayCfg.glob_y_pos])
        self.layout().addWidget(QtWidgets.QLabel('Y-position'), 50, 0)
        self.layout().addWidget(self.dspn_y_pos, 50, 1)


        ### Connect
        self.spn_win_x.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_pos_x, self.spn_win_x.value())
        )
        self.spn_win_y.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_pos_y, self.spn_win_y.value())
        )
        self.spn_win_width.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_width, self.spn_win_width.value())
        )
        self.spn_win_height.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_height, self.spn_win_height.value())
        )
        self.dspn_x_pos.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.glob_x_pos, self.dspn_x_pos.value())
        )
        self.dspn_y_pos.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.glob_y_pos, self.dspn_y_pos.value())
        )
        self.spn_screen_id.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_screen_id, self.spn_screen_id.value())
        )
        self.check_fullscreen.stateChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.window_fullscreen,
                                   Conversion.QtCheckstateToBool(self.check_fullscreen.checkState()))
        )

        ### Set timer
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(250)
        self._tmr_updateGUI.timeout.connect(self.updateGUI)
        self._tmr_updateGUI.start()


    def setConfig(self, name, val):
        Config.Display[name] = val

        if name in [Def.DisplayCfg.window_screen_id, Def.DisplayCfg.window_fullscreen]:
            IPC.rpc(Def.Process.Controller, Controller.initializeProcess, Display)

        if name in [Def.DisplayCfg.window_width, Def.DisplayCfg.window_height,
                    Def.DisplayCfg.window_pos_x, Def.DisplayCfg.window_pos_y]:
            IPC.rpc(Display.name, Display.updateWindow)


    def updateGUI(self):
        dconf = Config.Display
        ddef = Def.DisplayCfg

        # Win x pos
        if dconf[ddef.window_pos_x] != self.spn_win_x.value():
            self.spn_win_x.setValue(dconf[ddef.window_pos_x])
        # Win y pos
        if dconf[ddef.window_pos_y] != self.spn_win_y.value():
            self.spn_win_y.setValue(dconf[ddef.window_pos_y])

        # Win width
        if dconf[ddef.window_width] != self.spn_win_width.value():
            self.spn_win_width.setValue(dconf[ddef.window_width])
        # Win height
        if dconf[ddef.window_height] != self.spn_win_height.value():
            self.spn_win_height.setValue(dconf[ddef.window_height])

        # X pos
        if dconf[ddef.glob_x_pos] != self.dspn_x_pos.value():
            self.dspn_x_pos.setValue(dconf[ddef.glob_x_pos])

        # Y pos
        if dconf[ddef.glob_y_pos] != self.dspn_y_pos.value():
            self.dspn_y_pos.setValue(dconf[ddef.glob_y_pos])

        #### Screen ID
        if dconf[ddef.window_screen_id] != self.spn_screen_id.value():
            self.spn_screen_id.setValue(dconf[ddef.window_screen_id])

        ### Fullscreen toggle
        if dconf[ddef.window_fullscreen] != \
                Conversion.QtCheckstateToBool(self.check_fullscreen.checkState()):
            self.check_fullscreen.setCheckState(
                Conversion.boolToQtCheckstate(dconf[ddef.window_fullscreen]))


class SphericalDisplaySettings(QtWidgets.QWidget):

    def __init__(self, _main):
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)
        self._main : GUI.Main = _main

        self._setupUi()

    def _setupUi(self):

        ## Setup widget
        self.setWindowTitle('Spherical display settings')
        self.setLayout(QtWidgets.QVBoxLayout())

        ########
        ### Global display settings (apply for all types of visuals)
        self.grp_global = DisplaySettingsGlobal()
        self.layout().addWidget(self.grp_global)

        ########
        ### Sphere-specific display settings
        ## Radial position
        self.grp_position = QtWidgets.QGroupBox('Position')
        self.grp_position.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_position)
        # Distance from center
        self._dspn_vp_center_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_offset.setDecimals(3)
        self._dspn_vp_center_offset.setMinimum(-1.0)
        self._dspn_vp_center_offset.setMaximum(1.0)
        self._dspn_vp_center_offset.setSingleStep(.001)
        self._dspn_vp_center_offset.setValue(Config.Display[Def.DisplayCfg.sph_pos_glob_radial_offset])
        self.grp_position.layout().addWidget(QtWidgets.QLabel('Radial offset'), 2, 0)
        self.grp_position.layout().addWidget(self._dspn_vp_center_offset, 2, 1)

        ## View
        self.grp_view = QtWidgets.QGroupBox('View')
        self.grp_view.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_view)
        # Elevation
        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setValue(Config.Display[Def.DisplayCfg.sph_view_elev_angle])
        self.grp_view.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 0, 0)
        self.grp_view.layout().addWidget(self._dspn_elev_angle, 0, 1)
        # Azimuth
        self._dspn_azim_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_azim_angle.setDecimals(1)
        self._dspn_azim_angle.setSingleStep(0.1)
        self._dspn_azim_angle.setMinimum(-90.0)
        self._dspn_azim_angle.setMaximum(90.0)
        self._dspn_azim_angle.setValue(Config.Display[Def.DisplayCfg.sph_view_azim_angle])
        self.grp_view.layout().addWidget(QtWidgets.QLabel('Azimuth [deg]'), 1, 0)
        self.grp_view.layout().addWidget(self._dspn_azim_angle, 1, 1)
        # View distance(from origin of sphere)
        self._dspn_view_distance = QtWidgets.QDoubleSpinBox()
        self._dspn_view_distance.setDecimals(1)
        self._dspn_view_distance.setSingleStep(.1)
        self._dspn_view_distance.setValue(Config.Display[Def.DisplayCfg.sph_view_distance])
        self.grp_view.layout().addWidget(QtWidgets.QLabel('Distance [a.u.]'), 2, 0)
        self.grp_view.layout().addWidget(self._dspn_view_distance, 2, 1)
        # View scale
        self._dspn_scale = QtWidgets.QDoubleSpinBox()
        self._dspn_scale.setDecimals(3)
        self._dspn_scale.setSingleStep(0.001)
        self._dspn_scale.setValue(Config.Display[Def.DisplayCfg.sph_view_scale])
        self.grp_view.layout().addWidget(QtWidgets.QLabel('Scale [a.u.]'), 3, 0)
        self.grp_view.layout().addWidget(self._dspn_scale, 3, 1)

        ## Set timer for GUI settings update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(250)
        self._tmr_updateGUI.timeout.connect(self.updateGUI)
        self._tmr_updateGUI.start()

        ### Make connections between config and gui
        self._dspn_elev_angle.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.sph_view_elev_angle, self._dspn_elev_angle.value()))
        self._dspn_azim_angle.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.sph_view_azim_angle, self._dspn_azim_angle.value()))
        self._dspn_vp_center_offset.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.sph_pos_glob_radial_offset, self._dspn_vp_center_offset.value()))
        self._dspn_view_distance.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.sph_view_distance, self._dspn_view_distance.value()))
        self._dspn_scale.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.sph_view_scale, self._dspn_scale.value()))

    def setConfig(self, name, val):
        Config.Display[name] = val

    def updateGUI(self):
        _config = Config.Display

        if Def.DisplayCfg.sph_view_elev_angle in _config \
                and _config[Def.DisplayCfg.sph_view_elev_angle] != self._dspn_elev_angle.value():
            self._dspn_elev_angle.setValue(_config[Def.DisplayCfg.sph_view_elev_angle])

        if Def.DisplayCfg.sph_view_azim_angle in _config \
                and _config[Def.DisplayCfg.sph_view_azim_angle] != self._dspn_azim_angle.value():
            self._dspn_azim_angle.setValue(_config[Def.DisplayCfg.sph_view_azim_angle])

        if Def.DisplayCfg.sph_pos_glob_radial_offset in _config \
                and _config[Def.DisplayCfg.sph_pos_glob_radial_offset] != self._dspn_vp_center_offset.value():
            self._dspn_vp_center_offset.setValue(_config[Def.DisplayCfg.sph_pos_glob_radial_offset])

        if Def.DisplayCfg.sph_view_distance in _config \
                and _config[Def.DisplayCfg.sph_view_distance] != self._dspn_view_distance.value():
            self._dspn_view_distance.setValue(_config[Def.DisplayCfg.sph_view_distance])

        if Def.DisplayCfg.sph_view_scale in _config \
                and _config[Def.DisplayCfg.sph_view_scale] != self._dspn_scale.value():
            self._dspn_scale.setValue(_config[Def.DisplayCfg.sph_view_scale])


class PlanarDisplaySettings(QtWidgets.QWidget):

    def __init__(self, _main):
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)
        self._main : GUI.Main = _main

        self._setupUi()

    def _setupUi(self):

        self.setLayout(QtWidgets.QVBoxLayout())

        ########
        ### Global display settings (apply for all types of visuals)
        self.grp_global = DisplaySettingsGlobal()
        self.layout().addWidget(self.grp_global)

        ########
        ### Plane-specific display settings
        ## Position
        self.grp_extents = QtWidgets.QGroupBox('Extents')
        self.grp_extents.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_extents)

        # X extent
        self.grp_extents.dspn_x_extent = QtWidgets.QDoubleSpinBox()
        self.grp_extents.dspn_x_extent.setDecimals(3)
        self.grp_extents.dspn_x_extent.setMinimum(0.0)
        self.grp_extents.dspn_x_extent.setSingleStep(.001)
        self.grp_extents.dspn_x_extent.setValue(Config.Display[Def.DisplayCfg.pla_xextent])
        self.grp_extents.layout().addWidget(QtWidgets.QLabel('X-Extent [rel]'), 0, 0)
        self.grp_extents.layout().addWidget(self.grp_extents.dspn_x_extent, 0, 1)
        # Y extent
        self.grp_extents.dspn_y_extent = QtWidgets.QDoubleSpinBox()
        self.grp_extents.dspn_y_extent.setDecimals(3)
        self.grp_extents.dspn_y_extent.setMinimum(0.0)
        self.grp_extents.dspn_y_extent.setSingleStep(.001)
        self.grp_extents.dspn_y_extent.setValue(Config.Display[Def.DisplayCfg.pla_yextent])
        self.grp_extents.layout().addWidget(QtWidgets.QLabel('Y-Extent [rel]'), 1, 0)
        self.grp_extents.layout().addWidget(self.grp_extents.dspn_y_extent, 1, 1)
        # Small side dimensions
        self.grp_extents.dspn_small_side = QtWidgets.QDoubleSpinBox()
        self.grp_extents.dspn_small_side.setDecimals(3)
        self.grp_extents.dspn_small_side.setSingleStep(.001)
        self.grp_extents.dspn_small_side.setValue(Config.Display[Def.DisplayCfg.pla_small_side])
        self.grp_extents.layout().addWidget(QtWidgets.QLabel('Small side [mm]'), 2, 0)
        self.grp_extents.layout().addWidget(self.grp_extents.dspn_small_side, 2, 1)

        ### Connect
        self.grp_extents.dspn_x_extent.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.pla_xextent, self.grp_extents.dspn_x_extent.value()))
        self.grp_extents.dspn_y_extent.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.pla_yextent, self.grp_extents.dspn_y_extent.value()))
        self.grp_extents.dspn_small_side.valueChanged.connect(
            lambda: self.setConfig(Def.DisplayCfg.pla_small_side, self.grp_extents.dspn_small_side.value()))


        ### Set timer for GUI settings update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(250)
        self._tmr_updateGUI.timeout.connect(self.updateGUI)
        self._tmr_updateGUI.start()

    def setConfig(self, name, val):
        Config.Display[name] = val

    def updateGUI(self):
        _config = Config.Display

        if _config[Def.DisplayCfg.pla_xextent] != self.grp_extents.dspn_x_extent.value():
            self.grp_extents.dspn_x_extent.setValue(_config[Def.DisplayCfg.pla_xextent])

        if _config[Def.DisplayCfg.pla_yextent] != self.grp_extents.dspn_y_extent.value():
            self.grp_extents.dspn_x_extent.setValue(_config[Def.DisplayCfg.pla_yextent])

        if _config[Def.DisplayCfg.pla_small_side] != self.grp_extents.dspn_small_side.value():
            self.grp_extents.dspn_small_side.setValue(_config[Def.DisplayCfg.pla_small_side])

class Camera(QtWidgets.QWidget):

    def __init__(self, _main, *args, **kwargs):
        self.main = _main
        QtWidgets.QWidget.__init__(self, *args, parent=_main, **kwargs)

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QVBoxLayout())

        ### Set camera property dials
        self._gb_properties = QtWidgets.QGroupBox('Camera properties')
        self._gb_properties.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._gb_properties)
        ## Exposure
        self._gb_properties.layout().addWidget(QtWidgets.QLabel('Exposure [ms]'), 0, 0)
        self._dspn_exposure = QtWidgets.QDoubleSpinBox(self._gb_properties)
        self._dspn_exposure.setSingleStep(0.01)
        self._dspn_exposure.valueChanged.connect(lambda: self.updateConfig(Def.CameraCfg.exposure))
        self._gb_properties.layout().addWidget(self._dspn_exposure, 0, 1)
        ## Gain
        self._gb_properties.layout().addWidget(QtWidgets.QLabel('Gain [a.u.]'), 1, 0)
        self._dspn_gain = QtWidgets.QDoubleSpinBox(self._gb_properties)
        self._dspn_gain.setSingleStep(0.01)
        self._dspn_gain.valueChanged.connect(lambda: self.updateConfig(Def.CameraCfg.gain))
        self._gb_properties.layout().addWidget(self._dspn_gain, 1, 1)

        ### Set property update timer
        self.propTimer = QtCore.QTimer()
        self.propTimer.setInterval(250)
        self.propTimer.timeout.connect(self.updateProperties)
        self.propTimer.start()

    def updateProperties(self):
        self._dspn_exposure.setValue(Config.Camera[Def.CameraCfg.exposure])
        self._dspn_gain.setValue(Config.Camera[Def.CameraCfg.gain])

    def updateConfig(self, propName):
        if propName == Def.CameraCfg.exposure:
            Config.Camera[propName] = self._dspn_exposure.value()
        elif propName == Def.CameraCfg.gain:
            Config.Camera[propName] = self._dspn_gain.value()
