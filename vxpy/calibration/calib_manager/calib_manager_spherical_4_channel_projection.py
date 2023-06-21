from __future__ import annotations
from typing import Any, Dict, List

from PySide6 import QtWidgets

from vxpy.definitions import *
from vxpy import calibration, definitions, calib
from vxpy.utils.widgets import DoubleSliderWidget, IntSliderWidget, Checkbox, UniformWidth
from vxpy.calibration.calib_manager.calibration_utils import VisualInteractorCalibWidget


class Spherical4ChannelProjectionCalibration(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.settings = Settings(self)
        self.layout().addWidget(self.settings)


class Settings(QtWidgets.QWidget):

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
        self.layout().addWidget(self.channel_independent, 0, 0)

        self.uniform_width_label = UniformWidth()
        self.uniform_width_spinner = UniformWidth()

        self.azimuth_orient = DoubleSliderWidget(self, 'Azimuth orientation [deg]',
                                                 limits=(0., 360), default=0., step_size=.1, decimals=1)
        self.azimuth_orient.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_AZIM_ORIENT'))
        self.uniform_width_label.add_widget(self.azimuth_orient.label)
        self.uniform_width_spinner.add_widget(self.azimuth_orient.spinner)
        self.channel_independent.layout().addWidget(self.azimuth_orient)

        self.lat_lum_offset = DoubleSliderWidget(self, 'Lateral luminance offset',
                                                 limits=(0., 1.), default=0., step_size=.01, decimals=2,
                                                 label_width=200)
        self.lat_lum_offset.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_LAT_LUM_OFFSET'))
        self.uniform_width_label.add_widget(self.lat_lum_offset.label)
        self.uniform_width_spinner.add_widget(self.lat_lum_offset.spinner)
        self.channel_independent.layout().addWidget(self.lat_lum_offset)

        self.lat_lum_gradient = DoubleSliderWidget(self, 'Lateral luminance gradient',
                                                   limits=(0., 10.), default=1., step_size=.05, decimals=2,
                                                   label_width=200)
        self.lat_lum_gradient.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_LAT_LUM_GRADIENT'))
        self.uniform_width_label.add_widget(self.lat_lum_gradient.label)
        self.uniform_width_spinner.add_widget(self.lat_lum_gradient.spinner)
        self.channel_independent.layout().addWidget(self.lat_lum_gradient)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
        self.channel_independent.layout().addItem(spacer)

        self.visual_interactor = VisualInteractorCalibWidget()
        self.layout().addWidget(self.visual_interactor, 1, 0)

        # Set channels
        self.channel_widgets = QtWidgets.QWidget()
        self.channel_widgets.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.channel_widgets)

        # Add individual channel calibration widgets
        self.individual_channels = [ChannelParameters(i, self) for i in range(4)]
        self.layout().addWidget(self.individual_channels[0], 0, 1)
        self.layout().addWidget(self.individual_channels[1], 0, 2)
        self.layout().addWidget(self.individual_channels[2], 1, 1)
        self.layout().addWidget(self.individual_channels[3], 1, 2)

    @staticmethod
    def set_parameter_callback(name: str):
        def _parameter_callback(value):
            calib.__dict__[name] = value

        return _parameter_callback


class ChannelParameters(QtWidgets.QGroupBox):

    all: List[ChannelParameters] = []

    def __init__(self, channel_num, settings_widget):
        name = f'Channel {channel_num}'
        self.all.append(self)

        QtWidgets.QGroupBox.__init__(self, name)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.settings_widget = settings_widget
        self.channel_num = channel_num

        self.edits: Dict[str, DoubleSliderWidget] = {}

        self.uniform_width = UniformWidth()
        self.uniform_width_spinner = UniformWidth()

        # Radial offset
        wdgt = DoubleSliderWidget(self, 'Radial offset',
                                  limits=(0., 1.), default=0.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_POS_RADIAL_OFFSET'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_POS_RADIAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Lateral offset
        wdgt = DoubleSliderWidget(self, 'Lateral offset',
                                  limits=(-1., 1.), default=0.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_POS_LATERAL_OFFSET'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_POS_LATERAL_OFFSET'] = wdgt
        self.layout().addWidget(wdgt)

        # Elevation
        wdgt = DoubleSliderWidget(self, 'Elevation [deg]',
                                  limits=(-45., 45.), default=0.,
                                  step_size=.1, decimals=1)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_ELEV_ANGLE'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_VIEW_ELEV_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # Azimuth
        wdgt = DoubleSliderWidget(self, 'Azimuth [deg]',
                                  limits=(-20., 20.), default=0.,
                                  step_size=.1, decimals=1)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_AZIM_ANGLE'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_VIEW_AZIM_ANGLE'] = wdgt
        self.layout().addWidget(wdgt)

        # View distance
        wdgt = DoubleSliderWidget(self, 'Distance [norm]',
                                  limits=(1., 50.), default=5.,
                                  step_size=.05, decimals=2)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_DISTANCE'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_VIEW_DISTANCE'] = wdgt
        self.layout().addWidget(wdgt)

        # FOV
        wdgt = DoubleSliderWidget(self, 'FOV [deg]',
                                  limits=(.1, 179.), default=70.,
                                  step_size=.05, decimals=2)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_FOV'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_VIEW_FOV'] = wdgt
        self.layout().addWidget(wdgt)

        # View scale
        wdgt = DoubleSliderWidget(self, 'Scale [norm]',
                                  limits=(.001, 10.), default=1.,
                                  step_size=.001, decimals=3)
        wdgt.connect_callback(self.set_parameter_callback('CALIB_DISP_SPH_VIEW_SCALE'))
        self.uniform_width.add_widget(wdgt.label)
        self.uniform_width_spinner.add_widget(wdgt.spinner)
        self.edits['CALIB_DISP_SPH_VIEW_SCALE'] = wdgt
        self.layout().addWidget(wdgt)

        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                       QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

        self.update_parameters()

    def set_parameter_callback(self, name: str):
        def _parameter_callback(value):
            calib.__dict__[name][self.channel_num] = value

        return _parameter_callback

    def update_parameters(self):

        current_calib_dict = calibration.get_calibration_data()
        for name, w in self.edits.items():
            # Load calibration for channel
            w.set_value(current_calib_dict[name][self.channel_num])
