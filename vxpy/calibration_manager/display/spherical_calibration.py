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
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget, Checkbox


class SphericalCalibrationWidget(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.settings = Settings(self)
        self.layout().addWidget(self.settings)

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


class ChannelParameters(QtWidgets.QWidget):

    def __init__(self, channel_num, settings_widget):
        QtWidgets.QWidget.__init__(self)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.settings_widget = settings_widget
        self.channel_num = channel_num

        self.edits = dict()

        label_width = 150

        # Radial offset
        wdgt = DoubleSliderWidget('Radial offset', 0., 1., 0.,
                                  step_size=.001, decimals=3, label_width=label_width)
        wdgt.connect_to_result(self.radial_offset_updated)
        self.edits['CALIB_DISP_SPH_POS_RADIAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Lateral offset
        wdgt = DoubleSliderWidget('Lateral offset', -1., 1., 0.,
                                  step_size=.001, decimals=3, label_width=label_width)
        wdgt.connect_to_result(self.lateral_offset_updated)
        self.edits['CALIB_DISP_SPH_POS_LATERAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Elevation
        wdgt = DoubleSliderWidget('Elevation [deg]', -45., 45., 0.,
                                  step_size=.1, decimals=1, label_width=label_width)
        wdgt.connect_to_result(self.elevation_updated)
        self.edits['CALIB_DISP_SPH_VIEW_ELEV_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # Azimuth
        wdgt = DoubleSliderWidget('Azimuth [deg]', -20., 20., 0.,
                                  step_size=.1, decimals=1, label_width=label_width)
        wdgt.connect_to_result(self.azimuth_updated)
        self.edits['CALIB_DISP_SPH_VIEW_AZIM_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # View distance
        wdgt = DoubleSliderWidget('Distance [norm]', 1., 50., 5.,
                                  step_size=.05, decimals=2, label_width=label_width)
        wdgt.connect_to_result(self.view_distance_updated)
        self.edits['CALIB_DISP_SPH_VIEW_DISTANCE'] = wdgt
        self.layout().addWidget(wdgt)

        # FOV
        wdgt = DoubleSliderWidget('FOV [deg]', .1, 179., 70.,
                                  step_size=.05, decimals=2, label_width=label_width)
        wdgt.connect_to_result(self.view_fov_updated)
        self.edits['CALIB_DISP_SPH_VIEW_FOV'] = wdgt
        self.layout().addWidget(wdgt)

        # View scale
        wdgt = DoubleSliderWidget('Scale [norm]', .001, 10., 1.,
                                  step_size=.001, decimals=3, label_width=label_width)
        wdgt.connect_to_result(self.view_scale_updated)
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

        self.setLayout(QtWidgets.QVBoxLayout())

        self.azimuth_orient = DoubleSliderWidget('Azimuth orientation [deg]', 0., 360, 0., step_size=.1, decimals=1,
                                                 label_width=200)
        self.azimuth_orient.connect_to_result(self.update_azimuth_orient)
        self.layout().addWidget(self.azimuth_orient)

        self.lat_lum_offset = DoubleSliderWidget('Lateral luminance offset', 0., 1., 0., step_size=.01, decimals=2,
                                                 label_width=200)
        self.lat_lum_offset.connect_to_result(self.update_lat_lum_offset)
        self.layout().addWidget(self.lat_lum_offset)

        self.lat_lum_gradient = DoubleSliderWidget('Lateral luminance gradient', 0., 10., 1., step_size=.05, decimals=2,
                                                   label_width=200)
        self.lat_lum_gradient.connect_to_result(self.update_lat_lum_gradient)
        self.layout().addWidget(self.lat_lum_gradient)

        self.global_overwrite = Checkbox('Global overwrite', False, label_width=200)
        self.global_overwrite.checkbox.stateChanged.connect(self.toggle_overwrite)
        self.layout().addWidget(self.global_overwrite)

        # Set channels
        self.tabs = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tabs)
        self.channels = {str(i - 1): ChannelParameters(i - 1, self) for i in range(5)}
        for channel_num, channel_wdgt in self.channels.items():
            self.tabs.addTab(channel_wdgt, str(channel_num) if int(channel_num) >= 0 else 'Global')
        self.tabs.setTabEnabled(0, False)

        # Connect reload config signal
        access.window.sig_reload_calibration.connect(self.reload_calibration)

    def reload_calibration(self):
        self.azimuth_orient.set_value(calib.CALIB_DISP_SPH_VIEW_AZIM_ORIENT)
        self.lat_lum_offset.set_value(calib.CALIB_DISP_SPH_LAT_LUM_OFFSET)
        self.lat_lum_gradient.set_value(calib.CALIB_DISP_SPH_LAT_LUM_GRADIENT)

        # Update UI for individual channels
        for key, values in zip(self.channel_params, [getattr(calib, key) for key in self.channel_params]):
            # By default set "global overwrite" channel to 0 channel parameters
            self.channels['-1'].update_ui_edit(key, values[0])

            # Update all channels
            for i, v in enumerate(values):
                self.channels[str(i)].update_ui_edit(key, v)

    def toggle_overwrite(self, newstate):
        self.tabs.setTabEnabled(0, newstate)

        # if not newstate:
        #     return
        #
        # # Write channel 0 to global overwrite channel in UI
        # for key, values in zip(self.channel_params, [getattr(calib, key) for key in self.channel_params]):
        #     print(f'Write {key=} to {values[0]=}')
        #     self.channels['-1'].update_ui_edit(key, values[0])

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
        access.window.sig_reload_calibration.emit()

        access.window.display.update_canvas()


class Mesh(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical mesh')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget('Elevation SP [deg]', 1., 180., 22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget('Azimuth SP [deg]', 1., 360., 15.,
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
        access.window.display.canvas.current_visual.update({RegularMesh.u_elevation_sp: elevation_sp,
                                                            RegularMesh.u_azimuth_sp: azimuth_sp})


class Checker(QtWidgets.QGroupBox):
    def __init__(self, main):
        QtWidgets.QGroupBox.__init__(self, 'Spherical checkerboard')
        self.main = main

        label_width = 150

        self.setLayout(QtWidgets.QVBoxLayout())

        # Vertical SP
        self.elevation_sp = DoubleSliderWidget('Elevation SP [deg]', 1., 180., 22.5,
                                               step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.elevation_sp)

        # Horizontal SP
        self.azimuth_sp = DoubleSliderWidget('Azimuth SP [deg]', 1., 360., 15.,
                                             step_size=0.1, decimals=1, label_width=label_width)
        self.layout().addWidget(self.azimuth_sp)

        # Show button
        self.btn_show = QtWidgets.QPushButton('Show')
        self.btn_show.clicked.connect(self.show_visual)
        self.layout().addWidget(self.btn_show)

    def show_visual(self):
        from vxpy.visuals.spherical_calibration import BlackWhiteCheckerboard
        print('Show?')
        elevation_sp = self.elevation_sp.get_value()
        azimuth_sp = self.azimuth_sp.get_value()
        access.window.display.canvas.set_visual(BlackWhiteCheckerboard(access.window.display.canvas))
        access.window.display.canvas.current_visual.update({BlackWhiteCheckerboard.u_elevation_sp: elevation_sp,
                                                            BlackWhiteCheckerboard.u_azimuth_sp: azimuth_sp})
