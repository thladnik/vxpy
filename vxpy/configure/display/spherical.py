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

from PyQt6 import QtWidgets

from vxpy.configure import acc
from vxpy import Def
from vxpy.utils.uiutils import DoubleSliderWidget, IntSliderWidget, Checkbox


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


class Parameters(QtWidgets.QWidget):

    def __init__(self, channel_num, settings_wdgt):
        QtWidgets.QWidget.__init__(self)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.settings_wdgt = settings_wdgt
        self.channel_num = channel_num

        self.edits = dict()

        label_width = 150

        # Radial offset
        wdgt = DoubleSliderWidget('Radial offset', 0., 1., 0.,
                                  step_size=.001, decimals=3, label_width=label_width)
        wdgt.connect_to_result(self.update_radial_offset)
        self.edits[Def.DisplayCfg.sph_pos_glob_radial_offset] = wdgt
        self.layout().addWidget(wdgt)

        # Elevation
        wdgt = DoubleSliderWidget('Elevation [deg]', -45., 45., 0.,
                                  step_size=.1, decimals=1, label_width=label_width)
        wdgt.connect_to_result(self.update_elevation)
        self.edits[Def.DisplayCfg.sph_view_elev_angle] = wdgt
        self.layout().addWidget(wdgt)

        # Azimuth
        wdgt = DoubleSliderWidget('Azimuth [deg]', -20., 20., 0.,
                                  step_size=.1, decimals=1, label_width=label_width)
        wdgt.connect_to_result(self.update_azimuth)
        self.edits[Def.DisplayCfg.sph_view_azim_angle] = wdgt
        self.layout().addWidget(wdgt)

        # View distance
        wdgt = DoubleSliderWidget('Distance [norm]', 1., 50., 5.,
                                  step_size=.05, decimals=2, label_width=label_width)
        wdgt.connect_to_result(self.update_view_distance)
        self.edits[Def.DisplayCfg.sph_view_distance] = wdgt
        self.layout().addWidget(wdgt)

        # FOV
        wdgt = DoubleSliderWidget('FOV [deg]', .1, 179., 70.,
                                  step_size=.05, decimals=2, label_width=label_width)
        wdgt.connect_to_result(self.update_view_fov)
        self.edits[Def.DisplayCfg.sph_view_fov] = wdgt
        self.layout().addWidget(wdgt)

        # View scale
        wdgt = DoubleSliderWidget('Scale [norm]', .001, 10., 1.,
                                  step_size=.001, decimals=3, label_width=label_width)
        wdgt.connect_to_result(self.update_view_scale)
        self.edits[Def.DisplayCfg.sph_view_scale] = wdgt
        self.layout().addWidget(wdgt)

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

    def update_edit(self, key, value):
        self.edits[key].set_value(value)

    def update_radial_offset(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_pos_glob_radial_offset, value)

    def update_elevation(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_view_elev_angle, value)

    def update_azimuth(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_view_azim_angle, value)

    def update_view_distance(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_view_distance, value)

    def update_view_fov(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_view_fov, value)

    def update_view_scale(self, value):
        self.settings_wdgt.update_config(self.channel_num, Def.DisplayCfg.sph_view_scale, value)


class Settings(QtWidgets.QWidget):

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self)
        self.main = parent

        self.setLayout(QtWidgets.QVBoxLayout())

        self.azimuth_orient = DoubleSliderWidget('Azimuth orientation [deg]', 0., 360, 0., step_size=.1, decimals=1,
                                                 label_width=200)
        self.azimuth_orient.connect_to_result(self.update_azimuth_orient)
        self.layout().addWidget(self.azimuth_orient)

        self.global_overwrite = Checkbox('Global overwrite', False, label_width=200)
        self.global_overwrite.checkbox.stateChanged.connect(self.toggle_overwrite)
        self.layout().addWidget(self.global_overwrite)

        # Set channels
        self.tabs = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tabs)
        self.channels = {i - 1: Parameters(i - 1, self) for i in range(5)}
        for channel_num, channel_wdgt in self.channels.items():
            self.tabs.addTab(channel_wdgt, str(channel_num) if channel_num >= 0 else 'Global')
        self.tabs.setTabEnabled(0, False)

        # Connect reload config signal
        acc.main.sig_reload_config.connect(self.reload_config)

    def reload_config(self):
        section = Def.DisplayCfg.name

        parameters = [Def.DisplayCfg.sph_pos_glob_radial_offset,
                      Def.DisplayCfg.sph_view_elev_angle,
                      Def.DisplayCfg.sph_view_azim_angle,
                      Def.DisplayCfg.sph_view_distance,
                      Def.DisplayCfg.sph_view_fov,
                      Def.DisplayCfg.sph_view_scale]

        for key, value in zip(parameters, [acc.cur_conf.getParsed(section, key) for key in parameters]):
            # By default set "global overwrite" channel to 0 channel parameters
            self.channels[-1].update_edit(key, value[0])

            # Update all channels
            for i, v in enumerate(value):
                self.channels[i].update_edit(key, v)

    def toggle_overwrite(self, newstate):
        self.tabs.setTabEnabled(0, newstate)

    def update_azimuth_orient(self, value):
        acc.cur_conf.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.sph_view_azim_orient, value)
        acc.display.update_canvas()

    def update_config(self, channel_num, key, value):
        section = Def.DisplayCfg.name

        # Fetch current config
        conf = acc.cur_conf.getParsed(section, key)
        # Alter
        if channel_num >= 0:
            conf[channel_num] = value
        else:
            conf = [value for _ in conf]

        # Update config
        acc.cur_conf.setParsed(section, key, conf)

        # Trigger reload on other channels
        acc.main.sig_reload_config.emit()

        acc.display.update_canvas()


class Mesh(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical mesh')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget('Elevation SP [deg]', 1, 180, 22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget('Azimuth SP [deg]', 1, 360, 22.5,
                                             step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.azimuth_sp)

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def show_visual(self):
        from vxpy.visuals.spherical.calibration import RegularMesh
        elevation_sp = self.elevation_sp.get_value()
        azimuth_sp = self.azimuth_sp.get_value()
        acc.display.canvas.visual = RegularMesh(acc.display.canvas)
        acc.display.canvas.visual.update(**{RegularMesh.u_elevation_sp: elevation_sp,
                                            RegularMesh.u_azimuth_sp: azimuth_sp})


class Checker(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical checkerboard')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget('Elevation SP [deg]', 1, 180, 22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget('Azimuth SP [deg]', 1, 360, 22.5,
                                             step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.azimuth_sp)

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def show_visual(self):
        from vxpy.visuals.spherical.calibration import BlackWhiteCheckerboard
        elevation_sp = self.elevation_sp.get_value()
        azimuth_sp = self.azimuth_sp.get_value()
        acc.display.canvas.visual = BlackWhiteCheckerboard(acc.display.canvas)
        acc.display.canvas.visual.update(**{BlackWhiteCheckerboard.u_elevation_sp: elevation_sp,
                                            BlackWhiteCheckerboard.u_azimuth_sp: azimuth_sp})
