from __future__ import annotations

from typing import Dict

import yaml
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QApplication
from vxpy import config, configuration
from vxpy import utils
from vxpy.modules.display import Canvas
from vxpy.utils import widgets
import vxpy.extras


class DisplayManager(QtWidgets.QWidget):
    instance: DisplayManager = None
    # Create canvas
    canvas = Canvas(always_on_top=False)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        DisplayManager.instance = self
        self.setLayout(QtWidgets.QHBoxLayout())

        # Set layout
        self.window_settings = WindowSettings(parent=self)
        self.layout().addWidget(self.window_settings)

        self.canvas_timer = QtCore.QTimer(self)
        self.canvas_timer.setInterval(50)
        self.canvas_timer.timeout.connect(self.trigger_on_draw)
        self.canvas_timer.start()

        self.update_canvas()

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


class WindowSettings(QtWidgets.QGroupBox):

    def __init__(self, *args, **kwargs):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)', *args, **kwargs)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.screen_painter = ScreenPainter(parent=self)
        self.layout().addWidget(self.screen_painter)

        # Add parameter widgets
        self.parameters = QtWidgets.QGroupBox('Window parameters', parent=self)
        self.parameters.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.parameters)
        label_width = widgets.UniformWidth()
        edit_width = widgets.UniformWidth()
        self.screen_id = widgets.IntSliderWidget(parent=self.parameters, label='DISPLAY_WIN_SCREEN_ID',
                                                 default=0, limits=(0, 10), step_size=1)
        label_width.add_widget(self.screen_id.label)
        edit_width.add_widget(self.screen_id.spinner)
        self.screen_id.connect_callback(self.set_parameter_callback('DISPLAY_WIN_SCREEN_ID'))
        self.parameters.layout().addWidget(self.screen_id)
        self.x_pos = widgets.IntSliderWidget(parent=self.parameters, label='DISPLAY_WIN_POS_X',
                                             default=0, limits=(-10 ** 4, 10 ** 4), step_size=1)
        label_width.add_widget(self.x_pos.label)
        edit_width.add_widget(self.x_pos.spinner)
        self.x_pos.connect_callback(self.set_parameter_callback('DISPLAY_WIN_POS_X'))
        self.parameters.layout().addWidget(self.x_pos)
        self.y_pos = widgets.IntSliderWidget(parent=self.parameters, label='DISPLAY_WIN_POS_Y',
                                             default=0, limits=(-10 ** 4, 10 ** 4), step_size=1)
        label_width.add_widget(self.y_pos.label)
        edit_width.add_widget(self.y_pos.spinner)
        self.y_pos.connect_callback(self.set_parameter_callback('DISPLAY_WIN_POS_Y'))
        self.parameters.layout().addWidget(self.y_pos)
        self.win_width = widgets.IntSliderWidget(parent=self.parameters, label='DISPLAY_WIN_SIZE_WIDTH_PX',
                                                 default=400, limits=(1, 10 ** 4), step_size=1)
        label_width.add_widget(self.win_width.label)
        edit_width.add_widget(self.win_width.spinner)
        self.win_width.connect_callback(self.set_parameter_callback('DISPLAY_WIN_SIZE_WIDTH_PX'))
        self.parameters.layout().addWidget(self.win_width)
        self.win_height = widgets.IntSliderWidget(parent=self.parameters, label='DISPLAY_WIN_SIZE_HEIGHT_PX',
                                                  default=400, limits=(1, 10 ** 4), step_size=1)
        label_width.add_widget(self.win_height.label)
        edit_width.add_widget(self.win_height.spinner)
        self.win_height.connect_callback(self.set_parameter_callback('DISPLAY_WIN_SIZE_HEIGHT_PX'))
        self.parameters.layout().addWidget(self.win_height)

        self.parameters.layout().addItem(QtWidgets.QSpacerItem(1, 1,
                                                               QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                                               QtWidgets.QSizePolicy.Policy.MinimumExpanding))

        self.timer = QtCore.QTimer(parent=self)
        self.timer.timeout.connect(self.update_parameters)
        self.timer.setInterval(100)
        self.timer.start()

    def update_parameters(self):
        parameters: Dict[str, widgets.IntSliderWidget] = {'DISPLAY_WIN_SCREEN_ID': self.screen_id,
                                                          'DISPLAY_WIN_POS_X': self.x_pos,
                                                          'DISPLAY_WIN_POS_Y': self.y_pos,
                                                          'DISPLAY_WIN_SIZE_WIDTH_PX': self.win_width,
                                                          'DISPLAY_WIN_SIZE_HEIGHT_PX': self.win_height}
        current_config_dict = configuration.get_configuration_data()
        for name, w in parameters.items():
            w.set_value(current_config_dict[name])

    def set_parameter_callback(self, name):
        def _parameter_callback(value):
            configuration.set_configuration_data({name: value})

        return _parameter_callback


