"""Extras module for PSD/CSD calculation
"""
import numpy as np
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from scipy import signal

import vxpy.core.attribute as vxattribute
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
import vxpy.core.ipc as vxipc

log = vxlogger.getLogger(__name__)


class CalculateHistogram(vxroutine.WorkerRoutine):

    bin_max_num: int = 1000
    datapoint_range: int = 1
    bin_num: int = 500
    input_signal: str = ''
    log_spaced_data: bool = False


    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

    def setup(self):
        vxattribute.ArrayAttribute('bin_edges', (self.bin_max_num+1, ), vxattribute.ArrayType.float64)
        vxattribute.ArrayAttribute('bin_counts', (self.bin_max_num, ), vxattribute.ArrayType.float64)

    def initialize(self):
        pass

    def main(self, *args, **kwargs):
        if self.input_signal == '':
            return

        idx, t, y = vxattribute.read_attribute(self.input_signal, last=self.datapoint_range)

        if idx[0] < 0:
            return

        y = np.array(y).flatten()

        if self.log_spaced_data:
            y[np.isclose(y, 0)] = y[np.logical_not(np.isclose(y, 0))].min()
            bins = np.logspace(np.floor(np.log10(y.min())), np.ceil(np.log10(y.max())), self.bin_num+1, base=10)
        else:
            bins = np.linspace(y.min(), y.max(), self.bin_num+1)

        _, counts = np.histogram(y, bins=bins)

        # fill with nans
        all_bins = np.nan * np.ones(self.bin_max_num+1)
        all_bins[:bins.shape[0]] = bins

        all_counts = np.nan * np.ones(self.bin_max_num)
        all_counts[:counts.shape[0]] = counts

        vxattribute.write_attribute('bin_edges', all_bins)
        vxattribute.write_attribute('bin_counts', all_counts)


class DisplayHistogram(vxui.IoAddonWidget):

    def __init__(self, *args, **kwargs):
        vxui.IoAddonWidget.__init__(self, *args, **kwargs)
        self.central_widget.setLayout(QtWidgets.QGridLayout())

        # Attribute selection
        self.central_widget.layout().addWidget(QtWidgets.QLabel('Attribute'), 0, 0)
        self.attribute_selection = QtWidgets.QComboBox(self)
        self.attribute_selection.addItems([name for name, _ in vxattribute.get_attribute_list()])
        self.attribute_selection.currentTextChanged.connect(self.set_signal_attribute_name)
        self.central_widget.layout().addWidget(self.attribute_selection, 0, 1)

        # Integration window width
        # self.central_widget.layout().addWidget(QtWidgets.QLabel('Integration window size'), 1, 0)
        # self.integr_winwidth = QtWidgets.QComboBox()
        # for i in range(8):
        #     m = 2**i * CalculatePSD.nperseg
        #     self.integr_winwidth.addItem(str(m), userData=m)
        # self.integr_winwidth.currentIndexChanged.connect(self.set_integration_window_width)
        # self.integr_winwidth.currentIndexChanged.emit(0)
        # self.central_widget.layout().addWidget(self.integr_winwidth, 1, 1)

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.plot_item.setLabel('bottom', text='Bins')
        self.plot_item.setLabel('left', text='Counts')
        self.data_item: pg.PlotDataItem = self.plot_item.plot([], [])
        self.central_widget.layout().addWidget(self.plot_widget, 2, 0, 1, 2)

        # Start timer
        self.connect_to_timer(self.update_plot)

    def set_signal_attribute_name(self, value):
        CalculateHistogram.instance().input_signal = value

    def update_plot(self):
        idx, _, bin_edges = vxattribute.read_attribute('bin_edges')
        _, _, counts = vxattribute.read_attribute('bin_counts')

        if idx[0] < 0:
            return

        bin_edges = bin_edges[0]
        counts = counts[0]

        bins = bin_edges[:-1] + np.diff(bin_edges)

        valid_bins = np.isfinite(counts)

        self.data_item.setData(x=bins[valid_bins], y=counts[valid_bins])
