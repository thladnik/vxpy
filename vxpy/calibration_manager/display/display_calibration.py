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
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget, UniformWidth

vxvisual.set_vispy_env()


class DisplayCalibration(QtWidgets.QWidget):
    visual = None

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Create canvas
        self.canvas = Canvas(always_on_top=False)

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

        self.xminbound = 0
        self.xmaxbound = 1
        self.yminbound = 0
        self.ymaxbound = 1

    def mouseDoubleClickEvent(self, ev, *args, **kwargs):
        for screen_id, screen in enumerate(access.application.screens()):
            screen_rect = self.calculate_screen_rect(screen)

            # Check if clicked position is contained in screen rect
            if screen_rect.contains(QtCore.QPoint(ev.pos().x(), ev.pos().y())):
                # Set to fullscreen if it is contained
                self.set_fullscreen(screen_id)

    def set_fullscreen(self, screen_id):
        print(f'Set display to fullscreen on screen {screen_id}')

        screen = access.application.screens()[screen_id]
        px_ratio = screen.devicePixelRatio()
        self.main.global_settings.screen_id.set_value(screen_id)
        self.main.global_settings.win_x_pos.set_value(screen.geometry().x())
        self.main.global_settings.win_y_pos.set_value(screen.geometry().y())
        self.main.global_settings.win_width.set_value(int(screen.geometry().width() * px_ratio))
        self.main.global_settings.win_height.set_value(int(screen.geometry().height() * px_ratio))

        access.application.processEvents()

    def calculate_bounds(self):
        xbounds = []
        ybounds = []
        # Go through all screens and gauge the bounds
        for screen in access.application.screens():
            geo = screen.geometry()
            px_ratio = screen.devicePixelRatio()

            xbounds.append(geo.x())
            xbounds.append(geo.x() + geo.width())

            ybounds.append(geo.y())
            ybounds.append(geo.y() + geo.height())

        # Set bounds
        self.xminbound = min(xbounds)
        self.xmaxbound = max(xbounds)
        self.yminbound = min(ybounds)
        self.ymaxbound = max(ybounds)

        return self.display_bounds

    @property
    def display_bounds(self):
        return self.xminbound, self.xmaxbound, self.yminbound, self.ymaxbound

    def calculate_screen_rect(self, screen):

        # Get bounds
        xmin, xmax, ymin, ymax = self.display_bounds

        # Determine ranges
        xrange = xmax - xmin
        yrange = ymax - ymin

        # Estimate available drawing space on canvas
        canvas_width = self.size().width()-1
        canvas_height = self.size().height()-1

        # Calculate rect
        geo = screen.geometry()
        rect = QtCore.QRect(canvas_width * (geo.x() - xmin) / xrange,
                            canvas_height * (geo.y() - ymin) / yrange,
                            canvas_width * geo.width() / xrange,
                            canvas_height * geo.height() / yrange)

        return rect

    def paintEvent(self, QPaintEvent):

        # Update bounds
        self.calculate_bounds()

        # Paint all screens on canvas
        for screen_id, screen in enumerate(access.application.screens()):

            screen_rect = self.calculate_screen_rect(screen)

            self.painter.begin(self)

            # Paint rect
            self.painter.setBrush(QtCore.Qt.BrushStyle.Dense4Pattern)
            self.painter.drawRect(screen_rect)

            # Paint text
            self.painter.setPen(QColor(168, 34, 3))
            self.painter.setFont(QFont('Decorative', 30))
            self.painter.drawText(screen_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f'Screen {screen_id}')

            self.painter.end()

        return


class GlobalSettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Global')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())

        self.fixed_width = UniformWidth()

        # Window x pos
        self.win_x_pos = IntSliderWidget(self, 'Window X-Pos [px]',
                                         limits=(-5000, 5000), default=0,
                                         step_size=1, label_width=100)
        self.win_x_pos.connect_callback(self.update_window_x_pos)
        self.fixed_width.add_widget(self.win_x_pos.label)
        self.layout().addWidget(self.win_x_pos)

        # Window y pos
        self.win_y_pos = IntSliderWidget(self, 'Window Y-Pos [px]',
                                         limits=(-5000, 5000), default=0,
                                         step_size=1, label_width=100)
        self.win_y_pos.connect_callback(self.update_window_y_pos)
        self.fixed_width.add_widget(self.win_y_pos.label)
        self.layout().addWidget(self.win_y_pos)

        # Window width
        self.win_width = IntSliderWidget(self, 'Window width [px]',
                                         limits=(1, 5000), default=0,
                                         step_size=1, label_width=100)
        self.win_width.connect_callback(self.update_window_width)
        self.fixed_width.add_widget(self.win_width.label)
        self.layout().addWidget(self.win_width)

        # Window height
        self.win_height = IntSliderWidget(self, 'Window height [px]',
                                          limits=(1, 5000), default=0,
                                          step_size=1, label_width=100)
        self.win_height.connect_callback(self.update_window_height)
        self.fixed_width.add_widget(self.win_height.label)
        self.layout().addWidget(self.win_height)

        # Use current window settings
        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.use_current_window_settings)
        self.layout().addWidget(self.btn_use_current_window)

        # X Position
        self.x_pos = DoubleSliderWidget(self, 'X-position',
                                        limits=(-1., 1.), default=0.,
                                        step_size=.001, decimals=3, label_width=100)
        self.x_pos.connect_callback(self.update_x_pos)
        self.fixed_width.add_widget(self.x_pos.label)
        self.layout().addWidget(self.x_pos)

        # Y Position
        self.y_pos = DoubleSliderWidget(self, 'Y-position',
                                        limits=(-1., 1.), default=0.,
                                        step_size=.001, decimals=3, label_width=100)
        self.y_pos.connect_callback(self.update_y_pos)
        self.fixed_width.add_widget(self.y_pos.label)
        self.layout().addWidget(self.y_pos)

        # Screen
        self.screen_id = IntSliderWidget(self, 'Screen ID',
                                         limits=(0, 10), default=0, step_size=1, label_width=100)
        self.screen_id.connect_callback(self.update_screen_id)
        self.fixed_width.add_widget(self.screen_id.label)
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
        calib.CALIB_DISP_WIN_SIZE_WIDTH_PX = value
        access.window.display.update_canvas()

    @staticmethod
    def update_window_height(value):
        calib.CALIB_DISP_WIN_SIZE_HEIGHT_PX = value
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
        self.win_width.set_value(calib.CALIB_DISP_WIN_SIZE_WIDTH_PX)
        self.win_height.set_value(calib.CALIB_DISP_WIN_SIZE_HEIGHT_PX)
        self.x_pos.set_value(calib.CALIB_DISP_GLOB_POS_X)
        self.y_pos.set_value(calib.CALIB_DISP_GLOB_POS_Y)


class VisualSettings(QtWidgets.QTabWidget):

    def __init__(self):
        QtWidgets.QTabWidget.__init__(self)

        self.planar = planar_calibration.PlanarCalibrationWidget()
        self.spherical = spherical_calibration.SphericalCalibrationWidget()

        self.addTab(self.planar, 'Planar')
        self.addTab(self.spherical, 'Spherical')