class ScreenPainter(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setMinimumSize(400, 400)
        # self.setMaximumSize(1000, 1000)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        self.painter = QtGui.QPainter()

    def mouseDoubleClickEvent(self, ev, *args, **kwargs):
        for screen_id, screen in enumerate(QApplication.instance().screens()):
            screen_rect = self.get_screen_rect(screen)

            # Check if clicked position is contained in screen rect
            if screen_rect.contains(QtCore.QPoint(ev.pos().x(), ev.pos().y())):
                # Set to fullscreen if it is contained
                self.set_fullscreen(screen_id)

    def set_fullscreen(self, screen_id):
        print(f'Set display to fullscreen on screen {screen_id}')

        screen = QApplication.instance().screens()[screen_id]
        px_ratio = screen.devicePixelRatio()
        config.DISPLAY_WIN_SCREEN_ID = screen_id
        config.DISPLAY_WIN_POS_X = screen.geometry().x()
        config.DISPLAY_WIN_POS_Y = screen.geometry().y()
        config.DISPLAY_WIN_SIZE_WIDTH_PX = int(screen.geometry().width() * px_ratio)
        config.DISPLAY_WIN_SIZE_HEIGHT_PX = int(screen.geometry().height() * px_ratio)

        # QApplication.instance().processEvents()

        DisplayManager.canvas.update_dimensions()

    def get_common_dim(self):
        return min(self.width(), self.height()) - 120

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        # Start
        self.painter.begin(self)

        xmin, xmax, ymin, ymax = self.get_screenspace()
        xrange, yrange = xmax - xmin, ymax - ymin
        screenspace_aspect = xrange / yrange
        scale = self.get_common_dim()

        screenspace_rect = QtCore.QRect(10, 10 / screenspace_aspect,
                                        scale + 100, (scale + 100) / screenspace_aspect)

        # Painter format
        self.painter.setPen(QtGui.QColor(255, 255, 255))
        # Paint rect
        self.painter.setBrush(QtCore.Qt.BrushStyle.Dense4Pattern)
        self.painter.drawRect(screenspace_rect)
        # self.painter.setFont(QtGui.QFont('Decorative', 10))
        # self.painter.drawText(screenspace_rect, QtCore.Qt.AlignmentFlag.AlignTop, f'Screenspace')

        # Paint screen
        self.painter.setFont(QtGui.QFont('Decorative', 14))
        for screen_id, screen in enumerate(QApplication.instance().screens()):
            screen_rect = self.get_screen_rect(screen)
            self.painter.setPen(QtGui.QColor(255, 0, 0))
            self.painter.setBrush(QtCore.Qt.BrushStyle.Dense4Pattern)
            self.painter.drawRect(screen_rect)
            self.painter.drawText(screen_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f'Screen {screen_id}')

        # End
        self.painter.end()

    def get_screenspace(self):
        xbounds = []
        ybounds = []
        # Go through all screens and gauge the bounds
        for screen in QApplication.instance().screens():
            geo = screen.geometry()
            px_ratio = screen.devicePixelRatio()

            xbounds.append(geo.x())
            xbounds.append(geo.x() + geo.width() * px_ratio)

            ybounds.append(geo.y())
            ybounds.append(geo.y() + geo.height() * px_ratio)

        # Set bounds
        xmin = min(xbounds)
        xmax = max(xbounds)
        ymin = min(ybounds)
        ymax = max(ybounds)

        return xmin, xmax, ymin, ymax

    def get_screen_dims(self, screen: QtGui.QScreen):
        geo = screen.geometry()
        px_ratio = screen.devicePixelRatio()
        return geo.x(), geo.y(), geo.width() * px_ratio, geo.height() * px_ratio

    def get_screen_rect(self, screen: QtGui.QScreen):

        xmin, xmax, ymin, ymax = self.get_screenspace()
        xrange, yrange = xmax - xmin, ymax - ymin
        screenspace_aspect = xrange / yrange
        scale = self.get_common_dim()

        x, y, width, height = self.get_screen_dims(screen)  # self.get_screen(QApplication.instance().screens()[1])
        xnorm = (x - xmin) / xrange
        ynorm = (y - ymin) / yrange
        wnorm = width / xrange
        hnorm = height / yrange

        screen_rect = QtCore.QRect(xnorm * scale + 60,
                                   (ynorm * scale + 60) / screenspace_aspect,
                                   wnorm * scale,
                                   hnorm * scale / screenspace_aspect)

        return screen_rect
