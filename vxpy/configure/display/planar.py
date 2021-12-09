"""
MappApp ./setup/planar.py
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

from PySide6 import QtWidgets

from vxpy.configure import acc
from vxpy.Def import *
from vxpy import Def
from vxpy.utils.uiutils import DoubleSliderWidget, IntSliderWidget


class Main(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.setLayout(QtWidgets.QGridLayout())
        self.settings = Settings(self)
        self.layout().addWidget(self.settings, 0, 0, 2, 1)

        self.checker = Checker(self)
        self.layout().addWidget(self.checker, 0, 1)


class Settings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar')
        self.main = parent

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # X extent
        self.x_extent = DoubleSliderWidget('X-extent [rel]', 0., 10., 1.,
                                                     step_size=.001, decimals=3, label_width=label_width)
        self.x_extent.connect_to_result(self.update_x_extent)
        self.layout().addWidget(self.x_extent)

        # Y extent
        self.y_extent = DoubleSliderWidget('Y-extent [rel]', 0., 10., 1.,
                                                     step_size=.001, decimals=3, label_width=label_width)
        self.y_extent.connect_to_result(self.update_y_extent)
        self.layout().addWidget(self.y_extent)

        # Small side
        self.small_side = IntSliderWidget('Small side [mm]', 1, 1000, 100, label_width=label_width)
        self.small_side.connect_to_result(self.update_small_side)
        self.layout().addWidget(self.small_side)

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

        # Connect reload config signal
        acc.main.sig_reload_config.connect(self.reload_config)

    def reload_config(self):
        section = Def.DisplayCfg.name

        self.x_extent.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.pla_xextent))
        self.y_extent.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.pla_yextent))
        self.small_side.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.pla_small_side))

    def update_x_extent(self, x_extent):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.pla_xextent,
                               x_extent)
        acc.display.update_canvas()

    def update_y_extent(self, y_extent):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.pla_yextent,
                               y_extent)
        acc.display.update_canvas()

    def update_small_side(self, small_side):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.pla_small_side,
                               small_side)
        acc.display.update_canvas()


class Checker(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar Checkerboard')
        self.main = parent

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.vertical_sp = IntSliderWidget('Vertical SP [mm]', 1, 100, 10,
                                           step_size=1., label_width=label_width)
        self.layout().addWidget(self.vertical_sp)
        # Horizontal SF
        self.horizontal_sp = IntSliderWidget('Horizontal SP [mm]', 1, 100, 10,
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
        acc.display.canvas.visual = Sinusoid2d(acc.display.canvas)
        acc.display.canvas.visual.update(**{Sinusoid2d.u_sp_vertical: vertical_sf,
                                            Sinusoid2d.u_sp_horizontal: horizontal_sf,
                                            Sinusoid2d.u_checker_pattern: True})
