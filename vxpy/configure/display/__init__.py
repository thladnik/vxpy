"""
MappApp ./setup/__init__.py
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

from vxpy import Config
from vxpy import Def
from vxpy.configure import acc
from vxpy.configure.display import planar, spherical
from vxpy.configure.utils import ModuleWidget
from vxpy.utils.uiutils import DoubleSliderWidget, IntSliderWidget


class Canvas(app.Canvas):

    def __init__(self, _interval, *args, **kwargs):
        app.Canvas.__init__(self, *args, **kwargs)
        self.tick = 0
        self.visual = None
        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))

        self.show()

    def on_draw(self, event):
        gloo.clear()
        if self.visual is not None:
            self.visual.draw(0.0)
        self.update()

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)


class Main(ModuleWidget):

    visual = None

    def __init__(self, parent):
        ModuleWidget.__init__(self, Def.DisplayCfg.name, parent=parent)

        # app.use_app('glfw')
        acc.display = self

        # Create canvas
        self.canvas = Canvas(1/5)

        # Set timer for window updates
        self.tmr_glwindow = QtCore.QTimer()
        self.tmr_glwindow.setInterval(100)
        self.tmr_glwindow.timeout.connect(self.trigger_on_draw)
        self.tmr_glwindow.start()

        # Set layout
        self.setLayout(QtWidgets.QGridLayout())

        self.fullscreen_select = QtWidgets.QGroupBox('Fullscreen selection')
        self.layout().addWidget(self.fullscreen_select, 0, 0)
        self.fullscreen_select.setLayout(QtWidgets.QGridLayout())
        #self.fullscreen_select.btn_reset_normal = button_reset()
        #self.fullscreen_select.layout().addWidget(self.fullscreen_select.btn_reset_normal, 0, 1)
        self.screen_settings = ScreenSelection(self)
        self.fullscreen_select.layout().addWidget(self.screen_settings)

        # Global settings
        self.global_settings = GlobalSettings(self)
        self.layout().addWidget(self.global_settings, 0, 1)

        # Visual settings
        self.visuals = VisualSettings()
        self.layout().addWidget(self.visuals, 1, 0, 1, 2)

        acc.main.sig_reload_config.connect(self.update_canvas)

    def trigger_on_draw(self):
        app.process_events()

    def update_canvas(self):
        section = Def.DisplayCfg.name

        Config.Display = acc.cur_conf.getParsedSection(Def.DisplayCfg.name)

        # Update size
        w, h = acc.cur_conf.getParsed(section, Def.DisplayCfg.window_width), \
               acc.cur_conf.getParsed(section, Def.DisplayCfg.window_height),
        self.canvas.size = (w, h)

        # Update position
        x, y = acc.cur_conf.getParsed(section, Def.DisplayCfg.window_pos_x), \
               acc.cur_conf.getParsed(section, Def.DisplayCfg.window_pos_y)
        self.canvas.position = (x, y)

    def closed_main_window(self):
        self.canvas.close()


class ScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent: Main):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        self.screens = list()
        self.screen_frames = list()
        for screen in acc.app.screens():
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

                acc.app.processEvents()

                # Set fullscreen
                self.main.canvas.fullscreen = True
                #scr_handle = self.main.canvas.screens()[i]
                #self.main.canvas._native_window.windowHandle().setScreen(scr_handle)
                #self.main.canvas._native_window.showFullScreen()

                acc.cur_conf.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.window_fullscreen, True)


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

        acc.main.sig_reload_config.connect(self.load_config)

    def update_window_x_pos(self, win_x_pos):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.window_pos_x,
                               win_x_pos)
        acc.display.update_canvas()

    def update_window_y_pos(self, win_y_pos):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.window_pos_y,
                               win_y_pos)
        acc.display.update_canvas()

    def update_window_width(self, width):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.window_width,
                               width)
        acc.display.update_canvas()

    def update_window_height(self, height):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.window_height,
                               height)
        acc.display.update_canvas()

    def update_x_pos(self, x_pos):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.glob_x_pos,
                               x_pos)
        acc.display.update_canvas()

    def update_y_pos(self, y_pos):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.glob_y_pos,
                               y_pos)
        acc.display.update_canvas()

    def use_current_window_settings(self):

        geo = self.main.canvas._native_window.geometry()
        fgeo = self.main.canvas._native_window.frameGeometry()

        self.win_width.setValue(geo.width())
        self.win_height.setValue(geo.height())

        self.win_x_pos.setValue(fgeo.x())
        self.win_y_pos.setValue(fgeo.y())

    def load_config(self):
        section = Def.DisplayCfg.name

        self.win_x_pos.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.window_pos_x))
        self.win_y_pos.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.window_pos_y))
        self.win_width.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.window_width))
        self.win_height.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.window_height))
        self.x_pos.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.glob_x_pos))
        self.y_pos.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.glob_y_pos))


class VisualSettings(QtWidgets.QTabWidget):

    def __init__(self):
        QtWidgets.QTabWidget.__init__(self)

        self.planar = planar.Main()
        self.spherical = spherical.Main()

        self.addTab(self.planar, 'Planar')
        self.addTab(self.spherical, 'Spherical')

        # (Debug option) Select visual config tab
        # self.setCurrentWidget(self.spherical)
