"""
MappApp ./startup/display_setup.py
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
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPainter, QColor, QFont
from vispy import app, gloo

from mappapp import Config
from mappapp import Def
from mappapp.startup import settings
from mappapp.startup.utils import ModuleWidget
from mappapp.utils.gui import DoubleSliderWidget, IntSliderWidget


class Canvas(app.Canvas):

    def __init__(self, _interval, *args, **kwargs):
        app.Canvas.__init__(self, *args, **kwargs)
        self.tick = 0
        self.measure_fps(0.1, self.show_fps)
        self.visual = None
        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))

        self.timer = app.Timer(_interval, connect=self.on_timer, start=True)

        self.show()

    def on_draw(self, event):
        pass

    def on_timer(self, event):
        gloo.clear()
        if self.visual is not None:
            self.visual.draw(0.0)
        self.update()

    def show_fps(self, fps):
        pass
        #print("FPS {:.2f}".format(fps))

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)


class DisplayWidget(ModuleWidget):

    visual = None

    def __init__(self, parent):
        ModuleWidget.__init__(self,Def.DisplayCfg.name,parent=parent)

        # app.use_app('glfw')
        # app.use_app('glfw')

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
        self.layout().addWidget(self.fullscreen_select, 0, 0, 1, 2)
        self.fullscreen_select.setLayout(QtWidgets.QGridLayout())
        #self.fullscreen_select.btn_reset_normal = button_reset()
        #self.fullscreen_select.layout().addWidget(self.fullscreen_select.btn_reset_normal, 0, 1)
        self.screen_settings = DisplayScreenSelection(self)
        self.fullscreen_select.layout().addWidget(self.screen_settings, 1, 0, 1, 2)

        self.calibration = DisplayCalibration(self)
        self.layout().addWidget(self.calibration, 0, 2)

        # Global settings
        self.global_settings = GlobalDisplaySettings(self)
        self.layout().addWidget(self.global_settings, 1, 0)

        # Spherical settings
        self.spherical_settings = SphericalDisplaySettings(self)
        self.layout().addWidget(self.spherical_settings, 1, 1)

        # Planar settings
        self.planar_settings = PlanarDisplaySettings(self)
        self.layout().addWidget(self.planar_settings, 1, 2)

    def trigger_on_draw(self):
        app.process_events()

    def load_settings_from_config(self):
        self.global_settings.load_settings_from_config()
        self.spherical_settings.load_settings_from_config()
        self.planar_settings.load_settings_from_config()
        self.update_window()

    def update_window(self):
        section = Def.DisplayCfg.name

        Config.Display = settings.current_config.getParsedSection(Def.DisplayCfg.name)

        # Update size
        w, h = settings.current_config.getParsed(section,Def.DisplayCfg.window_width), \
               settings.current_config.getParsed(section,Def.DisplayCfg.window_height),
        self.canvas.size = (w, h)

        # Update position
        x, y = settings.current_config.getParsed(section,Def.DisplayCfg.window_pos_x), \
               settings.current_config.getParsed(section,Def.DisplayCfg.window_pos_y)
        self.canvas.position = (x, y)

    def closed_main_window(self):
        self.canvas.timer.stop()
        self.canvas.close()

    def on_draw(self, dt):
        if not(self.visual is None):
            self.visual.draw(0.0)


class DisplayScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent: DisplayWidget):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.screens = list()
        self.screen_frames = list()
        for screen in settings.winapp.screens():
            geo = screen.geometry()
            self.screens.append((geo.x(), geo.y(), geo.width(), geo.height()))

        self.screens_norm = self.screens

    def mouseDoubleClickEvent(self, *args, **kwargs):
        for i, (screen_norm, screen) in enumerate(zip(self.screens_norm, self.screens)):
            rect = QtCore.QRectF(*screen_norm)

            if rect.contains(QtCore.QPoint(args[0].x(), args[0].y())):

                print('Set display to fullscreen on screen {}'.format(i))

                self.main.global_settings.win_x_pos.set_value(screen[0])
                self.main.global_settings.win_y_pos.set_value(screen[1])
                self.main.global_settings.win_width.set_value(screen[2])
                self.main.global_settings.win_height.set_value(screen[3])


                # Update window settings
                #self.main.global_settings.spn_win_x.setValue(screen[0])
                #self.main.global_settings.spn_win_y.setValue(screen[1])
                #self.main.global_settings.spn_win_width.setValue(screen[2])
                #self.main.global_settings.spn_win_height.setValue(screen[3])
                settings.winapp.processEvents()

                # Set fullscreen
                self.main.canvas.fullscreen = True
                #scr_handle = self.main.canvas.screens()[i]
                #self.main.canvas._native_window.windowHandle().setScreen(scr_handle)
                #self.main.canvas._native_window.showFullScreen()

                settings.current_config.setParsed(Def.DisplayCfg.name,Def.DisplayCfg.window_fullscreen,True)


    def paintEvent(self, QPaintEvent):
        if len(self.screens) == 0:
            return

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

        # Planar checkerboard
        self.grp_pla_checker = QtWidgets.QGroupBox('Planar Checkerboard')
        self.grp_pla_checker.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.grp_pla_checker)
        # Vertical SF
        self.grp_pla_checker.vertical_sf = DoubleSliderWidget('Vertical SF [1/mm]', .001, 1., .1,
                                                              step_size=.001, decimals=3, label_width=100)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.vertical_sf)
        # Horizontal SF
        self.grp_pla_checker.horizontal_sf = DoubleSliderWidget('Horizontal SF [1/mm]', .001, 1., .1,
                                                                step_size=.001, decimals=3, label_width=100)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.horizontal_sf)
        # Show button
        self.grp_pla_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_pla_checker.btn_show.clicked.connect(self.show_planar_checkerboard)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.btn_show)

        # Spherical checkerboard
        self.grp_sph_checker = DisplaySphericalCheckerCalibration(self.main)
        self.layout().addWidget(self.grp_sph_checker)

        # Spherical mesh
        self.grp_sph_checker = DisplaySphericalMeshCalibration(self.main)
        self.layout().addWidget(self.grp_sph_checker)

        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(vSpacer)

    def show_planar_checkerboard(self):
        from mappapp.visuals.planar.calibration import Sinusoid2d
        vertical_sf = self.grp_pla_checker.vertical_sf.get_value(),
        horizontal_sf = self.grp_pla_checker.horizontal_sf.get_value()
        self.main.canvas.visual = Sinusoid2d(self.main.canvas,
                                             **{Sinusoid2d.u_sf_vertical: vertical_sf,
                                                Sinusoid2d.u_sf_horizontal: horizontal_sf,
                                                Sinusoid2d.u_checker_pattern: True})

    def show_spherical_mesh(self):
        from mappapp.visuals.spherical.calibration import RegularMesh
        rows = self.grp_sph_mesh.dspn_rows.value(),
        cols = self.grp_sph_mesh.dspn_cols.value()
        self.main.canvas.visual = RegularMesh(self.main.canvas,
                                              **{RegularMesh.u_rows : rows,
                                                 RegularMesh.u_cols : cols})



class DisplaySphericalMeshCalibration(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical mesh')
        self.main = main

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.elevation_sf = DoubleSliderWidget('Elevation SF [1/deg]', .001, 1., .1,
                                               step_size=.001, decimals=3, label_width=100)
        self.elevation_sf.connect_to_result(self.update_elevation_sp)
        self.layout().addWidget(self.elevation_sf)
        # Vertical SP
        self.elevation_sp = QtWidgets.QLineEdit('')
        self.elevation_sp.setDisabled(True)
        self.layout().addWidget(self.elevation_sp)
        self.elevation_sf.emit_current_value()

        # Horizontal SF
        self.azimuth_sf = DoubleSliderWidget('Azimuth SF [1/deg]', .001, 1., .1,
                                             step_size=.001, decimals=3, label_width=100)
        self.azimuth_sf.connect_to_result(self.update_azimuth_sp)
        self.layout().addWidget(self.azimuth_sf)
        # Horizontal SP
        self.azimuth_sp = QtWidgets.QLineEdit('')
        self.azimuth_sp.setDisabled(True)
        self.layout().addWidget(self.azimuth_sp)
        self.azimuth_sf.emit_current_value()

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def update_elevation_sp(self, sf):
        self.elevation_sp.setText('Elevation SP {:.1f} [deg]'.format(1. / sf))

    def update_azimuth_sp(self, sf):
        self.azimuth_sp.setText('Azimuth SP {:.1f} [deg]'.format(1. / sf))

    def show_visual(self):
        from mappapp.visuals.spherical.calibration import RegularMesh
        elevation_sf = self.elevation_sf.get_value(),
        azimuth_sf = self.azimuth_sf.get_value()
        self.main.canvas.visual = RegularMesh(self.main.canvas,
                                              **{RegularMesh.u_elevation_sf: elevation_sf,
                                                 RegularMesh.u_azimuth_sf: azimuth_sf})


class DisplaySphericalCheckerCalibration(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical checkerboard')
        self.main = main

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.elevation_sf = DoubleSliderWidget('Elevation SF [1/deg]', .001, 1., .1,
                                               step_size=.001, decimals=3, label_width=100)
        self.elevation_sf.connect_to_result(self.update_elevation_sp)
        self.layout().addWidget(self.elevation_sf)
        # Vertical SP
        self.elevation_sp = QtWidgets.QLineEdit('')
        self.elevation_sp.setDisabled(True)
        self.layout().addWidget(self.elevation_sp)
        self.elevation_sf.emit_current_value()

        # Horizontal SF
        self.azimuth_sf = DoubleSliderWidget('Azimuth SF [1/deg]', .001, 1., .1,
                                             step_size=.001, decimals=3, label_width=100)
        self.azimuth_sf.connect_to_result(self.update_azimuth_sp)
        self.layout().addWidget(self.azimuth_sf)
        # Horizontal SP
        self.azimuth_sp = QtWidgets.QLineEdit('')
        self.azimuth_sp.setDisabled(True)
        self.layout().addWidget(self.azimuth_sp)
        self.azimuth_sf.emit_current_value()

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def update_elevation_sp(self, sf):
        self.elevation_sp.setText('Elevation SP {:.1f} [deg]'.format(1. / sf))

    def update_azimuth_sp(self, sf):
        self.azimuth_sp.setText('Azimuth SP {:.1f} [deg]'.format(1. / sf))

    def show_visual(self):
        from mappapp.visuals.spherical.calibration import BlackWhiteCheckerboard
        elevation_sf = self.elevation_sf.get_value(),
        azimuth_sf = self.azimuth_sf.get_value()
        self.main.canvas.visual = BlackWhiteCheckerboard(self.main.canvas,
                                                         **{BlackWhiteCheckerboard.u_elevation_sf: elevation_sf,
                                                            BlackWhiteCheckerboard.u_azimuth_sf: azimuth_sf})


class GlobalDisplaySettings(QtWidgets.QGroupBox):

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

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(spacer)

    def update_window_x_pos(self, win_x_pos):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.window_pos_x,
                                          win_x_pos)
        self.main.update_window()

    def update_window_y_pos(self, win_y_pos):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.window_pos_y,
                                          win_y_pos)
        self.main.update_window()

    def update_window_width(self, width):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.window_width,
                                          width)
        self.main.update_window()

    def update_window_height(self, height):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.window_height,
                                          height)
        self.main.update_window()

    def update_x_pos(self, x_pos):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.glob_x_pos,
                                          x_pos)
        self.main.update_window()

    def update_y_pos(self, y_pos):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.glob_y_pos,
                                          y_pos)
        self.main.update_window()

    def use_current_window_settings(self):

        geo = self.main.canvas._native_window.geometry()
        fgeo = self.main.canvas._native_window.frameGeometry()

        self.win_width.setValue(geo.width())
        self.win_height.setValue(geo.height())

        self.win_x_pos.setValue(fgeo.x())
        self.win_y_pos.setValue(fgeo.y())

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name

        self.win_x_pos.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.window_pos_x))
        self.win_y_pos.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.window_pos_y))
        self.win_width.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.window_width))
        self.win_height.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.window_height))
        self.x_pos.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.glob_x_pos))
        self.y_pos.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.glob_y_pos))


class SphericalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Spherical')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())

        # Radial offset
        self.radial_offset = DoubleSliderWidget('Radial offset',-1.,1.,0.,
                                                step_size=.001,decimals=3,label_width=100)
        self.radial_offset.connect_to_result(self.update_radial_offset)
        self.layout().addWidget(self.radial_offset)

        # Elevation
        self.view_elev_angle = DoubleSliderWidget('Elevation [deg]',-90.,90.,0.,
                                                  step_size=.1,decimals=1,label_width=100)
        self.view_elev_angle.connect_to_result(self.update_elevation)
        self.layout().addWidget(self.view_elev_angle)

        # Azimuth
        self.view_azim_angle = DoubleSliderWidget('Azimuth [deg]',-180.,180.,0.,
                                                  step_size=.1,decimals=1,label_width=100)
        self.view_azim_angle.connect_to_result(self.update_azimuth)
        self.layout().addWidget(self.view_azim_angle)

        # View distance
        self.view_distance = DoubleSliderWidget('Distance [norm]',1.,50.,5.,
                                                step_size=.05,decimals=2,label_width=100)
        self.view_distance.connect_to_result(self.update_view_distance)
        self.layout().addWidget(self.view_distance)

        # FOV
        self.view_fov = DoubleSliderWidget('FOV [deg]',.1,179.,70.,
                                           step_size=.05,decimals=2,label_width=100)
        self.view_fov.connect_to_result(self.update_view_fov)
        self.layout().addWidget(self.view_fov)

        # View scale
        self.view_scale = DoubleSliderWidget('Scale [norm]',.001,10.,1.,
                                             step_size=.001,decimals=3,label_width=100)
        self.view_scale.connect_to_result(self.update_view_scale)
        self.layout().addWidget(self.view_scale)

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(spacer)


    def update_radial_offset(self, offset):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_pos_glob_radial_offset,
                                          offset)
        self.main.update_window()

    def update_elevation(self, elevation):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_view_elev_angle,
                                          elevation)
        self.main.update_window()

    def update_azimuth(self, azimuth):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_view_azim_angle,
                                          azimuth)
        self.main.update_window()

    def update_view_distance(self, distance):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_view_distance,
                                          distance)
        self.main.update_window()

    def update_view_fov(self, fov):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_view_fov,
                                          fov)
        self.main.update_window()

    def update_view_scale(self, scale):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.sph_view_scale,
                                          scale)
        self.main.update_window()

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name

        self.radial_offset.set_value(
            settings.current_config.getParsed(section,Def.DisplayCfg.sph_pos_glob_radial_offset))
        self.view_elev_angle.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.sph_view_elev_angle))
        self.view_azim_angle.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.sph_view_azim_angle))
        self.view_distance.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.sph_view_distance))
        self.view_fov.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.sph_view_fov))
        self.view_scale.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.sph_view_scale))


class PlanarDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar')
        self.main = parent

        self.setLayout(QtWidgets.QVBoxLayout())

        # X extent
        self.x_extent = DoubleSliderWidget('X-extent [rel]', 0., 10., 1.,
                                                     step_size=.001, decimals=3, label_width=100)
        self.x_extent.connect_to_result(self.update_x_extent)
        self.layout().addWidget(self.x_extent)

        # Y extent
        self.y_extent = DoubleSliderWidget('Y-extent [rel]', 0., 10., 1.,
                                                     step_size=.001, decimals=3, label_width=100)
        self.y_extent.connect_to_result(self.update_y_extent)
        self.layout().addWidget(self.y_extent)

        # Small side
        self.small_side = IntSliderWidget('Small side [mm]', 1, 1000, 100, label_width=100)
        self.small_side.connect_to_result(self.update_small_side)
        self.layout().addWidget(self.small_side)

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(spacer)

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name

        self.x_extent.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.pla_xextent))
        self.y_extent.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.pla_yextent))
        self.small_side.set_value(settings.current_config.getParsed(section,Def.DisplayCfg.pla_small_side))

    def update_x_extent(self, x_extent):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.pla_xextent,
                                          x_extent)
        self.main.update_window()

    def update_y_extent(self, y_extent):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.pla_yextent,
                                          y_extent)
        self.main.update_window()

    def update_small_side(self, small_side):
        settings.current_config.setParsed(Def.DisplayCfg.name,
                                          Def.DisplayCfg.pla_small_side,
                                          small_side)
        self.main.update_window()