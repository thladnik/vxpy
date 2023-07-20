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


class CalculatePSD(vxroutine.WorkerRoutine):

    nperseg = 2 ** 10

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.callback_ops.append(CalculatePSD.set_input_signal)
        self.callback_ops.append(CalculatePSD.set_integration_window_width)

    def set_input_signal(self, attr_name, force_overwrite=False):
        if self.input_signal is not None and not force_overwrite:
            warn_context = f'Signal is already set to {self.input_signal.name}.'
        else:
            self.input_signal = vxattribute.get_attribute(attr_name)

            if self.input_signal is None:
                warn_context = 'Undefined attribute.'
            else:
                log.info(f'Set input signal in {self.__class__.__name__} to {attr_name}.')
                return

        log.warning(f'Failed to set input signal in {self.__class__.__name__} to {attr_name}. {warn_context}')

    def set_integration_window_width(self, width):
        if width < self.nperseg:
            log.warning(f'Failed to set integration window width in {self.__class__.__name__}. '
                          f'New value {width} < nperseg ({self.nperseg}). '
                          f'Keeping current ({self.integration_window_width})')
            return

        self.integration_window_width = width

    def setup(self):
        self.input_signal: vxattribute.ArrayAttribute = None
        self.integration_window_width = None
        psd_return_size = self.nperseg // 2 + 1
        self.frequencies = vxattribute.ArrayAttribute('psd_frequency', (psd_return_size, ), vxattribute.ArrayType.float64)
        self.power = vxattribute.ArrayAttribute('psd_power', (psd_return_size, ), vxattribute.ArrayType.float64)

    def initialize(self):
        pass

    def main(self, *args, **kwargs):
        if self.input_signal is None or self.integration_window_width is None:
            return

        i, t, y = self.input_signal.read(self.integration_window_width)
        if np.isnan(t[0]) or not isinstance(y, np.ndarray):
            return

        fs = 1./np.mean(np.diff(t))
        y = y.flatten()
        f, p = signal.csd(y, y, fs=fs, nperseg=self.nperseg)

        self.frequencies.write(f)
        self.power.write(p)


class DisplayPSD(vxui.IoAddonWidget):

    def __init__(self, *args, **kwargs):
        vxui.IoAddonWidget.__init__(self, *args, **kwargs)
        self.central_widget.setLayout(QtWidgets.QGridLayout())

        self.attribute_names = []
        # Attribute selection
        self.central_widget.layout().addWidget(QtWidgets.QLabel('Attribute'), 0, 0)
        self.attribute_selection = QtWidgets.QComboBox(self)
        self.attribute_selection.currentTextChanged.connect(self.set_signal_attribute_name)
        self.central_widget.layout().addWidget(self.attribute_selection, 0, 1)

        # Integration window width
        self.central_widget.layout().addWidget(QtWidgets.QLabel('Integration window size'), 1, 0)
        self.integr_winwidth = QtWidgets.QComboBox()
        for i in range(8):
            m = 2**i * CalculatePSD.nperseg
            self.integr_winwidth.addItem(str(m), userData=m)
        self.integr_winwidth.currentIndexChanged.connect(self.set_integration_window_width)
        self.integr_winwidth.currentIndexChanged.emit(0)
        self.central_widget.layout().addWidget(self.integr_winwidth, 1, 1)

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.plot_item.setLabel('bottom', text='Frequency', units='Hz')
        self.plot_item.setLabel('left', text='PSD')
        self.data_item: pg.PlotDataItem = self.plot_item.plot([], [])
        self.central_widget.layout().addWidget(self.plot_widget, 2, 0, 1, 2)

        # Start timer
        self.connect_to_timer(self.update_plot)
        self.connect_to_timer(self.update_ui)

    def set_signal_attribute_name(self, a0):
        vxipc.worker_rpc(CalculatePSD.set_input_signal, a0, force_overwrite=True)

    def set_integration_window_width(self, a0):
        vxipc.worker_rpc(CalculatePSD.set_integration_window_width, self.integr_winwidth.itemData(a0, role=QtCore.Qt.ItemDataRole.UserRole))

    def update_ui(self):
        for attr_name, attr in vxattribute.get_attribute_list():

            if attr_name in self.attribute_names:
                continue

            # Only add 1 long ArrayAttributes (ObjectAttributes have shape[0] == None)
            if len(attr.shape) != 1 or attr.shape[0] != 1:
                continue

            # Check if it has values written to it
            i, t, f = vxattribute.read_attribute(attr_name)
            if np.isnan(t[0]):
                continue

            self.attribute_names.append(attr_name)
            self.attribute_selection.addItem(attr_name)

    def update_plot(self):
        i, t, f = vxattribute.read_attribute('psd_frequency')
        _, _, p = vxattribute.read_attribute('psd_power')

        self.data_item.setData(x=f.flatten(), y=p.flatten())
