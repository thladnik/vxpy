"""
MappApp ./gui/io/display_calibration.py
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
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg

from vxpy.definitions import *
from vxpy import definitions
from vxpy.core import ipc
from vxpy.core.gui import AddonWidget
from vxpy.utils.uiutils import IntSliderWidget
from vxpy.api.attribute import get_attribute_list, get_attribute, read_attribute
from vxpy.api import worker_rpc
from vxpy.routines.worker.calculate_csd import CalculatePSD


class DisplayPSD(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())

        self.attribute_names = []
        # Attribute selection
        self.layout().addWidget(QtWidgets.QLabel('Attribute'), 0, 0)
        self.attribute_selection = QtWidgets.QComboBox(self)
        self.attribute_selection.currentTextChanged.connect(self.set_signal_attribute_name)
        self.layout().addWidget(self.attribute_selection, 0, 1)

        # Integration window width
        self.layout().addWidget(QtWidgets.QLabel('Integration window size'), 1, 0)
        self.integr_winwidth = QtWidgets.QComboBox()
        for i in range(6):
            m = 2**i * CalculatePSD.nperseg
            self.integr_winwidth.addItem(str(m), userData=m)
        self.integr_winwidth.currentIndexChanged.connect(self.set_integration_window_width)
        self.integr_winwidth.currentIndexChanged.emit(0)
        self.layout().addWidget(self.integr_winwidth, 1, 1)

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.plot_item.setLabel('bottom', text='Frequency', units='Hz')
        self.plot_item.setLabel('left', text='PSD')
        self.data_item: pg.PlotDataItem = self.plot_item.plot([], [])
        self.layout().addWidget(self.plot_widget, 2, 0, 1, 2)

        # Start timer
        self.plot_timer = QtCore.QTimer()
        self.plot_timer.setInterval(1000 // 10)
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start()

        self.ui_timer = QtCore.QTimer()
        self.ui_timer.setInterval(1000 // 2)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start()

    def set_signal_attribute_name(self, a0):
        worker_rpc(CalculatePSD.set_input_signal, a0, force_overwrite=True)

    def set_integration_window_width(self, a0):
        worker_rpc(CalculatePSD.set_integration_window_width, self.integr_winwidth.itemData(a0, role=QtCore.Qt.ItemDataRole.UserRole))

    def update_ui(self):
        for attr_name, attr in get_attribute_list():

            if attr_name in self.attribute_names:
                continue

            # Only add 1 long ArrayAttributes (ObjectAttributes have shape[0] == None)
            if len(attr.shape) != 1 or attr.shape[0] != 1:
                continue

            # Check if it has values written to it
            i, t, f = read_attribute(attr_name)
            if t[0] is None:
                continue

            self.attribute_names.append(attr_name)
            self.attribute_selection.addItem(attr_name)

    def update_plot(self):
        i, t, f = read_attribute('psd_frequency')
        _, _, p = read_attribute('psd_power')

        self.data_item.setData(x=f.flatten(), y=p.flatten())
