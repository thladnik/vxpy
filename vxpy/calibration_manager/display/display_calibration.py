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
from vispy import gloo

from vxpy import calib
from vxpy.definitions import *
import vxpy.core.visual as vxvisual
from vxpy.calibration_manager.display import planar_calibration
from vxpy.calibration_manager.display import spherical_calibration
from vxpy.calibration_manager import access
from vxpy.modules.display import Canvas
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget

vxvisual.set_vispy_env()


class DisplayCalibration(QtWidgets.QWidget):
    visual = None

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Create canvas
        self.canvas = Canvas(1 / 10, always_on_top=False)

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

    def trigger_on_draw(self):
        self.canvas.on_draw(event=None)

    def update_canvas(self):
        self.canvas.clear()
        self.canvas.update_dimensions()


class ScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent: DisplayCalibration):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        self.painter = QPainter()

    def mouseDoubleClickEvent(self, ev, *args, **kwargs):
        for screen_id, screen_coords in enumerate(self._get_widget_screen_coords()):
            rect = QtCore.QRectF(*screen_coords)

            if not rect.contains(QtCore.QPoint(ev.pos().x(), ev.pos().y())):
                continue

            print(f'Set display to fullscreen on screen {screen_id}')

            screen = access.application.screens()[screen_id]
            px_ratio = screen.devicePixelRatio()
            self.main.global_settings.screen_id.set_value(screen_id)
            self.main.global_settings.win_x_pos.set_value(screen.geometry().x())
            self.main.global_settings.win_y_pos.set_value(screen.geometry().y())
            self.main.global_settings.win_width.set_value(int(screen.geometry().width() * px_ratio))
            self.main.global_settings.win_height.set_value(int(screen.geometry().height() * px_ratio))

            access.application.processEvents()

    @staticmethod
    def _get_norm_screen_coords() -> np.ndarray:

        # Get connected screens
        avail_screens = access.application.screens()

        # Calculate total display area bounding box
        area = [[s.geometry().width() * s.devicePixelRatio(), s.geometry().height() * s.devicePixelRatio()] for s in
                avail_screens]
        area = np.sum(area, axis=0)

        xmin = np.min([s.geometry().x() for s in avail_screens])
        ymin = np.min([s.geometry().y() for s in avail_screens])

        # Define normalization functions
        xnorm = lambda x: (x - xmin) / area[0]
        ynorm = lambda y: (y - ymin) / area[1]

        # Add screen dimensions
        screens = []
        for s in avail_screens:
            g = s.geometry()
            screens.append([xnorm(g.x() * s.devicePixelRatio()),  # x
                            ynorm(g.y() * s.devicePixelRatio()),  # y
                            xnorm(g.width() * s.devicePixelRatio()),  # width
                            ynorm(g.height() * s.devicePixelRatio())])  # height

        return np.array(screens)

    def _get_widget_screen_coords(self):
        s = self._get_norm_screen_coords()
        s[:, 0] *= self.size().width()
        s[:, 1] *= self.size().height()
        s[:, 2] *= self.size().width()
        s[:, 3] *= self.size().height()

        return s.astype(int)

    def paintEvent(self, QPaintEvent):

        for i, screen in enumerate(self._get_widget_screen_coords()):

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
        self.win_x_pos = IntSliderWidget('Window X-Pos [px]', -5000, 5000, 0,
                                         step_size=1, label_width=100)
        self.win_x_pos.connect_to_result(self.update_window_x_pos)
        self.layout().addWidget(self.win_x_pos)

        # Window y pos
        self.win_y_pos = IntSliderWidget('Window Y-Pos [px]', -5000, 5000, 0,
                                         step_size=1, label_width=100)
        self.win_y_pos.connect_to_result(self.update_window_y_pos)
        self.layout().addWidget(self.win_y_pos)

        # Window width
        self.win_width = IntSliderWidget('Window width [px]', 1, 5000, 0,
                                         step_size=1, label_width=100)
        self.win_width.connect_to_result(self.update_window_width)
        self.layout().addWidget(self.win_width)

        # Window height
        self.win_height = IntSliderWidget('Window height [px]', 1, 5000, 0,
                                          step_size=1, label_width=100)
        self.win_height.connect_to_result(self.update_window_height)
        self.layout().addWidget(self.win_height)

        # Use current window settings
        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.use_current_window_settings)
        self.layout().addWidget(self.btn_use_current_window)

        # X Position
        self.x_pos = DoubleSliderWidget('X-position', -1., 1., 0.,
                                        step_size=.001, decimals=3, label_width=100)
        self.x_pos.connect_to_result(self.update_x_pos)
        self.layout().addWidget(self.x_pos)

        # Y Position
        self.y_pos = DoubleSliderWidget('Y-position', -1., 1., 0.,
                                        step_size=.001, decimals=3, label_width=100)
        self.y_pos.connect_to_result(self.update_y_pos)
        self.layout().addWidget(self.y_pos)

        # Screen
        self.screen_id = IntSliderWidget('Screen ID', 0, 10, 0, step_size=1, label_width=100)
        self.screen_id.connect_to_result(self.update_screen_id)
        self.layout().addWidget(self.screen_id)

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
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

    @staticmethod
    def update_screen_id(value):
        calib.CALIB_DISP_WIN_SCREEN_ID = value
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
