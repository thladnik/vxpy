"""
MappApp ./gui/io/__init__.py
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
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg

from vxpy import Def
from vxpy.core import ipc
from vxpy.core.gui import AddonWidget
from vxpy.utils.uiutils import IntSliderWidget
from vxpy.api.attribute import get_attribute_list, get_attribute, read_attribute
from vxpy.api import worker_rpc
from vxpy.routines.worker.calculate_csd import CalculatePSD


class DisplayPSD(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())

        # Attribute selection
        self.attribute_selection = QtWidgets.QComboBox(self)
        for attr_name, attr in get_attribute_list():
            # Only add 1 long ArrayAttributes (ObjectAttributes have shape[0] == None)
            if len(attr.shape) == 1 and attr.shape[0] == 1:
                self.attribute_selection.addItem(attr_name)
        self.attribute_selection.currentTextChanged.connect(self.set_signal_attribute_name)
        self.layout().addWidget(self.attribute_selection)

        # Integration window width
        self.integr_winwidth = QtWidgets.QSpinBox(self)
        self.integr_winwidth.valueChanged.connect(self.set_integration_window_width)
        self.integr_winwidth.setMinimum(2**9)
        self.integr_winwidth.setValue(2**10)
        self.integr_winwidth.setMaximum(9999)
        self.layout().addWidget(self.integr_winwidth)

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.plot_item.setLabel('bottom', text='Frequency', units='Hz')
        self.plot_item.setLabel('left', text='PSD')
        self.data_item: pg.PlotDataItem = self.plot_item.plot([], [])
        self.layout().addWidget(self.plot_widget)

        # Start timer
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000 // 20)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    def set_signal_attribute_name(self, a0):
        worker_rpc(CalculatePSD.set_input_signal, a0, force_overwrite=True)

    def set_integration_window_width(self, a0):
        worker_rpc(CalculatePSD.set_integration_window_width, a0)

    def update_plot(self):
        i, t, f = read_attribute('psd_frequency')
        _, _, p = read_attribute('psd_power')

        self.data_item.setData(x=f.flatten(), y=p.flatten())
