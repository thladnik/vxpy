"""
MappApp ./setup/spherical_calibration.py
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
from typing import Any

from PySide6 import QtWidgets

from vxpy.calibration_manager import access
from vxpy.definitions import *
from vxpy import definitions, calib
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget, Checkbox, UniformWidth


class SphericalCalibrationWidget(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        # Settings on the left
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.setStretch(0, 5)
        self.setLayout(hlayout)
        self.settings = Settings(self)
        self.layout().addWidget(self.settings)

        # Test visuals on the right
        self.test_visuals = QtWidgets.QWidget()
        self.test_visuals.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.test_visuals)

        self.mesh = Mesh(self)
        self.test_visuals.layout().addWidget(self.mesh)

        self.checker = Checker(self)
        self.test_visuals.layout().addWidget(self.checker)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.test_visuals.layout().addItem(spacer)


class ChannelParameters(QtWidgets.QGroupBox):

    def __init__(self, channel_num, settings_widget):
        QtWidgets.QGroupBox.__init__(self, f'Channel {channel_num}')
        self.setLayout(QtWidgets.QVBoxLayout())

        self.settings_widget = settings_widget
        self.channel_num = channel_num

        self.edits = dict()

        self.uniform_width = UniformWidth()


        # Radial offset
        wdgt = DoubleSliderWidget(self, 'Radial offset',
                                  limits=(0., 1.), default=0.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.radial_offset_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_POS_RADIAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Lateral offset
        wdgt = DoubleSliderWidget(self, 'Lateral offset',
                                  limits=(-1., 1.), default=0.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.lateral_offset_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_POS_LATERAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Elevation
        wdgt = DoubleSliderWidget(self, 'Elevation [deg]',
                                  limits=(-45., 45.), default=0.,
                                  step_size=.1, decimals=1)
        wdgt.connect_callback(self.elevation_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_VIEW_ELEV_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # Azimuth
        wdgt = DoubleSliderWidget(self, 'Azimuth [deg]',
                                  limits=(-20., 20.), default=0.,
                                  step_size=.1, decimals=1)
        wdgt.connect_callback(self.azimuth_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_VIEW_AZIM_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # View distance
        wdgt = DoubleSliderWidget(self, 'Distance [norm]',
                                  limits=(1., 50.), default=5.,
                                  step_size=.05, decimals=2)
        wdgt.connect_callback(self.view_distance_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_VIEW_DISTANCE'] = wdgt
        self.layout().addWidget(wdgt)

        # FOV
        wdgt = DoubleSliderWidget(self, 'FOV [deg]',
                                  limits=(.1, 179.), default=70.,
                                  step_size=.05, decimals=2)
        wdgt.connect_callback(self.view_fov_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_VIEW_FOV'] = wdgt
        self.layout().addWidget(wdgt)

        # View scale
        wdgt = DoubleSliderWidget(self, 'Scale [norm]',
                                  limits=(.001, 10.), default=1.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.view_scale_updated)
        self.uniform_width.add_widget(wdgt.label)
        self.edits['CALIB_DISP_SPH_VIEW_SCALE'] = wdgt
        self.layout().addWidget(wdgt)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

    def update_ui_edit(self, key, value):
        self.edits[key].set_value(value)

    def radial_offset_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_POS_RADIAL_OFFSET', value)

    def lateral_offset_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_POS_LATERAL_OFFSET', value)

    def elevation_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_VIEW_ELEV_ANGLE', value)

    def azimuth_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_VIEW_AZIM_ANGLE', value)

    def view_distance_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_VIEW_DISTANCE', value)

    def view_fov_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_VIEW_FOV', value)

    def view_scale_updated(self, value):
        self.settings_widget.update_calibration(self.channel_num, 'CALIB_DISP_SPH_VIEW_SCALE', value)


class Settings(QtWidgets.QWidget):
    # TODO: there is a bug here that causes multiple recursions/stack overflow
    #  and ultimately results in a crash when values in channel -1 or 0
    #  are changed in quick succession. It doesn't affect normal everyday operation.

    channel_params = ['CALIB_DISP_SPH_POS_RADIAL_OFFSET',
                      'CALIB_DISP_SPH_POS_LATERAL_OFFSET',
                      'CALIB_DISP_SPH_VIEW_ELEV_ANGLE',
                      'CALIB_DISP_SPH_VIEW_AZIM_ANGLE',
                      'CALIB_DISP_SPH_VIEW_DISTANCE',
                      'CALIB_DISP_SPH_VIEW_FOV',
                      'CALIB_DISP_SPH_VIEW_SCALE']

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.main = parent

        self.setLayout(QtWidgets.QGridLayout())

        # Add channel-independent settings
        self.channel_independent = QtWidgets.QGroupBox('Channel independent settings')
        self.channel_independent.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.channel_independent)

        self.uniform_width = UniformWidth()

        self.azimuth_orient = DoubleSliderWidget(self, 'Azimuth orientation [deg]',
                                                 limits=(0., 360), default=0., step_size=.1, decimals=1)
        self.azimuth_orient.connect_callback(self.update_azimuth_orient)
        self.uniform_width.add_widget(self.azimuth_orient.label)
        self.channel_independent.layout().addWidget(self.azimuth_orient)

        self.lat_lum_offset = DoubleSliderWidget(self, 'Lateral luminance offset',
                                                 limits=(0., 1.), default=0., step_size=.01, decimals=2,
                                                 label_width=200)
        self.lat_lum_offset.connect_callback(self.update_lat_lum_offset)
        self.uniform_width.add_widget(self.lat_lum_offset.label)
        self.channel_independent.layout().addWidget(self.lat_lum_offset)

        self.lat_lum_gradient = DoubleSliderWidget(self, 'Lateral luminance gradient',
                                                   limits=(0., 10.), default=1., step_size=.05, decimals=2,
                                                   label_width=200)
        self.lat_lum_gradient.connect_callback(self.update_lat_lum_gradient)
        self.uniform_width.add_widget(self.lat_lum_gradient.label)
        self.channel_independent.layout().addWidget(self.lat_lum_gradient)

        # Set channels
        self.channel_tab_widget = QtWidgets.QTabWidget(self)
        self.layout().addWidget(self.channel_tab_widget)

        # Add global overwrite channel
        self.global_overwrite_channel = ChannelParameters(-1, self)
        self.channel_tab_widget.addTab(self.global_overwrite_channel, 'Global overwrite')

        # Add individual channel calibration widgets
        self.individual_channels = QtWidgets.QWidget()
        self.channels = [ChannelParameters(i, self) for i in range(4)]
        self.individual_channels.setLayout(QtWidgets.QGridLayout())
        self.individual_channels.layout().addWidget(self.channels[0], 0, 1)
        self.individual_channels.layout().addWidget(self.channels[1], 1, 1)
        self.individual_channels.layout().addWidget(self.channels[2], 1, 0)
        self.individual_channels.layout().addWidget(self.channels[3], 0, 0)
        self.channel_tab_widget.addTab(self.individual_channels, 'Channels')

        # Select individual channels
        self.channel_tab_widget.setCurrentWidget(self.individual_channels)

        # Connect reload config signal
        access.window.sig_reload_calibration.connect(self.reload_calibration)

    def reload_calibration(self):
        self.azimuth_orient.set_value(calib.CALIB_DISP_SPH_VIEW_AZIM_ORIENT)
        self.lat_lum_offset.set_value(calib.CALIB_DISP_SPH_LAT_LUM_OFFSET)
        self.lat_lum_gradient.set_value(calib.CALIB_DISP_SPH_LAT_LUM_GRADIENT)

        # Update UI for individual channels
        for key, values in zip(self.channel_params, [getattr(calib, key) for key in self.channel_params]):
            # By default set "global overwrite" channel to 0 channel parameters
            # self.channels['-1'].update_ui_edit(key, values[0])

            # Update all channels
            for i, v in enumerate(values):
                self.channels[i].update_ui_edit(key, v)

    @staticmethod
    def update_azimuth_orient(value):
        calib.CALIB_DISP_SPH_VIEW_AZIM_ORIENT = value
        access.window.display.update_canvas()

    @staticmethod
    def update_lat_lum_offset(value):
        calib.CALIB_DISP_SPH_LAT_LUM_OFFSET = value
        access.window.display.update_canvas()

    @staticmethod
    def update_lat_lum_gradient(value):
        calib.CALIB_DISP_SPH_LAT_LUM_GRADIENT = value
        access.window.display.update_canvas()

    @staticmethod
    def update_calibration(channel_num: int, key: str, value: Any):

        # Fetch current config
        _calib = getattr(calib, key)
        # Alter
        if channel_num >= 0:
            _calib[channel_num] = value
        else:
            _calib = [value] * len(_calib)

        # Update config
        setattr(calib, key, _calib)

        # Trigger reload on other channels
        # access.window.sig_reload_calibration.emit()

        access.window.display.update_canvas()


class Mesh(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical mesh')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget(self, 'Elevation SP [deg]',
                                               limits=(1., 180.), default=22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget(self, 'Azimuth SP [deg]',
                                             limits=(1., 360.), default=22.5,
                                             step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.azimuth_sp)

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def show_visual(self):
        from vxpy.visuals.spherical_calibration import RegularMesh
        elevation_sp = self.elevation_sp.get_value()
        azimuth_sp = self.azimuth_sp.get_value()
        access.window.display.canvas.set_visual(RegularMesh(access.window.display.canvas))
        new_parameters = {RegularMesh.u_elevation_sp: elevation_sp,
                          RegularMesh.u_azimuth_sp: azimuth_sp}
        access.window.display.canvas.current_visual.update(new_parameters)
        access.window.display.canvas.current_visual.is_active = True


class Checker(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical checkerboard')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget(self, 'Elevation SP [deg]',
                                               limits=(1., 180.), default=22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget(self, 'Azimuth SP [deg]',
                                             limits=(1., 360.), default=22.5,
                                             step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.azimuth_sp)

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def show_visual(self):
        from vxpy.visuals.spherical_calibration import BlackWhiteCheckerboard
        elevation_sp = self.elevation_sp.get_value()
        azimuth_sp = self.azimuth_sp.get_value()
        access.window.display.canvas.set_visual(BlackWhiteCheckerboard(access.window.display.canvas))
        new_parameters = {BlackWhiteCheckerboard.u_elevation_sp: elevation_sp,
                          BlackWhiteCheckerboard.u_azimuth_sp: azimuth_sp}
        access.window.display.canvas.current_visual.update(new_parameters)
        access.window.display.canvas.current_visual.is_active = True
