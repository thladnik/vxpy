"""
MappApp ./setup/display_calibration.py
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
import numpy as np
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QPainter, QColor, QFont
from vispy import app, gloo

from vxpy import calib
from vxpy import definitions
from vxpy.definitions import *
from vxpy.calibration_manager.display import planar_calibration
from vxpy.calibration_manager.display import spherical_calibration
from vxpy.calibration_manager import access
from vxpy.modules.display import Canvas
from vxpy.utils.uiutils import DoubleSliderWidget, IntSliderWidget


class DisplayCalibration(QtWidgets.QWidget):

    visual = None

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Create canvas
        self.canvas = Canvas(1/10)

        self.canvas_timer = QtCore.QTimer(self)
        self.canvas_timer.setInterval(50)
        self.canvas_timer.timeout.connect(self.trigger_on_draw)
        self.canvas_timer.start()

        # Set layout
        self.setLayout(QtWidgets.QGridLayout())

        self.fullscreen_select = QtWidgets.QGroupBox('Fullscreen selection')
        self.layout().addWidget(self.fullscreen_select, 0, 0)
        self.fullscreen_select.setLayout(QtWidgets.QGridLayout())
        self.screen_settings = ScreenSelection(self)
        self.fullscreen_select.layout().addWidget(self.screen_settings)

        # Global settings
        self.global_settings = GlobalSettings(self)
        self.layout().addWidget(self.global_settings, 0, 1)

        # Visual settings
        self.visuals = VisualSettings()
        self.layout().addWidget(self.visuals, 1, 0, 1, 2)

        access.window.sig_window_closed.connect(self.canvas.close)
        self.update_canvas()

    def trigger_on_draw(self):
        self.canvas.draw()

    def update_canvas(self):
        # Update size
        self.canvas.size = (calib.CALIB_DISP_WIN_SIZE_WIDTH, calib.CALIB_DISP_WIN_SIZE_HEIGHT)

        # Update position
        self.canvas.position = (calib.CALIB_DISP_WIN_POS_X, calib.CALIB_DISP_WIN_POS_Y)

        # Update fullscreen
        self.canvas.fullscreen = calib.CALIB_DISP_WIN_FULLSCREEN

        app.process_events()


class ScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent: DisplayCalibration):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        self.screens = list()
        self.screen_frames = list()
        for screen in access.application.screens():
            geo = screen.geometry()
            self.screens.append((geo.x(), geo.y(), geo.width(), geo.height()))

        self.screens_norm = self.screens

    def mouseDoubleClickEvent(self, ev, *args, **kwargs):
        for i, (screen_norm, screen) in enumerate(zip(self.screens_norm, self.screens)):
            rect = QtCore.QRectF(*screen_norm)

            if rect.contains(QtCore.QPoint(ev.pos().x(), ev.pos().y())):

                print('Set display to fullscreen on screen {}'.format(i))

                self.main.global_settings.win_x_pos.set_value(screen[0])
                self.main.global_settings.win_y_pos.set_value(screen[1])
                self.main.global_settings.win_width.set_value(screen[2])
                self.main.global_settings.win_height.set_value(screen[3])

                access.application.processEvents()

                # Set fullscreen
                self.main.canvas.fullscreen = True

                calib.CALIB_DISP_WIN_FULLSCREEN = True

    def paintEvent(self, QPaintEvent):
        if len(self.screens) == 0:
            return

        screens = np.array(self.screens).astype(np.float32)
        # Norm position
        # x
        xmax = screens[:,2].sum()
        ymax = screens[:,3].sum()
        usemax = max(xmax, ymax)
        screens[:,0] -= screens[:,0].min()
        screens[:,0] = screens[:,0] / usemax
        screens[:,0] *= self.size().width()
        # y
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

            self.painter.setBrush(QtCore.Qt.BrushStyle.Dense4Pattern)
            self.painter.drawRect(rect)

            self.painter.setPen(QColor(168, 34, 3))
            self.painter.setFont(QFont('Decorative', 30))
            self.painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, str(i))

            self.painter.end()


class GlobalSettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Global')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())

        # Window x pos
        self.win_x_pos = IntSliderWidget('Window X-Pos [px]',-5000,5000,0,
                                         step_size=1,label_width=100)
        self.win_x_pos.connect_to_result(self.update_window_x_pos)
        self.layout().addWidget(self.win_x_pos)

        # Window y pos
        self.win_y_pos = IntSliderWidget('Window Y-Pos [px]',-5000,5000,0,
                                         step_size=1,label_width=100)
        self.win_y_pos.connect_to_result(self.update_window_y_pos)
        self.layout().addWidget(self.win_y_pos)

        # Window width
        self.win_width = IntSliderWidget('Window width [px]',1,5000,0,
                                         step_size=1,label_width=100)
        self.win_width.connect_to_result(self.update_window_width)
        self.layout().addWidget(self.win_width)

        # Window height
        self.win_height = IntSliderWidget('Window height [px]',1,5000,0,
                                          step_size=1,label_width=100)
        self.win_height.connect_to_result(self.update_window_height)
        self.layout().addWidget(self.win_height)

        # Use current window settings
        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.use_current_window_settings)
        self.layout().addWidget(self.btn_use_current_window)

        # X Position
        self.x_pos = DoubleSliderWidget('X-position',-1.,1.,0.,
                                        step_size=.001,decimals=3,label_width=100)
        self.x_pos.connect_to_result(self.update_x_pos)
        self.layout().addWidget(self.x_pos)

        # Y Position
        self.y_pos = DoubleSliderWidget('Y-position',-1.,1.,0.,
                                        step_size=.001,decimals=3,label_width=100)
        self.y_pos.connect_to_result(self.update_y_pos)
        self.layout().addWidget(self.y_pos)

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

        access.window.sig_reload_calibration.connect(self.update_ui)

    @staticmethod
    def update_window_x_pos(value):
        calib.CALIB_DISP_WIN_POS_X = value
        access.window.display.update_canvas()

    @staticmethod
    def update_window_y_pos(value):
        calib.CALIB_DISP_WIN_POS_Y = value
        access.window.display.update_canvas()

    @staticmethod
    def update_window_width(value):
        calib.CALIB_DISP_WIN_SIZE_WIDTH = value
        access.window.display.update_canvas()

    @staticmethod
    def update_window_height(value):
        calib.CALIB_DISP_WIN_SIZE_HEIGHT = value
        access.window.display.update_canvas()

    @staticmethod
    def update_x_pos(value):
        calib.CALIB_DISP_GLOB_POS_X = value
        access.window.display.update_canvas()

    @staticmethod
    def update_y_pos(value):
        calib.CALIB_DISP_GLOB_POS_Y = value
        access.window.display.update_canvas()

    def use_current_window_settings(self):
        geo = self.main.canvas._native_window.geometry()
        fgeo = self.main.canvas._native_window.frameGeometry()

        self.win_width.set_value(geo.width())
        self.win_height.set_value(geo.height())

        self.win_x_pos.set_value(fgeo.x())
        self.win_y_pos.set_value(fgeo.y())

    def update_ui(self):
        self.win_x_pos.set_value(calib.CALIB_DISP_WIN_POS_X)
        self.win_y_pos.set_value(calib.CALIB_DISP_WIN_POS_Y)
        self.win_width.set_value(calib.CALIB_DISP_WIN_SIZE_WIDTH)
        self.win_height.set_value(calib.CALIB_DISP_WIN_SIZE_HEIGHT)
        self.x_pos.set_value(calib.CALIB_DISP_GLOB_POS_X)
        self.y_pos.set_value(calib.CALIB_DISP_GLOB_POS_Y)


class VisualSettings(QtWidgets.QTabWidget):

    def __init__(self):
        QtWidgets.QTabWidget.__init__(self)

        self.planar = planar_calibration.PlanarCalibrationWidget()
        self.spherical = spherical_calibration.SphericalCalibrationWidget()

        self.addTab(self.planar, 'Planar')
        self.addTab(self.spherical, 'Spherical')

        # (Debug option) Select visual config tab
        # self.setCurrentWidget(self.spherical)
