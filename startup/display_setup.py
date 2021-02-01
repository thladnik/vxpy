import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPainter, QColor, QFont
from vispy import app, gloo

import Config
import Def
from startup import settings
from startup.utils import ModuleWidget

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
        ModuleWidget.__init__(self, Def.DisplayCfg.name, parent=parent)

        app.use_app('pyqt5')

        # Create canvas
        self.canvas = Canvas(1/60)

        # Set timer for window updates
        self.tmr_glwindow = QtCore.QTimer()
        self.tmr_glwindow.setInterval(100)
        self.tmr_glwindow.timeout.connect(self.trigger_on_draw)
        self.tmr_glwindow.start()

        # Set layout
        self.setLayout(QtWidgets.QGridLayout())

        # Screen settings
        def button_reset():
            btn_reset_normal = QtWidgets.QPushButton('Reset to normal')
            btn_reset_normal.clicked.connect(self.canvas._native_window.showNormal)
            btn_reset_normal.clicked.connect(
                lambda: self.canvas._native_window.resize(512, 512))
            btn_reset_normal.clicked.connect(
                lambda: settings.current_config.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.window_fullscreen, False))
            return btn_reset_normal

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
        w, h = settings.current_config.getParsed(section, Def.DisplayCfg.window_width), \
               settings.current_config.getParsed(section, Def.DisplayCfg.window_height),
        self.canvas.size = (w, h)

        # Update position
        x, y = settings.current_config.getParsed(section, Def.DisplayCfg.window_pos_x), \
               settings.current_config.getParsed(section, Def.DisplayCfg.window_pos_y)
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

                self.main.global_settings.spn_win_x.set_value(screen[0])
                self.main.global_settings.spn_win_y.set_value(screen[1])
                self.main.global_settings.spn_win_width.set_value(screen[2])
                self.main.global_settings.spn_win_height.set_value(screen[3])


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

                settings.current_config.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.window_fullscreen, True)


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
        self.grp_pla_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_pla_checker)
        # Rows
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. rows [1/mm]'), 0, 0)
        self.grp_pla_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_rows.setValue(9)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_rows, 0, 1)
        # Cols
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. cols [1/mm]'), 1, 0)
        self.grp_pla_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_cols.setValue(9)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_cols, 1, 1)
        # Show button
        self.grp_pla_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_pla_checker.btn_show.clicked.connect(self.show_planar_checkerboard)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.btn_show, 2, 0, 1, 2)

        # Spherical checkerboard
        self.grp_sph_checker = QtWidgets.QGroupBox('Spherical Checkerboard')
        self.grp_sph_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_sph_checker)
        # Rows
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. rows'), 0, 0)
        self.grp_sph_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_rows.setValue(32)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_rows, 0, 1)
        # Cols
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. cols'), 1, 0)
        self.grp_sph_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_cols.setValue(32)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_cols, 1, 1)
        # Show button
        self.grp_sph_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_sph_checker.btn_show.clicked.connect(self.show_spherical_checkerboard)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.btn_show, 2, 0, 1, 2)

        # Spherical mesh
        self.grp_sph_mesh = QtWidgets.QGroupBox('Spherical Mesh')
        self.grp_sph_mesh.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_sph_mesh)
        # Rows
        self.grp_sph_mesh.layout().addWidget(QtWidgets.QLabel('Num. rows'), 0, 0)
        self.grp_sph_mesh.dspn_rows = QtWidgets.QSpinBox()
        self.grp_sph_mesh.dspn_rows.setValue(32)
        self.grp_sph_mesh.layout().addWidget(self.grp_sph_mesh.dspn_rows, 0, 1)
        # Cols
        self.grp_sph_mesh.layout().addWidget(QtWidgets.QLabel('Num. cols'), 1, 0)
        self.grp_sph_mesh.dspn_cols = QtWidgets.QSpinBox()
        self.grp_sph_mesh.dspn_cols.setValue(32)
        self.grp_sph_mesh.layout().addWidget(self.grp_sph_mesh.dspn_cols, 1, 1)
        # Show button
        self.grp_sph_mesh.btn_show = QtWidgets.QPushButton('Show')
        self.grp_sph_mesh.btn_show.clicked.connect(self.show_spherical_mesh)
        self.grp_sph_mesh.layout().addWidget(self.grp_sph_mesh.btn_show, 2, 0, 1, 2)

        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(vSpacer)

    def show_planar_checkerboard(self):
        from visuals.planar.Calibration import Checkerboard
        rows = self.grp_pla_checker.dspn_rows.value(),
        cols = self.grp_pla_checker.dspn_cols.value()
        self.main.canvas.visual = Checkerboard(self.main.canvas,
                                               **{Checkerboard.u_rows : rows,
                                                  Checkerboard.u_cols : cols})

    def show_spherical_checkerboard(self):
        from visuals.spherical.Calibration import BlackWhiteCheckerboard
        rows = self.grp_sph_checker.dspn_rows.value(),
        cols = self.grp_sph_checker.dspn_cols.value()
        self.main.canvas.visual = BlackWhiteCheckerboard(self.main.canvas,
                                                         **{BlackWhiteCheckerboard.u_rows : rows,
                                                            BlackWhiteCheckerboard.u_cols : cols})

    def show_spherical_mesh(self):
        from visuals.spherical.Calibration import RegularMesh
        rows = self.grp_sph_mesh.dspn_rows.value(),
        cols = self.grp_sph_mesh.dspn_cols.value()
        self.main.canvas.visual = RegularMesh(self.main.canvas,
                                              **{RegularMesh.u_rows : rows,
                                                 RegularMesh.u_cols : cols})


class GlobalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Global')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())


        from helper.gui import DoubleSliderWidget, IntSliderWidget

        # Window x pos
        self.spn_win_x = IntSliderWidget('Window X-Position', -5000, 5000, 0,
                                         step_size=1, label_width=100)
        self.spn_win_x.connect_to_result(self.update_window_x_pos)
        self.layout().addWidget(self.spn_win_x)

        # Window y pos
        self.spn_win_y = IntSliderWidget('Window Y-Position', -5000, 5000, 0,
                                         step_size=1, label_width=100)
        self.spn_win_y.connect_to_result(self.update_window_y_pos)
        self.layout().addWidget(self.spn_win_y)


        # Window width
        self.spn_win_width = IntSliderWidget('Window width', 1, 5000, 0,
                                         step_size=1, label_width=100)
        self.spn_win_width.connect_to_result(self.update_window_width)
        self.layout().addWidget(self.spn_win_width)

        # Window height
        self.spn_win_height = IntSliderWidget('Window Y-Position', 1, 5000, 0,
                                         step_size=1, label_width=100)
        self.spn_win_height.connect_to_result(self.update_window_height)
        self.layout().addWidget(self.spn_win_height)


        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.use_current_window_settings)
        self.layout().addWidget(self.btn_use_current_window)

        # X Position
        self.dspn_x_pos = DoubleSliderWidget('X-position', -1., 1., 0.,
                                                     step_size=.001, decimals=3, label_width=100)
        self.dspn_x_pos.connect_to_result(self.update_x_pos)
        self.layout().addWidget(self.dspn_x_pos)

        # Y Position
        self.dspn_y_pos = DoubleSliderWidget('Y-position', -1., 1., 0.,
                                                     step_size=.001, decimals=3, label_width=100)
        self.dspn_y_pos.connect_to_result(self.update_y_pos)
        self.layout().addWidget(self.dspn_y_pos)


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

        self.spn_win_width.setValue(geo.width())
        self.spn_win_height.setValue(geo.height())

        self.spn_win_x.setValue(fgeo.x())
        self.spn_win_y.setValue(fgeo.y())

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name

        self.spn_win_x.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.window_pos_x))
        self.spn_win_y.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.window_pos_y))
        self.spn_win_width.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.window_width))
        self.spn_win_height.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.window_height))
        self.dspn_x_pos.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.glob_x_pos))
        self.dspn_y_pos.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.glob_y_pos))


class SphericalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Spherical')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())

        from helper.gui import DoubleSliderWidget

        # Radial offset
        self.dspn_radial_offset = DoubleSliderWidget('Radial offset', -1., 1., 0.,
                                                     step_size=.001, decimals=3, label_width=100)
        self.dspn_radial_offset.connect_to_result(self.update_radial_offset)
        self.layout().addWidget(self.dspn_radial_offset)

        # Elevation
        self.dspn_view_elev_angle = DoubleSliderWidget('Elevation [deg]', -90., 90., 0.,
                                                       step_size=.1, decimals=1, label_width=100)
        self.dspn_view_elev_angle.connect_to_result(self.update_elevation)
        self.layout().addWidget(self.dspn_view_elev_angle)

        # Azimuth
        self.dspn_view_azim_angle = DoubleSliderWidget('Azimuth [deg]', -180., 180., 0.,
                                                       step_size=.1, decimals=1, label_width=100)
        self.dspn_view_azim_angle.connect_to_result(self.update_azimuth)
        self.layout().addWidget(self.dspn_view_azim_angle)

        # View distance
        self.dspn_view_distance = DoubleSliderWidget('Distance [norm]', 1., 50., 5.,
                                                       step_size=.05, decimals=2, label_width=100)
        self.dspn_view_distance.connect_to_result(self.update_view_distance)
        self.layout().addWidget(self.dspn_view_distance)

        # FOV
        self.dspn_view_fov = DoubleSliderWidget('FOV [deg]', .1, 179., 70.,
                                                       step_size=.05, decimals=2, label_width=100)
        self.dspn_view_fov.connect_to_result(self.update_view_fov)
        self.layout().addWidget(self.dspn_view_fov)

        # View scale
        self.dspn_view_scale = DoubleSliderWidget('Scale [norm]', .001, 10., 1.,
                                                       step_size=.001, decimals=3, label_width=100)
        self.dspn_view_scale.connect_to_result(self.update_view_scale)
        self.layout().addWidget(self.dspn_view_scale)

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

        self.dspn_radial_offset.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_pos_glob_radial_offset))
        self.dspn_view_elev_angle.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_view_elev_angle))
        self.dspn_view_azim_angle.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_view_azim_angle))
        self.dspn_view_distance.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_view_distance))
        self.dspn_view_fov.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_view_fov))
        self.dspn_view_scale.set_value(settings.current_config.getParsed(section, Def.DisplayCfg.sph_view_scale))


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
        self.dspn_x_extent.valueChanged.connect(lambda: settings.current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_xextent,
                                                                             self.dspn_x_extent.value()))
        self.dspn_x_extent.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('X-Extent [rel]'), 0, 0)
        self.layout().addWidget(self.dspn_x_extent, 0, 1)
        # Y extent
        self.dspn_y_extent = QtWidgets.QDoubleSpinBox()
        self.dspn_y_extent.setDecimals(3)
        self.dspn_y_extent.setMinimum(0.0)
        self.dspn_y_extent.setSingleStep(.001)
        self.dspn_y_extent.valueChanged.connect(lambda: settings.current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_yextent,
                                                                             self.dspn_y_extent.value()))
        self.dspn_y_extent.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Y-Extent [rel]'), 1, 0)
        self.layout().addWidget(self.dspn_y_extent, 1, 1)
        # Small side dimensions
        self.dspn_small_side = QtWidgets.QDoubleSpinBox()
        self.dspn_small_side.setDecimals(3)
        self.dspn_small_side.setSingleStep(.001)
        self.dspn_small_side.valueChanged.connect(lambda: settings.current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_small_side,
                                                                             self.dspn_small_side.value()))
        self.dspn_small_side.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Small side [mm]'), 2, 0)
        self.layout().addWidget(self.dspn_small_side, 2, 1)

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name

        self.dspn_x_extent.setValue(settings.current_config.getParsed(section, Def.DisplayCfg.pla_xextent))
        self.dspn_y_extent.setValue(settings.current_config.getParsed(section, Def.DisplayCfg.pla_yextent))
        self.dspn_small_side.setValue(settings.current_config.getParsed(section, Def.DisplayCfg.pla_small_side))
