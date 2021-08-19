"""
MappApp ./setup/spherical.py
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

from PyQt5 import QtWidgets

from mappapp.setup import acc
from mappapp import Def
from mappapp.utils.gui import DoubleSliderWidget, IntSliderWidget

class Main(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.setLayout(QtWidgets.QGridLayout())
        self.settings = Settings(self)
        self.layout().addWidget(self.settings, 0, 0, 2, 1)

        self.mesh = Mesh(self)
        self.layout().addWidget(self.mesh, 0, 1)

        self.checker = Checker(self)
        self.layout().addWidget(self.checker, 1, 1)


class Settings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Spherical')
        self.main = parent
        self.setLayout(QtWidgets.QVBoxLayout())

        label_width = 150

        # Radial offset
        self.radial_offset = DoubleSliderWidget('Radial offset',-1.,1.,0.,
                                                step_size=.001,decimals=3,label_width=label_width)
        self.radial_offset.connect_to_result(self.update_radial_offset)
        self.layout().addWidget(self.radial_offset)

        # Elevation
        self.view_elev_angle = DoubleSliderWidget('Elevation [deg]',-90.,90.,0.,
                                                  step_size=.1,decimals=1,label_width=label_width)
        self.view_elev_angle.connect_to_result(self.update_elevation)
        self.layout().addWidget(self.view_elev_angle)

        # Azimuth
        self.view_azim_angle = DoubleSliderWidget('Azimuth [deg]',-180.,180.,0.,
                                                  step_size=.1,decimals=1,label_width=label_width)
        self.view_azim_angle.connect_to_result(self.update_azimuth)
        self.layout().addWidget(self.view_azim_angle)

        # View distance
        self.view_distance = DoubleSliderWidget('Distance [norm]',1.,50.,5.,
                                                step_size=.05,decimals=2,label_width=label_width)
        self.view_distance.connect_to_result(self.update_view_distance)
        self.layout().addWidget(self.view_distance)

        # FOV
        self.view_fov = DoubleSliderWidget('FOV [deg]',.1,179.,70.,
                                           step_size=.05,decimals=2,label_width=label_width)
        self.view_fov.connect_to_result(self.update_view_fov)
        self.layout().addWidget(self.view_fov)

        # View scale
        self.view_scale = DoubleSliderWidget('Scale [norm]',.001,10.,1.,
                                             step_size=.001,decimals=3,label_width=label_width)
        self.view_scale.connect_to_result(self.update_view_scale)
        self.layout().addWidget(self.view_scale)

        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(spacer)

        # Connect reload config signal
        acc.main.sig_reload_config.connect(self.reload_config)

    def reload_config(self):
        section = Def.DisplayCfg.name

        self.radial_offset.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_pos_glob_radial_offset))
        self.view_elev_angle.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_view_elev_angle))
        self.view_azim_angle.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_view_azim_angle))
        self.view_distance.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_view_distance))
        self.view_fov.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_view_fov))
        self.view_scale.set_value(acc.cur_conf.getParsed(section, Def.DisplayCfg.sph_view_scale))

    def update_radial_offset(self, offset):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_pos_glob_radial_offset,
                               offset)
        acc.display.update_canvas()

    def update_elevation(self, elevation):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_view_elev_angle,
                               elevation)
        acc.display.update_canvas()

    def update_azimuth(self, azimuth):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_view_azim_angle,
                               azimuth)
        acc.display.update_canvas()

    def update_view_distance(self, distance):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_view_distance,
                               distance)
        acc.display.update_canvas()

    def update_view_fov(self, fov):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_view_fov,
                               fov)
        acc.display.update_canvas()

    def update_view_scale(self, scale):
        acc.cur_conf.setParsed(Def.DisplayCfg.name,
                               Def.DisplayCfg.sph_view_scale,
                               scale)
        acc.display.update_canvas()


class Mesh(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical mesh')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.elevation_sf = DoubleSliderWidget('Elevation SF [1/deg]', .001, 1., .1,
                                               step_size=.001, decimals=3, label_width=label_width)
        self.elevation_sf.connect_to_result(self.update_elevation_sp)
        self.layout().addWidget(self.elevation_sf)
        # Vertical SP
        self.elevation_sp = QtWidgets.QLineEdit('')
        self.elevation_sp.setDisabled(True)
        self.layout().addWidget(self.elevation_sp)
        self.elevation_sf.emit_current_value()

        # Horizontal SF
        self.azimuth_sf = DoubleSliderWidget('Azimuth SF [1/deg]', .001, 1., .1,
                                             step_size=.001, decimals=3, label_width=label_width)
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
        acc.display.canvas.visual = RegularMesh(acc.display.canvas,
                                                **{RegularMesh.u_elevation_sf: elevation_sf,
                                                 RegularMesh.u_azimuth_sf: azimuth_sf})


class Checker(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical checkerboard')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SF
        self.elevation_sf = DoubleSliderWidget('Elevation SF [1/deg]', .001, 1., .1,
                                               step_size=.001, decimals=3, label_width=label_width)
        self.elevation_sf.connect_to_result(self.update_elevation_sp)
        self.layout().addWidget(self.elevation_sf)
        # Vertical SP
        self.elevation_sp = QtWidgets.QLineEdit('')
        self.elevation_sp.setDisabled(True)
        self.layout().addWidget(self.elevation_sp)
        self.elevation_sf.emit_current_value()

        # Horizontal SF
        self.azimuth_sf = DoubleSliderWidget('Azimuth SF [1/deg]', .001, 1., .1,
                                             step_size=.001, decimals=3, label_width=label_width)
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
        acc.display.canvas.visual = BlackWhiteCheckerboard(
            acc.display.canvas,
            **{BlackWhiteCheckerboard.u_elevation_sf: elevation_sf,
               BlackWhiteCheckerboard.u_azimuth_sf: azimuth_sf})
