"""
vxPy ./calibration_manager/display/planar_calibration.py
Copyright (C) 2022 Tim Hladnik

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
from PySide6 import QtWidgets

from vxpy import calib
from vxpy.calibration_manager import access
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget


class PlanarCalibrationWidget(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.settings = Settings(self)
        self.layout().addWidget(self.settings)

        self.test_visuals = QtWidgets.QWidget()
        self.test_visuals.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.test_visuals)

        self.checker = Checker(self)
        self.test_visuals.layout().addWidget(self.checker)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.test_visuals.layout().addItem(spacer)


class Settings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar')
        self.main = parent

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # X extent
        self.x_extent = DoubleSliderWidget(self, 'X-extent [rel]',
                                           limits=(0., 10.), default=1.,
                                           step_size=.001, decimals=3, label_width=label_width)
        self.x_extent.connect_callback(self.update_x_extent)
        self.layout().addWidget(self.x_extent)

        # Y extent
        self.y_extent = DoubleSliderWidget(self, 'Y-extent [rel]',
                                           limits=(0., 10.), default=1.,
                                           step_size=.001, decimals=3, label_width=label_width)
        self.y_extent.connect_callback(self.update_y_extent)
        self.layout().addWidget(self.y_extent)

        # Small side
        self.small_side = IntSliderWidget(self, 'Small side [mm]',
                                          limits=(1, 1000), default=100, label_width=label_width)
        self.small_side.connect_callback(self.update_small_side)
        self.layout().addWidget(self.small_side)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

        access.window.sig_reload_calibration.connect(self.update_ui)

    @staticmethod
    def update_x_extent(value):
        calib.CALIB_DISP_PLA_EXTENT_X = value
        access.window.display.update_canvas()

    @staticmethod
    def update_y_extent(value):
        calib.CALIB_DISP_PLA_EXTENT_Y = value
        access.window.display.update_canvas()

    @staticmethod
    def update_small_side(value):
        calib.CALIB_DISP_PLA_SMALL_SIDE = value
        access.window.display.update_canvas()

    def update_ui(self):
        self.x_extent.set_value(calib.CALIB_DISP_PLA_EXTENT_X)
        self.y_extent.set_value(calib.CALIB_DISP_PLA_EXTENT_Y)
        self.small_side.set_value(calib.CALIB_DISP_PLA_SMALL_SIDE)


class Checker(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar Checkerboard')
        self.main = parent

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.vertical_sp = IntSliderWidget(self, 'Vertical SP [mm]',
                                           limits=(1, 100), default=10,
                                           step_size=1., label_width=label_width)
        self.layout().addWidget(self.vertical_sp)
        # Horizontal SF
        self.horizontal_sp = IntSliderWidget(self, 'Horizontal SP [mm]',
                                             limits=(1, 100), default=10,
                                             step_size=1, label_width=label_width)
        self.layout().addWidget(self.horizontal_sp)
        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_planar_checkerboard)
        self.layout().addWidget(self.btn_show)

    def show_planar_checkerboard(self):
        from vxpy.visuals.planar_calibration import Sinusoid2d
        vertical_sf = self.vertical_sp.get_value(),
        horizontal_sf = self.horizontal_sp.get_value()
        access.window.display.canvas.set_visual(Sinusoid2d(access.window.display.canvas))
        new_parameters = {Sinusoid2d.u_sp_vertical: vertical_sf,
                          Sinusoid2d.u_sp_horizontal: horizontal_sf,
                          Sinusoid2d.u_checker_pattern: 'Checker'}
        access.window.display.canvas.current_visual.update(new_parameters)
        access.window.display.canvas.current_visual.is_active = True
