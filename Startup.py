"""
MappApp ./Startup.py - Startup script is used for creation and
modification of program configuration files.
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

import argparse
from configparser import ConfigParser
import os
import sys
import time
import keyboard
from glumpy.app.window import window
import numpy as np


from PyQt5 import QtCore, QtWidgets

import Def
from helper import Basic
import process.Controller

from devices.Camera import GetCamera

import wres

current_config = Basic.ConfigParser()

import Logging
import Config
Logging.write = lambda *args, **kwargs: None

################################################################
################################
### MODULES

class ModuleWidget(QtWidgets.QWidget):

    def __init__(self, module_name, *_args, **_kwargs):
        QtWidgets.QWidget.__init__(self, *_args, **_kwargs)

        self.module_name = module_name

    def getSetting(self, option_name):
        global current_config
        return current_config.getParsed(self.module_name, option_name)

    def updateSetting(self, option, value):
        global current_config
        current_config.setParsed(self.module_name, option, value)


################################
### CAMERA

from devices import Camera
class CameraWidget(ModuleWidget):

    def __init__(self, parent):
        ModuleWidget.__init__(self, Def.CameraCfg.name, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())

        self._vbox_cameras = QtWidgets.QWidget()
        self._vbox_cameras.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self._vbox_cameras)

        self._listw_cameras = QtWidgets.QListWidget()
        self._vbox_cameras.layout().addWidget(QtWidgets.QLabel('Camera types'))
        self._vbox_cameras.layout().addWidget(self._listw_cameras)
        for name in Camera.__dict__:
            if name.startswith('CAM_'):
                self._listw_cameras.addItem(name)


################################
### DISPLAY

class DisplayWidget(ModuleWidget):

    visual = None

    def __init__(self, parent):
        ModuleWidget.__init__(self, Def.DisplayCfg.name, parent=parent)

        from glumpy import app

        ### Set universal MappApp backend
        app.use('{} (GL 4.6 core)'.format(Def.Display_backend))

        ### Create glumpy window and context
        self.glwindow = app.Window(color=(0., 0., 0., 1.))

        ### (Manually) Configure glumpy eventloop
        self.glumpy_backend = app.__backend__
        self.glumpy_clock = app.__init__(backend=self.glumpy_backend)
        self.glumpy_count = len(self.glumpy_backend.windows())

        ### (Manually) Decorate on_draw method
        self.on_draw = self.glwindow.event(self.on_draw)
        self.on_key_press = self.glwindow.event(self.on_key_press)

        ### Set timer for glumpy window updates
        self.tmr_glwindow = QtCore.QTimer()
        self.tmr_glwindow.setInterval(100)
        self.tmr_glwindow.timeout.connect(self.triggerOnDraw)
        self.tmr_glwindow.start()

        ### Set layout
        self.setLayout(QtWidgets.QGridLayout())

        ### Screen settings
        self.screen_settings = DisplayScreenSelection(self)
        self.layout().addWidget(self.screen_settings, 0, 0, 1, 2)

        self.calibration = DisplayCalibration(self)
        self.layout().addWidget(self.calibration, 0, 2)

        ### Global settings
        self.global_settings = GlobalDisplaySettings(self)
        self.layout().addWidget(self.global_settings, 1, 0)

        ### Spherical settings
        self.spherical_settings = SphericalDisplaySettings(self)
        self.layout().addWidget(self.spherical_settings, 1, 1)

        ### Planar settings
        self.planar_settings = PlanarDisplaySettings(self)
        self.layout().addWidget(self.planar_settings, 1, 2)


    def triggerOnDraw(self):
        if self.glumpy_count:
            self.glumpy_count = self.glumpy_backend.process(self.glumpy_clock.tick())

    def loadSettingsFromConfig(self):
        self.global_settings.loadSettingsFromConfig()
        self.spherical_settings.loadSettingsFromConfig()
        self.planar_settings.loadSettingsFromConfig()
        self.updateWindow()

    def updateWindow(self):
        section = Def.DisplayCfg.name
        global current_config

        Config.Display = current_config.getParsedSection(Def.DisplayCfg.name)

        ### Update size
        w, h = current_config.getParsed(section, Def.DisplayCfg.window_width), \
               current_config.getParsed(section, Def.DisplayCfg.window_height),
        self.glwindow.set_size(w, h)

        ### Update position
        x, y = current_config.getParsed(section, Def.DisplayCfg.window_pos_x), \
               current_config.getParsed(section, Def.DisplayCfg.window_pos_y)
        self.glwindow.set_position(x, y)


    def on_draw(self, dt):
        self.glwindow.clear((0., 0., 0., 1.))

        if not(self.visual is None):
            self.visual.draw(0, 0.0)


    def on_key_press(self, symbol, modifiers):

        return

        ###
        # Key event handling here sucks

        continPressDelay = 0.02
        print(window.key.X, symbol)

        if modifiers & window.key.MOD_ALT:
            if modifiers & window.key.MOD_SHIFT:
                ### Fullscreen toggle: Ctrl+Alt+F
                if symbol == window.key.F:
                    Config.Display[Def.DisplayCfg.window_fullscreen] = not(Config.Display[Def.DisplayCfg.window_fullscreen])


            sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1

            if keyboard.is_pressed('X'):
                try:
                    self.global_settings.dspn_x_pos.setValue(Config.Display[Def.DisplayCfg.glob_x_pos] + sign * 0.001)
                except:
                    import IPython
                    IPython.embed()

            """
            ### X position: Ctrl(+Shift)+X
            elif symbol == window.key.X:
                print('hello')
                while keyboard.is_pressed('X'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    #Config.Display[Def.DisplayCfg.glob_x_pos] += sign * 0.001
                    self.global_settings.dspn_x_pos.setValue(Config.Display[Def.DisplayCfg.glob_x_pos] + sign * 0.001)
                    time.sleep(continPressDelay)

            ### Y position: Ctrl(+Shift)+Y
            elif symbol == window.key.Y:
                while keyboard.is_pressed('Y'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    #Config.Display[Def.DisplayCfg.glob_y_pos] += sign * 0.001
                    self.global_settings.dspn_y_pos.setValue(Config.Display[Def.DisplayCfg.glob_y_pos] + sign * 0.001)
                    time.sleep(continPressDelay)

            ### Radial offset: Ctrl(+Shift)+R
            elif symbol == window.key.R:
                while keyboard.is_pressed('R'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_pos_glob_radial_offset] += sign * 0.001
                    time.sleep(continPressDelay)


            ### Elevation: Ctrl(+Shift)+E
            elif symbol == window.key.E:
                while keyboard.is_pressed('E'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_elev_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Azimuth: Ctrl(+Shift)+A
            elif symbol == window.key.A:
                while keyboard.is_pressed('A'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_azim_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Distance: Ctrl(+Shift)+D
            elif symbol == window.key.D:
                while keyboard.is_pressed('D'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_distance] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Scale: Ctrl(+Shift)+S
            elif symbol == window.key.S:
                while keyboard.is_pressed('S'):
                    sign = +1 if (modifiers & window.key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_scale] += sign * 0.001
                    time.sleep(continPressDelay)
            else:
                self._glWindow.on_key_press(symbol, modifiers)
            """

class DisplayScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent : DisplayWidget):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.screens = list()
        self.screen_frames = list()
        for screen in winapp.screens():
            geo = screen.geometry()
            self.screens.append((geo.x(), geo.y(), geo.width(), geo.height()))

        self.screens_norm = self.screens

    def mouseDoubleClickEvent(self, *args, **kwargs):
        for i, (screen_norm, screen) in enumerate(zip(self.screens_norm, self.screens)):
            rect = QtCore.QRectF(*screen_norm)

            if rect.contains(QtCore.QPoint(args[0].x(), args[0].y())):
                self.main.global_settings.spn_win_x.setValue(0)
                self.main.global_settings.spn_win_y.setValue(0)
                self.main.global_settings.spn_win_width.setValue(256)
                self.main.global_settings.spn_win_height.setValue(256)

                winapp.processEvents()

                wgeo = self.main.glwindow._native_window.geometry()
                fgeo = self.main.glwindow._native_window.frameGeometry()

                xdiff = fgeo.width()-wgeo.width()
                ydiff = fgeo.height()-wgeo.height()

                print('Set display to fullscreen on screen {}'.format(i))
                self.main.global_settings.spn_win_x.setValue(screen[0]-xdiff/2)
                self.main.global_settings.spn_win_y.setValue(screen[1]-ydiff-1)
                self.main.global_settings.spn_win_width.setValue(screen[2]+xdiff/2)
                self.main.global_settings.spn_win_height.setValue(screen[3]+ydiff-1)
                return

    def paintEvent(self, QPaintEvent):
        if len(self.screens) == 0:
            return

        global winapp
        from PyQt5.QtGui import QPainter, QColor, QFont

        screens = np.array(self.screens).astype(np.float32)
        ### Norm position
        ## x
        xmax = screens[:,2].sum()
        ymax = screens[:,3].sum()
        usemax = max(xmax, ymax)
        screens[:,0] -= screens[:,0].min()
        screens[:,0] = screens[:,0] / usemax
        screens[:,0] *= self.size().width()
        ## y
        screens[:,1] -= screens[:,1].min()
        screens[:,1] = screens[:,1] / usemax
        screens[:,1] *= self.size().height()
        ## Norm width/height
        screens[:,2] = screens[:,2] / usemax * self.size().width()
        screens[:,3] = screens[:,3] / usemax * self.size().height()

        screens = screens.astype(int)

        self.screens_norm = screens

        self.painter = QPainter()
        for i, screen in enumerate(screens):

            rect = QtCore.QRect(*screen)

            self.painter.begin(self)

            self.painter.setBrush(QtCore.Qt.Dense4Pattern)
            self.painter.drawRect(rect)

            self.painter.setPen(QColor(168, 34, 3))
            self.painter.setFont(QFont('Decorative', 30))
            self.painter.drawText(rect, QtCore.Qt.AlignCenter, str(i))

            self.painter.end()


class DisplayCalibration(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Display calibration')
        self.main = parent

        self.setLayout(QtWidgets.QVBoxLayout())

        ### Planar checkerboard
        self.grp_pla_checker = QtWidgets.QGroupBox('Planar Checkerboard')
        self.grp_pla_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_pla_checker)
        ## Rows
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. rows [1/mm]'), 0, 0)
        self.grp_pla_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_rows.setValue(5)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_rows, 0, 1)
        ## Cols
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. cols [1/mm]'), 1, 0)
        self.grp_pla_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_cols.setValue(5)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_cols, 1, 1)
        ## Show button
        self.grp_pla_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_pla_checker.btn_show.clicked.connect(
            lambda: self.showPlanarCheckerboard(self.grp_pla_checker.dspn_rows.value(),
                                                   self.grp_pla_checker.dspn_cols.value())
        )
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.btn_show, 2, 0, 1, 2)

        ### Spherical checkerboard
        self.grp_sph_checker = QtWidgets.QGroupBox('Spherical Checkerboard')
        self.grp_sph_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_sph_checker)
        ## Rows
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. rows'), 0, 0)
        self.grp_sph_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_rows.setValue(5)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_rows, 0, 1)
        ## Cols
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. cols'), 1, 0)
        self.grp_sph_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_cols.setValue(5)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_cols, 1, 1)
        ## Show button
        self.grp_sph_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_sph_checker.btn_show.clicked.connect(
            lambda: self.showSphericalCheckerboard(self.grp_sph_checker.dspn_rows.value(),
                                                   self.grp_sph_checker.dspn_cols.value())
        )
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.btn_show, 2, 0, 1, 2)

        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(vSpacer)

    def showPlanarCheckerboard(self, rows, cols):
        from Protocol import StaticProtocol
        from visuals.planar.Calibration import Checkerboard
        protocol = StaticProtocol(None)
        self.main.visual = Checkerboard(self.main.glwindow, **{Checkerboard.u_rows : rows,
                                                                Checkerboard.u_cols : cols})


    def showSphericalCheckerboard(self, rows, cols):
        from Protocol import StaticProtocol
        from visuals.spherical.Calibration import BlackWhiteCheckerboard
        protocol = StaticProtocol(None)
        self.main.visual = BlackWhiteCheckerboard(self.main.glwindow,
                                                  **{BlackWhiteCheckerboard.u_rows : rows,
                                                     BlackWhiteCheckerboard.u_cols : cols})



class GlobalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Global')
        self.main = parent

        global current_config

        ### Set layout
        self.setLayout(QtWidgets.QGridLayout())

        # Window x pos
        self.layout().addWidget(QtWidgets.QLabel('Window x-Position'), 0, 0)
        self.spn_win_x = QtWidgets.QSpinBox()
        self.spn_win_x.setMinimum(-9999)
        self.spn_win_x.setMaximum(9999)
        self.spn_win_x.setSingleStep(1)
        self.spn_win_x.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_pos_x,
                                                                             self.spn_win_x.value()))
        self.spn_win_x.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.spn_win_x, 0, 1)

        # Window y pos
        self.layout().addWidget(QtWidgets.QLabel('Window y-Position'), 1, 0)
        self.spn_win_y = QtWidgets.QSpinBox()
        self.spn_win_y.setMinimum(-9999)
        self.spn_win_y.setMaximum(9999)
        self.spn_win_y.setSingleStep(1)
        self.spn_win_y.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_pos_y,
                                                                             self.spn_win_y.value()))
        self.spn_win_y.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.spn_win_y, 1, 1)

        # Window width
        self.layout().addWidget(QtWidgets.QLabel('Window width'), 20, 0)
        self.spn_win_width = QtWidgets.QSpinBox()
        self.spn_win_width.setMinimum(1)
        self.spn_win_width.setMaximum(9999)
        self.spn_win_width.setSingleStep(1)
        self.spn_win_width.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_width,
                                                                             self.spn_win_width.value()))
        self.spn_win_width.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.spn_win_width, 20, 1)

        # Window height
        self.layout().addWidget(QtWidgets.QLabel('Window height'), 21, 0)
        self.spn_win_height = QtWidgets.QSpinBox()
        self.spn_win_height.setMinimum(1)
        self.spn_win_height.setMaximum(9999)
        self.spn_win_height.setSingleStep(1)
        self.spn_win_height.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_height,
                                                                             self.spn_win_height.value()))
        self.spn_win_height.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.spn_win_height, 21, 1)

        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.useCurrentWindowSettings)
        self.layout().addWidget(self.btn_use_current_window, 25, 0, 1, 2)

        # X Position
        self.layout().addWidget(QtWidgets.QLabel('X-position'), 40, 0)
        self.dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_x_pos.setDecimals(3)
        self.dspn_x_pos.setMinimum(-1.0)
        self.dspn_x_pos.setMaximum(1.0)
        self.dspn_x_pos.setSingleStep(.001)
        self.dspn_x_pos.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.glob_x_pos,
                                                                             self.dspn_x_pos.value()))
        self.dspn_x_pos.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.dspn_x_pos, 40, 1)

        # Y position
        self.layout().addWidget(QtWidgets.QLabel('Y-position'), 50, 0)
        self.dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_y_pos.setDecimals(3)
        self.dspn_y_pos.setMinimum(-1.0)
        self.dspn_y_pos.setMaximum(1.0)
        self.dspn_y_pos.setSingleStep(.001)
        self.dspn_y_pos.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.glob_y_pos,
                                                                             self.dspn_y_pos.value()))
        self.dspn_y_pos.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(self.dspn_y_pos, 50, 1)


    def useCurrentWindowSettings(self):

        geo = self.main.glwindow._native_window.geometry()
        fgeo = self.main.glwindow._native_window.frameGeometry()

        self.spn_win_width.setValue(geo.width())
        self.spn_win_height.setValue(geo.height())

        self.spn_win_x.setValue(fgeo.x())
        self.spn_win_y.setValue(fgeo.y())

    def loadSettingsFromConfig(self):
        section = Def.DisplayCfg.name
        global current_config

        self.spn_win_x.setValue(current_config.getParsed(section, Def.DisplayCfg.window_pos_x))
        self.spn_win_y.setValue(current_config.getParsed(section, Def.DisplayCfg.window_pos_y))
        self.spn_win_width.setValue(current_config.getParsed(section, Def.DisplayCfg.window_width))
        self.spn_win_height.setValue(current_config.getParsed(section, Def.DisplayCfg.window_height))
        self.dspn_x_pos.setValue(current_config.getParsed(section, Def.DisplayCfg.glob_x_pos))
        self.dspn_y_pos.setValue(current_config.getParsed(section, Def.DisplayCfg.glob_y_pos))


class SphericalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Spherical')
        self.main = parent

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())

        ## Radial position (distance from center)
        self.dspn_radial_offset = QtWidgets.QDoubleSpinBox()
        self.dspn_radial_offset.setDecimals(3)
        self.dspn_radial_offset.setMinimum(-1.0)
        self.dspn_radial_offset.setMaximum(1.0)
        self.dspn_radial_offset.setSingleStep(.001)
        self.dspn_radial_offset.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_pos_glob_radial_offset,
                                                                             self.dspn_radial_offset.value()))
        self.dspn_radial_offset.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Radial offset'), 0, 0)
        self.layout().addWidget(self.dspn_radial_offset, 0, 1)

        # Elevation
        self.dspn_view_elev_angle = QtWidgets.QDoubleSpinBox()
        self.dspn_view_elev_angle.setDecimals(1)
        self.dspn_view_elev_angle.setSingleStep(0.1)
        self.dspn_view_elev_angle.setMinimum(-90.0)
        self.dspn_view_elev_angle.setMaximum(90.0)
        self.dspn_view_elev_angle.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_elev_angle,
                                                                             self.dspn_view_elev_angle.value()))
        self.dspn_view_elev_angle.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 5, 0)
        self.layout().addWidget(self.dspn_view_elev_angle, 5, 1)

        # Azimuth
        self.dspn_view_azim_angle = QtWidgets.QDoubleSpinBox()
        self.dspn_view_azim_angle.setDecimals(1)
        self.dspn_view_azim_angle.setSingleStep(0.1)
        self.dspn_view_azim_angle.setMinimum(-90.0)
        self.dspn_view_azim_angle.setMaximum(90.0)
        self.dspn_view_azim_angle.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_azim_angle,
                                                                             self.dspn_view_azim_angle.value()))
        self.dspn_view_azim_angle.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Azimuth [deg]'), 10, 0)
        self.layout().addWidget(self.dspn_view_azim_angle, 10, 1)

        # View distance(from origin of sphere)
        self.dspn_view_distance = QtWidgets.QDoubleSpinBox()
        self.dspn_view_distance.setDecimals(1)
        self.dspn_view_distance.setSingleStep(.1)
        self.dspn_view_distance.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_distance,
                                                                             self.dspn_view_distance.value()))
        self.dspn_view_distance.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Distance [a.u.]'), 15, 0)
        self.layout().addWidget(self.dspn_view_distance, 15, 1)

        # View scale
        self.dspn_view_scale = QtWidgets.QDoubleSpinBox()
        self.dspn_view_scale.setDecimals(3)
        self.dspn_view_scale.setSingleStep(0.001)
        self.dspn_view_scale.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_scale,
                                                                             self.dspn_view_scale.value()))
        self.dspn_view_scale.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Scale [a.u.]'), 20, 0)
        self.layout().addWidget(self.dspn_view_scale, 20, 1)

    def loadSettingsFromConfig(self):
        section = Def.DisplayCfg.name
        global current_config

        self.dspn_radial_offset.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_pos_glob_radial_offset))
        self.dspn_view_elev_angle.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_elev_angle))
        self.dspn_view_azim_angle.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_azim_angle))
        self.dspn_view_distance.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_distance))
        self.dspn_view_scale.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_scale))


class PlanarDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar')
        self.main = parent

        self.setLayout(QtWidgets.QGridLayout())

        # X extent
        self.dspn_x_extent = QtWidgets.QDoubleSpinBox()
        self.dspn_x_extent.setDecimals(3)
        self.dspn_x_extent.setMinimum(0.0)
        self.dspn_x_extent.setSingleStep(.001)
        self.dspn_x_extent.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_xextent,
                                                                             self.dspn_x_extent.value()))
        self.dspn_x_extent.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('X-Extent [rel]'), 0, 0)
        self.layout().addWidget(self.dspn_x_extent, 0, 1)
        # Y extent
        self.dspn_y_extent = QtWidgets.QDoubleSpinBox()
        self.dspn_y_extent.setDecimals(3)
        self.dspn_y_extent.setMinimum(0.0)
        self.dspn_y_extent.setSingleStep(.001)
        self.dspn_y_extent.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_yextent,
                                                                             self.dspn_y_extent.value()))
        self.dspn_y_extent.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Y-Extent [rel]'), 1, 0)
        self.layout().addWidget(self.dspn_y_extent, 1, 1)
        # Small side dimensions
        self.dspn_small_side = QtWidgets.QDoubleSpinBox()
        self.dspn_small_side.setDecimals(3)
        self.dspn_small_side.setSingleStep(.001)
        self.dspn_small_side.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_small_side,
                                                                             self.dspn_small_side.value()))
        self.dspn_small_side.valueChanged.connect(self.main.updateWindow)
        self.layout().addWidget(QtWidgets.QLabel('Small side [mm]'), 2, 0)
        self.layout().addWidget(self.dspn_small_side, 2, 1)

    def loadSettingsFromConfig(self):
        section = Def.DisplayCfg.name
        global current_config

        self.dspn_x_extent.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_xextent))
        self.dspn_y_extent.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_yextent))
        self.dspn_small_side.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_small_side))


################################################################
################################
### STARTUP MAIN WINDOW

class ModuleCheckbox(QtWidgets.QCheckBox):

    def __init__(self, module_name, *_args):
        QtWidgets.QCheckBox.__init__(self, module_name.upper(), *_args)
        self.module_name = module_name

        self.toggled.connect(self.reactToToggle)

    def reactToToggle(self, bool):
        print('Set module \"{}\" usage to {}'.format(self.text(), bool))
        global current_config
        current_config.setParsed(self.module_name, Def.Cfg.use, bool)



class StartupConfiguration(QtWidgets.QMainWindow):

    _availModules = {Def.CameraCfg.name  : CameraWidget,
                     Def.DisplayCfg.name : DisplayWidget,
                     Def.GuiCfg.name     : ModuleWidget,
                     Def.IoCfg.name      : ModuleWidget,
                     Def.RecCfg.name     : ModuleWidget}

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self.configuration = Basic.Config()
        self._configfile = None
        self._currentConfigChanged = False

        self._setupUI()


    def _setupUI(self):
        global current_config
        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        hSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        ## Setup window
        self.resize(1200, 1000)

        ## Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        ########
        ### Config file selection
        self.gb_select = QtWidgets.QGroupBox('Select config file...')
        self.gb_select.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.gb_select)

        # Selection
        self.gb_select.layout().addWidget(QtWidgets.QLabel('Select configuration file: '))
        self.gb_select.cb_select = QtWidgets.QComboBox()
        self.gb_select.cb_select.currentTextChanged.connect(self.openConfigfile)
        self.gb_select.layout().addWidget(self.gb_select.cb_select)
        # New
        self.gb_select.btn_new = QtWidgets.QPushButton('Add new...')
        self.gb_select.btn_new.clicked.connect(self._addConfigfile)
        self.gb_select.layout().addWidget(self.gb_select.btn_new)
        # Use
        self.gb_select.btn_use = QtWidgets.QPushButton('Use')
        self.gb_select.btn_use.clicked.connect(self.startApplication)
        self.gb_select.layout().addWidget(self.gb_select.btn_use)


        ########
        ### Change configurations for current file
        self.gb_edit = QtWidgets.QGroupBox('Change config')
        self.gb_edit.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self.gb_edit)

        ####
        ### Module selection
        self.gb_edit.gb_select_mod = QtWidgets.QGroupBox('Select modules')
        self.gb_edit.gb_select_mod.setMaximumWidth(200)
        self.gb_edit.gb_select_mod.setLayout(QtWidgets.QVBoxLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.gb_select_mod, 0, 0)

        ## Set configs widget
        self.gb_edit.tab_modules = QtWidgets.QTabWidget(self)
        self.gb_edit.tab_modules.setLayout(QtWidgets.QGridLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.tab_modules, 0, 1, 1, 2)
        #self.gb_edit.layout().addItem(hSpacer, 1, 1, 1, 2)

        ### Add all available modules
        self.module_checkboxes = dict()
        self.module_widgets = dict()
        for name, widget in self._availModules.items():

            cb = ModuleCheckbox(name)
            cb.setChecked(False)
            self.module_checkboxes[name] = cb
            self.gb_edit.gb_select_mod.layout().addWidget(self.module_checkboxes[name])

            if widget.__name__ == 'ModuleWidget':
                wdgt = widget(name, self)
            else:
                wdgt = widget(self)


            self.module_widgets[name] = wdgt
            self.gb_edit.tab_modules.addTab(self.module_widgets[name], name.upper())

        ### Spacer
        self.gb_edit.gb_select_mod.layout().addItem(vSpacer)

        self.btn_save_config = QtWidgets.QPushButton('Save changes')
        self.btn_save_config.clicked.connect(current_config.saveToFile)
        self.gb_edit.layout().addWidget(self.btn_save_config, 1, 1)

        self.btn_start_app = QtWidgets.QPushButton('Save and start')
        self.btn_start_app.clicked.connect(self.saveAndStartApplication)
        self.gb_edit.layout().addWidget(self.btn_start_app, 1, 2)

        # Update and show
        self.updateConfigfileList()
        self.show()

    def updateConfigfileList(self):
        self.gb_select.cb_select.clear()
        for fname in os.listdir(Def.Path.Config):
            self.gb_select.cb_select.addItem(fname[:-4])

    def _addConfigfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(Def.Path.Config):
                with open(os.path.join(Def.Path.Config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self.updateConfigfileList()
            self.gb_select.cb_select.setCurrentText(name)


    def openConfigfile(self):

        name = self.gb_select.cb_select.currentText()

        if name == '':
            return

        print('Open config {}'.format(name))
        global current_config

        self._configfile = '{}.ini'.format(name)
        current_config.read(self._configfile)

        ### Set display config for visual compat.
        Config.Display = current_config.getParsedSection(Def.DisplayCfg.name)

        ### Update module selection
        for module_name, checkbox in self.module_checkboxes.items():
            use = current_config.getParsed(module_name, Def.Cfg.use)
            checkbox.setChecked(use)
            self.module_widgets[module_name].setEnabled(use)

        ### Update module settings
        for module_name, wdgt in self.module_widgets.items():
            if hasattr(wdgt, 'loadSettingsFromConfig'):
                print('Load settings for module \"{}\" from config file'.format(module_name))
                wdgt.loadSettingsFromConfig()
            else:
                print('Could not load settings for module \"{}\" from config file'.format(module_name))


    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                global current_config
                current_config.saveToFile()

        event.accept()

    def saveAndStartApplication(self):
        global current_config
        current_config.saveToFile()
        self.startApplication()

    def startApplication(self):
        print('Start application')
        global configfile
        configfile = self._configfile
        self.close()




if __name__ == '__main__':

    from sys import platform

    if platform == 'win32':
        ### Set windows timer precision as high as possible
        minres, maxres, curres = wres.query_resolution()
        print(curres)
        with wres.set_resolution(maxres):

            skip_setup = False

            parser = argparse.ArgumentParser()
            parser.add_argument('--ini', action='store', dest='ini_file', type=str)
            #parser.add_argument('--skip_setup', action='store_true', dest='skip_setup', default=False)
            args = parser.parse_args(sys.argv[1:])

            if not(args.ini_file is None):
                process.Controller.configfile = args.ini_file
                skip_setup = True

            if skip_setup:
                ctrl = process.Controller()

            else:

                configfile = None
                winapp = QtWidgets.QApplication([])
                startupwin = StartupConfiguration()
                winapp.exec_()

                if configfile is None:
                    exit()

                import process.Controller
                process.Controller.configfile = configfile
                ctrl = process.Controller()
    else:
        print('Sorry, probably not gonna work on \"{}\"'.format(platform))


