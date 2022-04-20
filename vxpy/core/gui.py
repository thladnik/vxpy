"""
vxPy ./core/gui.py
Copyright (C) 2022 Tim Hladnik

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
from __future__ import annotations
import importlib
import os.path
import sys
import time
from collections import OrderedDict

import h5py
import h5gview
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QLabel
import pyqtgraph as pg
from typing import Callable, List, Union

from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.protocol as vxprotocol
from vxpy.definitions import *
import vxpy.modules as vxmodules

log = vxlogger.getLogger(__name__)


class Widget:
    """Base widget"""

    def __init__(self, main):
        self.main: vxmodules.Gui = main


class ExposedWidget:
    """Widget base class for widgets which expose bound methods to be called from external sources"""

    def __init__(self):
        # List of exposed methods to register for rpc callbacks
        self.exposed: List[Callable] = []

    def create_hooks(self):
        """Register exposed functions as callbacks with the local process"""
        for fun in self.exposed:
            fun_str = fun.__qualname__
            vxipc.Process.register_rpc_callback(self, fun_str, fun)


class AddonWidget(QtWidgets.QWidget, ExposedWidget, Widget):
    """Addon widget which should be subclassed by custom widgets in plugins, etc"""

    def __init__(self, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=main)
        self.module_active = True

    @staticmethod
    def connect_to_timer(fun: Callable):
        AddonTabWidget.timer.timeout.connect(fun)


class IntegratedWidget(QtWidgets.QGroupBox, ExposedWidget, Widget):
    """Integrated widgets which are part of the  main window"""

    def __init__(self, group_name: str, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QGroupBox.__init__(self, group_name, parent=main)


class WindowWidget(QtWidgets.QWidget, ExposedWidget, Widget):
    """Widget that should be displayed as a separate window"""

    def __init__(self, title: str, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=main, f=QtCore.Qt.WindowType.Window)

        # Set title
        self.setWindowTitle(title)

        # Make known to window manager
        self.createWinId()

        # Open/show
        self.show()

    def toggle_visibility(self):
        """Switch visibility based on current visibility"""

        if self.isVisible():
            self.hide()
        else:
            self.show()

        if self.isMinimized():
            self.showNormal()

    def event(self, event):
        """Catch all events and execute custom responses"""

        # If window is activated (e.g. brought to front),
        # this also raises all other windows
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            # Raise main window
            vxipc.Process.window.raise_()
            # Raise all subwindows
            vxipc.Process.window.raise_subwindows()
            # Raise this window last
            self.raise_()

        return QtWidgets.QWidget.event(self, event)


class WindowTabWidget(WindowWidget, ExposedWidget):
    """Windowed widget which implements a central tab widget that is used to display addon widgets"""

    def __init__(self, *args, **kwargs):
        WindowWidget.__init__(self, *args, **kwargs)

        # Add tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.tab_widget)

    def create_addon_tabs(self, process_name: str) -> None:
        """Read UI addons for local given process and add them to central tab widget.

        :param process_name: name of process for which to add the addons to the tab widget
        """
        # Select ui addons for this local
        used_addons = config.CONF_GUI_ADDONS[process_name]

        # Add all addons as individual tabs to tab widget
        for path in used_addons:
            log.info(f'Load UI addon {path}')

            # Load routine
            parts = path.split('.')
            module = importlib.import_module('.'.join(parts[:-1]))
            addon_cls = getattr(module, parts[-1])

            if addon_cls is None:
                log.error(f'UI addon {path} not found.')
                continue

            wdgt = addon_cls(self.main)

            self.tab_widget.addTab(wdgt, f'{process_name}:{parts[-1]}')


class AddonTabWidget(WindowTabWidget):
    timer = QtCore.QTimer()
    timer_interval = 50  # ms

    def __init__(self, *args):
        WindowTabWidget.__init__(self, 'Addon widgets', *args)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.stream_fps = 20
        self.timer.setInterval(self.timer_interval)
        self.timer.start()



class PlottingWindow(WindowWidget):
    # Colormap is tab10 from matplotlib:
    # https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html
    cmap = (np.array([(0.12156862745098039, 0.4666666666666667, 0.7058823529411765),
                      (1.0, 0.4980392156862745, 0.054901960784313725),
                      (0.17254901960784313, 0.6274509803921569, 0.17254901960784313),
                      (0.8392156862745098, 0.15294117647058825, 0.1568627450980392),
                      (0.5803921568627451, 0.403921568627451, 0.7411764705882353),
                      (0.5490196078431373, 0.33725490196078434, 0.29411764705882354),
                      (0.8901960784313725, 0.4666666666666667, 0.7607843137254902),
                      (0.4980392156862745, 0.4980392156862745, 0.4980392156862745),
                      (0.7372549019607844, 0.7411764705882353, 0.13333333333333333),
                      (0.09019607843137255, 0.7450980392156863, 0.8117647058823529)]) * 255).astype(int)

    cache_chunk_size = 10 ** 4

    def __init__(self, *args):
        WindowWidget.__init__(self, 'Plotter', *args)

        self.starttime = time.perf_counter()

        # Set layout
        self.setLayout(QtWidgets.QVBoxLayout())

        # Make add_buffer_attribute method accessible for RPCs
        self.exposed.append(PlottingWindow.add_buffer_attribute)

        # Add range widget
        self.topbar_widget = QtWidgets.QWidget()
        self.layout().addWidget(self.topbar_widget)
        self.topbar_widget.setLayout(QtWidgets.QHBoxLayout())

        # Autoscale checkbox
        self.check_auto_scale = QtWidgets.QCheckBox('X-autoscale')
        self.check_auto_scale.setChecked(True)
        self.topbar_widget.layout().addWidget(self.check_auto_scale)

        # Add spacer
        hspacer = QtWidgets.QSpacerItem(1, 1,
                                        QtWidgets.QSizePolicy.Policy.Expanding,
                                        QtWidgets.QSizePolicy.Policy.Minimum)
        self.topbar_widget.layout().addItem(hspacer)

        self.topbar_widget.layout().addWidget(QLabel('Show subplot: '))

        # Add plot widget
        self.layout_widget = pg.GraphicsLayoutWidget()
        self.layout().addWidget(self.layout_widget)
        self.plot_items: OrderedDict[str, pg.PlotItem] = OrderedDict()
        self.data_items: OrderedDict[str, pg.PlotDataItem] = OrderedDict()
        self.legend_items: OrderedDict[str, pg.LegendItem] = OrderedDict()
        self.subplot_toggles: Dict[str, QtWidgets.QCheckBox] = {}

        # Start timer
        self.tmr_update_data = QtCore.QTimer()
        self.tmr_update_data.setInterval(1000 // 20)
        self.tmr_update_data.timeout.connect(self._read_buffer_data)
        self.tmr_update_data.start()

        # self.x_range = 1000
        self.xmin = -20.
        self.xmax = 0

        # Set up cache file
        temp_path = os.path.join(PATH_TEMP, '._plotter_temp.h5')
        if os.path.exists(temp_path):
            os.remove(temp_path)
        self.cache = h5py.File(temp_path, 'w')

    def _read_buffer_data(self):

        grp = None
        for attr_name, grp in self.cache.items():

            # Read new values from buffer
            try:
                last_idx = grp.attrs['last_idx']

                # If last_idx is set to negative, read last one and set to index
                if last_idx < 0:
                    n_idcs, n_times, n_data = vxattribute.read_attribute(attr_name)
                    if n_times[0] is None:
                        continue
                    grp.attrs['last_idx'] = n_idcs[0]
                else:
                    # Read this attribute starting from the last_idx
                    n_idcs, n_times, n_data = vxattribute.read_attribute(attr_name, from_idx=last_idx)


            except Exception as exc:
                log.warning(f'Problem trying to read attribute "{attr_name}" from_idx={grp.attrs["last_idx"]}'
                              f'If this warning persists, DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE is possibly set too low.'
                              f'// Exception: {exc}')

                # In case of exception, assume that GUI is lagging behind temporarily and reset last_idx
                grp.attrs['last_idx'] = -1

                continue

            # No new datapoints to plot
            if len(n_times) == 0:
                continue

            try:
                n_times = np.array(n_times)
                n_data = np.array(n_data)
            except Exception as exc:
                continue

            # Set new last index
            grp.attrs['last_idx'] = n_idcs[-1]

            try:
                # Reshape datasets
                old_n = grp['t'].shape[0]
                new_n = n_times.shape[0]
                grp['t'].resize((old_n + new_n, ))
                grp['y'].resize((old_n + new_n, ))

                # Write new data
                grp['t'][-new_n:] = n_times.flatten()
                grp['y'][-new_n:] = n_data.flatten()

                # Set chunk time marker for indexing
                i_o = old_n // self.cache_chunk_size
                i_n = (old_n + new_n) // self.cache_chunk_size
                if i_n > i_o:
                    grp['mt'].resize((i_n+1, ))
                    grp['mt'][-1] = n_times[(old_n+new_n) % self.cache_chunk_size]
            except Exception as exc:
                import traceback
                print(traceback.print_exc())

        if grp is not None:
            self._update_xrange(grp['t'][-1])

        self.update_plots()

    def update_plots(self):
        times = None
        for attr_name, dataitem in self.data_items.items():

            grp = self.cache[attr_name]

            if grp['t'].shape[0] == 0:
                continue

            idcs = np.where(grp['mt'][:][grp['mt'][:] < self.xmin])
            if len(idcs[0]) > 0:
                start_idx = idcs[0][-1] * self.cache_chunk_size
            else:
                start_idx = 0

            times = grp['t'][start_idx:]
            data = grp['y'][start_idx:]

            dataitem.setData(x=times, y=data)

        # xmax = 0.
        # for plot_dataitem in self.data_items.values():
        #     x = plot_dataitem.xData
        #     y = plot_dataitem.yData
        #
        #     now = time.perf_counter() - self.starttime
        #     newnum = 40
        #     dt = (now - x[-1]) / newnum
        #
        #     x = np.concatenate([x, np.arange(x[-1], now, dt) + dt])
        #     y = np.concatenate([y, np.random.rand(newnum)])
        #     plot_dataitem.setData(x=x, y=y)
        #
        #     new_xmax = np.max(x)
        #     if new_xmax > xmax:
        #         xmax = new_xmax

        # self._update_xrange(xmax)

    def _update_xrange(self, new_xmax):

        if self.check_auto_scale.isChecked():

            # Calculate new range
            xrange = self.xmax - self.xmin
            self.xmin = new_xmax - xrange
            self.xmax = new_xmax

        # Update x range for all subplots
        for plot_item in self.plot_items.values():
            plot_item.getViewBox().setXRange(self.xmin, self.xmax, padding=0.)

    def _xrange_changed(self, viewbox, xrange):
        self.xmin, self.xmax = xrange

    def _add_subplot_toggle(self, axis_name):
        checkbox = QtWidgets.QCheckBox(axis_name)
        checkbox.setTristate(False)
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(self._toggle_subplot_visibility(axis_name))
        self.topbar_widget.layout().addWidget(checkbox)
        self.subplot_toggles[axis_name] = checkbox

    def _toggle_subplot_visibility(self, axis_name):
        def _toggle():
            state = self.subplot_toggles[axis_name].isChecked()
            plot_item = self.plot_items[axis_name]
            if state:
                plot_item.show()
            else:
                shown = sum([cb.isChecked() for cb in self.subplot_toggles.values()])
                if shown < 1:
                    self.subplot_toggles[axis_name].setChecked(True)
                else:
                    plot_item.hide()
        return _toggle

    def _subplot(self, axis_name, units=None):

        if units is None:
            units = 'au'

        # Return subplot if it exists
        if axis_name in self.plot_items:
            return self.plot_items[axis_name]

        # Else create subplot

        # Hide x axis for previously added subplot
        if len(self.plot_items) > 0:
            self.plot_items[list(self.plot_items)[-1]].hideAxis('bottom')

        # Add new subplot
        new_plot: pg.PlotItem = self.layout_widget.addPlot(col=0, row=len(self.plot_items))
        new_plot.getViewBox().enableAutoRange(x=False)
        new_plot.setLabel('bottom', text='Time', units='s')
        new_plot.setLabel('left', text=axis_name, units=units)
        new_plot.getAxis('left').setWidth(75)
        new_plot.sigXRangeChanged.connect(self._xrange_changed)
        self.plot_items[axis_name] = new_plot

        # Add subplot toggle option
        self._add_subplot_toggle(axis_name)

        # Add legend for new plot
        new_legend = pg.LegendItem()
        new_legend.setParentItem(new_plot)
        self.legend_items[axis_name] = new_legend

        return new_plot

    def _dataitem(self, subplot, attr_name):

        i = len(subplot.getViewBox().addedItems)
        color = self.cmap[i]

        idcs, times, values = vxattribute.read_attribute(attr_name)
        print(idcs, times, values)
        new_dataitem = pg.PlotDataItem(times, values[0], pen=pg.mkPen(color=color, style=QtCore.Qt.PenStyle.SolidLine))
        # new_dataitem = pg.PlotDataItem([now], [0], pen=pg.mkPen(color=color, style=QtCore.Qt.PenStyle.SolidLine))
        subplot.getViewBox().addItem(new_dataitem)
        # Add dataitem to dict
        self.data_items[attr_name] = new_dataitem

        return new_dataitem

    def add_buffer_attribute(self, attr_name, name=None, axis=None, units=None):

        if name is None:
            name = attr_name

        # Determine axis name
        axis_name = axis if axis is not None else 'Default'

        # Fetch subplot
        subplot = self._subplot(axis_name, units=units)

        # Add dataitem
        dataitem = self._dataitem(subplot, attr_name)

        # Add dataitem to legend
        self.legend_items[axis_name].addItem(dataitem, name)

        # Add temporary datasets
        grp = self.cache.create_group(attr_name)
        grp.create_dataset('t', shape=(0,), chunks=(self.cache_chunk_size,), maxshape=(None,), dtype=np.float32)
        grp.create_dataset('y', shape=(0,), chunks=(self.cache_chunk_size,), maxshape=(None,), dtype=np.float32)
        grp.create_dataset('mt', shape=(1,), chunks=(self.cache_chunk_size,), maxshape=(None,), dtype=np.float32)
        grp.attrs['last_idx'] = -1
        grp['mt'][0] = 0.


class PlottingWindow1(WindowWidget):

    # Colormap is tab10 from matplotlib:
    # https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html
    cmap = \
        ((0.12156862745098039, 0.4666666666666667, 0.7058823529411765),
         (1.0, 0.4980392156862745, 0.054901960784313725),
         (0.17254901960784313, 0.6274509803921569, 0.17254901960784313),
         (0.8392156862745098, 0.15294117647058825, 0.1568627450980392),
         (0.5803921568627451, 0.403921568627451, 0.7411764705882353),
         (0.5490196078431373, 0.33725490196078434, 0.29411764705882354),
         (0.8901960784313725, 0.4666666666666667, 0.7607843137254902),
         (0.4980392156862745, 0.4980392156862745, 0.4980392156862745),
         (0.7372549019607844, 0.7411764705882353, 0.13333333333333333),
         (0.09019607843137255, 0.7450980392156863, 0.8117647058823529))

    mem_seg_len = 1000

    def __init__(self, *args):
        WindowWidget.__init__(self, 'Plotter', *args)

        hspacer = QtWidgets.QSpacerItem(1, 1,
                                        QtWidgets.QSizePolicy.Policy.Expanding,
                                        QtWidgets.QSizePolicy.Policy.Minimum)
        self.cmap = (np.array(self.cmap) * 255).astype(int)

        self.exposed.append(PlottingWindow1.add_buffer_attribute)

        self.setLayout(QtWidgets.QGridLayout())

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.plot_item.setLabel('bottom', text='Time', units='s')
        self.layout().addWidget(self.plot_widget, 1, 0, 1, 5)

        self.legend_item = pg.LegendItem()
        self.legend_item.setParentItem(self.plot_item)

        # Start timer
        self.tmr_update_data = QtCore.QTimer()
        self.tmr_update_data.setInterval(1000 // 20)
        self.tmr_update_data.timeout.connect(self.read_buffer_data)
        self.tmr_update_data.start()


        self.plot_data_items = dict()
        self.plot_num = 0
        self._interact = False
        self._xrange = 20
        self.plot_item.sigXRangeChanged.connect(self.set_new_xrange)
        self.plot_item.setXRange(-self._xrange, 0, padding=0.)
        self.plot_item.setLabels(left='defaulty')
        self.axes = {'defaulty': {'axis': self.plot_item.getAxis('left'),
                                  'vb': self.plot_item.getViewBox()}}
        self.plot_item.hideAxis('left')
        self.axis_idx = 3
        self.plot_data = dict()

        # Set auto scale checkbox
        self.check_auto_scale = QtWidgets.QCheckBox('Autoscale')
        self.check_auto_scale.stateChanged.connect(self.auto_scale_toggled)
        self.check_auto_scale.setChecked(True)
        self.layout().addWidget(self.check_auto_scale, 0, 0)
        self.auto_scale_toggled()
        # Scale inputs
        self.layout().addWidget(QLabel('X-Range'), 0, 1)
        # Xmin
        self.dsp_xmin = QtWidgets.QDoubleSpinBox()
        self.dsp_xmin.setRange(-10**6, 10**6)
        self.block_xmin = QtCore.QSignalBlocker(self.dsp_xmin)
        self.block_xmin.unblock()
        self.dsp_xmin.valueChanged.connect(self.ui_xrange_changed)
        self.layout().addWidget(self.dsp_xmin, 0, 2)
        # Xmax
        self.dsp_xmax = QtWidgets.QDoubleSpinBox()
        self.dsp_xmax.setRange(-10**6, 10**6)
        self.block_xmax = QtCore.QSignalBlocker(self.dsp_xmax)
        self.block_xmax.unblock()
        self.dsp_xmax.valueChanged.connect(self.ui_xrange_changed)
        self.layout().addWidget(self.dsp_xmax, 0, 3)
        self.layout().addItem(hspacer, 0, 4)
        # Connect viewbox range update signal
        self.plot_item.sigXRangeChanged.connect(self.update_ui_xrange)

        # Set up cache file
        temp_path = os.path.join(PATH_TEMP, '._plotter_temp.h5')
        if os.path.exists(temp_path):
            os.remove(temp_path)
        self.cache = h5py.File(temp_path, 'w')

    def ui_xrange_changed(self):
        self.plot_item.setXRange(self.dsp_xmin.value(), self.dsp_xmax.value(), padding=0.)

    def update_ui_xrange(self, *args):
        xrange = self.plot_item.getAxis('bottom').range
        self.block_xmin.reblock()
        self.dsp_xmin.setValue(xrange[0])
        self.block_xmin.unblock()

        self.block_xmax.reblock()
        self.dsp_xmax.setValue(xrange[1])
        self.block_xmax.unblock()

    def auto_scale_toggled(self, *args):
        self.auto_scale = self.check_auto_scale.isChecked()

    def mouseDoubleClickEvent(self, a0) -> None:
        # Check if double click on AxisItem
        click_pointf = QtCore.QPointF(a0.pos())
        items = [o for o in self.plot_item.scene().items(click_pointf) if isinstance(o, pg.AxisItem)]
        if len(items) == 0:
            return

        axis_item = items[0]

        # TODO: this flipping of pens doesn't work if new plotdataitems
        #   were added to the axis after the previous ones were hidden
        for id, data in self.plot_data.items():
            if axis_item.labelText == data['axis']:
                data_item: pg.PlotDataItem = self.plot_data_items[id]
                # Flip pen
                current_pen = data_item.opts['pen']
                if current_pen.style() == QtCore.Qt.PenStyle.NoPen:
                    data_item.setPen(data['pen'])
                else:
                    data_item.setPen(None)


        a0.accept()

    def set_new_xrange(self, vb, xrange):
        self._xrange = np.floor(xrange[1]-xrange[0])

    def update_views(self):
        for axis_name, ax in self.axes.items():
            ax['vb'].setGeometry(self.plot_item.vb.sceneBoundingRect())
            ax['vb'].linkedViewChanged(self.plot_item.vb, ax['vb'].XAxis)

    def add_buffer_attribute(self, attr_name, start_idx=0, name=None, axis=None):

        id = attr_name

        # Set axis
        if axis is None:
            axis = 'defaulty'

        # Set name
        if name is None:
            name = attr_name

        if axis not in self.axes:
            self.axes[axis] = dict(axis=pg.AxisItem('left'), vb=pg.ViewBox())

            self.plot_item.layout.addItem(self.axes[axis]['axis'], 2, self.axis_idx)
            self.plot_item.scene().addItem(self.axes[axis]['vb'])
            self.axes[axis]['axis'].linkToView(self.axes[axis]['vb'])
            self.axes[axis]['vb'].setXLink(self.plot_item)
            self.axes[axis]['axis'].setLabel(axis)

            self.update_views()
            self.plot_item.vb.sigResized.connect(self.update_views)
            self.axis_idx += 1

        if id not in self.plot_data:
            # Choose pen
            i = self.plot_num // len(self.cmap)
            m = self.plot_num % len(self.cmap)
            color = (*self.cmap[m], 255 // (2**i))
            pen = pg.mkPen(color)
            self.plot_num += 1

            # Set up cache group
            grp = self.cache.create_group(name)
            grp.create_dataset('x', shape=(0, ), chunks=(self.mem_seg_len, ), maxshape=(None, ), dtype=np.float32)
            grp.create_dataset('y', shape=(0, ), chunks=(self.mem_seg_len, ), maxshape=(None, ), dtype=np.float32)
            grp.create_dataset('mt', shape=(1, ), chunks=(self.mem_seg_len, ), maxshape=(None, ), dtype=np.float32)
            grp['mt'][0] = 0.

            # Set plot data
            self.plot_data[id] = {'axis': axis,
                                  'last_idx': None,
                                  'pen': pen,
                                  'name': name,
                                  'h5grp': grp}

        if id not in self.plot_data_items:

            # Create data item and add to axis viewbox
            data_item = pg.PlotDataItem([], [], pen=self.plot_data[id]['pen'])
            self.axes[axis]['vb'].addItem(data_item)

            # Add to legend
            self.legend_item.addItem(data_item, name)

            # Set data item
            self.plot_data_items[id] = data_item

    def read_buffer_data(self):

        for attr_name, data in self.plot_data.items():

            # Read new values from buffer
            try:
                last_idx = data['last_idx']

                # If no last_idx is set read last one and set to index if it is not None
                if last_idx is None:
                    n_idcs, n_times, n_data = vxattribute.read_attribute(attr_name)
                    if n_times[0] is None:
                        continue
                    data['last_idx'] = n_idcs[0]
                else:
                    # Read this attribute starting from the last_idx
                    n_idcs, n_times, n_data = vxattribute.read_attribute(attr_name, from_idx=last_idx)


            except Exception as exc:
                log.warning(f'Problem trying to read attribute "{attr_name}" from_idx={data["last_idx"]}'
                              f'If this warning persists, DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE is possibly set too low.'
                              f'// Exception: {exc}')

                # In case of execution, assume that GUI is lagging behind temporarily and reset last_idx
                data['last_idx'] = None

                continue

            # No new datapoints to plot
            if len(n_times) == 0:
                continue

            try:
                n_times = np.array(n_times)
                n_data = np.array(n_data)
            except Exception as exc:
                continue

            # Set new last index
            data['last_idx'] = n_idcs[-1]

            try:
                # Reshape datasets
                old_n = data['h5grp']['x'].shape[0]
                new_n = n_times.shape[0]
                data['h5grp']['x'].resize((old_n + new_n, ))
                data['h5grp']['y'].resize((old_n + new_n, ))

                # Write new data
                data['h5grp']['x'][-new_n:] = n_times.flatten()
                data['h5grp']['y'][-new_n:] = n_data.flatten()

                # Set chunk time marker for indexing
                i_o = old_n // self.mem_seg_len
                i_n = (old_n + new_n) // self.mem_seg_len
                if i_n > i_o:
                    data['h5grp']['mt'].resize((i_n+1, ))
                    data['h5grp']['mt'][-1] = n_times[(old_n+new_n) % self.mem_seg_len]

            except Exception as exc:
                import traceback
                print(traceback.print_exc())

        self.update_plots()

    def update_plots(self):
        times = None
        for id, data_item in self.plot_data_items.items():

            grp = self.plot_data[id]['h5grp']

            if grp['x'].shape[0] == 0:
                continue

            if self.auto_scale:
                last_t = grp['x'][-1]
            else:
                last_t = self.plot_item.getAxis('bottom').range[1]

            first_t = last_t - self._xrange

            idcs = np.where(grp['mt'][:][grp['mt'][:] < first_t])
            if len(idcs[0]) > 0:
                start_idx = idcs[0][-1] * self.mem_seg_len
            else:
                start_idx = 0

            times = grp['x'][start_idx:]
            data = grp['y'][start_idx:]

            data_item.setData(x=times, y=data)

        # Update range
        if times is not None and self.auto_scale:
            self.plot_item.setXRange(times[-1] - self._xrange, times[-1], padding=0.)


class ProcessInfo(QtWidgets.QWidget):

    def __init__(self, process_name: str, parent: ProcessMonitorWidget):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Set layout
        self.setLayout(QtWidgets.QGridLayout())
        self.setContentsMargins(0, 0, 0, 0)

        lbl = QtWidgets.QLabel(process_name)
        lbl.setStyleSheet('font-weight:bold;')
        lbl.setFixedWidth(50)
        self.layout().addWidget(lbl, 0, 0)
        state = QtWidgets.QLineEdit('')
        state.setDisabled(True)
        state.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        parent.state_widgets[process_name] = state
        self.layout().addWidget(state, 0, 1)


class ProcessMonitorWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Process monitor', *args)

        self.exposed.append(ProcessMonitorWidget.update_process_interval)

        self.state_labels = dict()
        self.state_widgets = dict()
        self.intval_widgets = dict()
        self._process_widgets: Dict[str, QtWidgets.QWidget] = {}

        self._setup_ui()

    def _create_process_monitor_widget(self, process_name: str) -> QtWidgets.QWidget:

        wdgt = ProcessInfo(process_name, self)

        self._process_widgets[process_name] = wdgt

        return wdgt

    def _setup_ui(self):

        # self.setFixedWidth(200)

        # Setup widget
        self.setLayout(QtWidgets.QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)

        # Controller modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_CONTROLLER))
        # Camera modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_CAMERA))
        # Display modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_DISPLAY))
        # Gui modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_GUI))
        # IO modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_IO))
        # Worker modules status
        self.layout().addWidget(self._create_process_monitor_widget(PROCESS_WORKER))

        # Add spacer
        vSpacer = QtWidgets.QSpacerItem(1, 1,
                                        QtWidgets.QSizePolicy.Policy.Minimum,
                                        QtWidgets.QSizePolicy.Policy.Expanding)
        # self.layout().addItem(vSpacer, 6, 0)

        # Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._update_states)
        self._tmr_updateGUI.start()

    def update_process_interval(self, process_name, target_inval, mean_inval, std_inval):
        if process_name in self.state_widgets:
            self.state_widgets[process_name].setToolTip(f'{mean_inval * 1000:.1f}'
                                                        f'/{target_inval * 1000:.1f} '
                                                        f'({std_inval * 1000:.1f}) ms')
        else:
            print(process_name, '{:.2f} +/- {:.2f}ms'.format(mean_inval * 1000, std_inval * 1000))

    @staticmethod
    def _set_process_state(le: QtWidgets.QLineEdit, state: Enum):
        # Set text
        le.setText(state.name)

        # Set style
        if state == State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif state == State.STARTING:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif state == State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif state == State.STOPPED:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        elif state == State.RUNNING:
            le.setStyleSheet('color: #deb737; font-weight:bold;')
        else:
            le.setStyleSheet('color: #000000')

    def _update_states(self):
        for process_name, state_widget in self.state_widgets.items():
            self._set_process_state(state_widget, vxipc.get_state(process_name))


class RecordingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Recordings', *args)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.setObjectName('RecordingWidgetComboBox')

        # Add exposed methods
        self.exposed.append(RecordingWidget.show_lab_notebook)
        self.exposed.append(RecordingWidget.close_lab_notebook)

        v_spacer = QtWidgets.QSpacerItem(1, 1,
                                         QtWidgets.QSizePolicy.Policy.Minimum,
                                         QtWidgets.QSizePolicy.Policy.Expanding)

        self.lab_nb_folder = None
        self.h5views: Dict[str, h5gview.ui.Main] = {}

        # Basic properties
        self.folder_wdgt_width = 300
        self.notebook_width = 300
        self.setFixedWidth(400)
        self.setCheckable(True)

        # Create folder widget and add to widget
        self.folder_wdgt = QtWidgets.QWidget()
        self.folder_wdgt.setLayout(QtWidgets.QGridLayout())
        self.folder_wdgt.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.folder_wdgt)

        # Current base folder for recordings
        self.base_folder = QtWidgets.QLineEdit('')
        self.base_folder.setReadOnly(True)
        self.folder_wdgt.layout().addWidget(QLabel('Base folder'), 0, 0)
        self.folder_wdgt.layout().addWidget(self.base_folder, 0, 1, 1, 2)

        # Current recording folder
        self.rec_folder = QtWidgets.QLineEdit()
        self.rec_folder.editingFinished.connect(self.set_recording_folder)
        # self.rec_folder.setReadOnly(True)
        self.folder_wdgt.layout().addWidget(QLabel('Folder'), 1, 0)
        self.folder_wdgt.layout().addWidget(self.rec_folder, 1, 1, 1, 2)

        # Button: Open base folder
        self.btn_open_base_folder = QtWidgets.QPushButton('Open base folder')
        self.btn_open_base_folder.clicked.connect(self.open_base_folder)
        self.folder_wdgt.layout().addWidget(self.btn_open_base_folder, 2, 1)

        # Button: Open last recording
        self.btn_open_recording = QtWidgets.QPushButton('Open last recording')
        self.btn_open_recording.setDisabled(True)
        self.btn_open_recording.clicked.connect(self._open_last_recording)
        self.folder_wdgt.layout().addWidget(self.btn_open_recording, 2, 2)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Controls widget
        self.controls = QtWidgets.QWidget()
        self.controls.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.controls)

        # Create interaction widget and add to controls
        self.interact_widget = QtWidgets.QWidget()
        # self.interact_widget.setFixedWidth(100)
        self.interact_widget.setLayout(QtWidgets.QHBoxLayout())
        self.interact_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.controls.layout().addWidget(self.interact_widget)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_start.clicked.connect(self.start_recording)
        self.interact_widget.layout().addWidget(self.btn_start)
        # Pause
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.clicked.connect(self.pause_recording)
        self.interact_widget.layout().addWidget(self.btn_pause)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.clicked.connect(self.finalize_recording)
        self.interact_widget.layout().addWidget(self.btn_stop)
        self.interact_widget.layout().addItem(v_spacer)

        # Lab notebook (opened when recording is active)
        self.lab_notebook = QtWidgets.QWidget()
        self.lab_notebook.setLayout(QtWidgets.QVBoxLayout())
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Experimenter'))
        self.nb_experimenter = QtWidgets.QLineEdit()
        self.lab_notebook.layout().addWidget(self.nb_experimenter)
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Notes'))
        self.nb_notes = QtWidgets.QTextEdit()
        self.lab_notebook.layout().addWidget(self.nb_notes)
        # self.lab_notebook.hide()
        self.layout().addWidget(self.lab_notebook)
        self.close_lab_notebook()

        # Set timer for GUI update
        self.ui_state = ()
        self.tmr_update_gui = QtCore.QTimer()
        self.tmr_update_gui.setInterval(200)
        self.tmr_update_gui.timeout.connect(self.update_ui)
        self.tmr_update_gui.start()

    @staticmethod
    def open_base_folder():
        output_path = os.path.abspath(config.CONF_REC_OUTPUT_FOLDER)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(output_path.replace('\\', '/')))

    def show_lab_notebook(self):
        self.lab_nb_folder = os.path.join(config.CONF_REC_OUTPUT_FOLDER, vxipc.Control.Recording[RecCtrl.folder])
        self.lab_notebook.setEnabled(True)

    def close_lab_notebook(self):

        if self.lab_nb_folder is not None:
            experimenter = self.nb_experimenter.text()
            notes = self.nb_notes.toPlainText()
            with open(os.path.join(self.lab_nb_folder, 'lab_notebook.txt'), 'w') as f:
                f.write(f'Experimenter: {experimenter}\n---\nNotes\n{notes}')
            self.lab_nb_folder = None
        self.nb_notes.clear()
        self.lab_notebook.setEnabled(False)

    def set_recording_folder(self):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.set_recording_folder, self.rec_folder.text())

    @staticmethod
    def start_recording():
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.start_manual_recording)

    @staticmethod
    def pause_recording():
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.pause_recording)

    @staticmethod
    def finalize_recording():
        # First: pause recording
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.pause_recording)

        # Finally: stop recording
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.stop_manual_recording)

    @staticmethod
    def toggle_enable(newstate):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.set_enable_recording, newstate)

    def _open_last_recording(self):
        base_path = os.path.abspath(config.CONF_REC_OUTPUT_FOLDER)
        recording_list = []
        for s in os.listdir(base_path):
            rec_path = os.path.join(base_path, s)
            if not os.path.isdir(rec_path):
                continue
            recording_list.append(rec_path)

        if len(recording_list) == 0:
            log.warning('Cannot open recording. No valid folders in base directory.')
            return
        recording_list.sort(key=lambda x: os.path.getmtime(x))

        last_recording = recording_list[-1]
        file_list = [os.path.join(last_recording, s) for s in os.listdir(last_recording) if s.endswith('.hdf5')]

        self.h5views[last_recording] = h5gview.open_ui(file_list)

    def update_ui(self):
        """(Periodically) update UI based on shared configuration"""

        # Get states
        enabled = vxipc.Control.Recording[RecCtrl.enabled]
        active = vxipc.Control.Recording[RecCtrl.active]
        current_folder = vxipc.Control.Recording[RecCtrl.folder]

        # Make these calls a bit more economical
        state = (enabled, active, current_folder)
        if state == self.ui_state:
            return
        self.ui_state = state

        if active and enabled:
            self.setStyleSheet('QGroupBox#RecordingWidgetComboBox{border: 4px solid red;}')
        else:
            self.setStyleSheet('QGroupBox#RecordingWidgetComboBox{}')

        # Set enabled
        self.setCheckable(not active and not bool(current_folder))
        self.setChecked(enabled)

        # Base folder
        self.base_folder.setText(config.CONF_REC_OUTPUT_FOLDER)

        # Recording folder
        self.rec_folder.setText(vxipc.Control.Recording[RecCtrl.folder])
        self.rec_folder.setReadOnly(active)

        # Buttons
        # Start
        self.btn_start.setEnabled(not active and enabled)
        # self.btn_start.setText('Start' if vxipc.in_state(State.IDLE, PROCESS_CONTROLLER) else 'Resume')
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(active and enabled and not bool(vxipc.Control.Protocol[ProtocolCtrl.name]))
        # Overwrite stop button during protocol
        # if bool(vxipc.Control.Protocol[ProtocolCtrl.name]):
        #     self.btn_stop.setEnabled(False)

        self.btn_open_recording.setEnabled(
            bool(os.listdir(os.path.abspath(config.CONF_REC_OUTPUT_FOLDER))) and not active)


class RecordingSettings(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        # Show recorded routines
        self.recorded_attributes = QtWidgets.QGroupBox('Recorded attributes')
        self.recorded_attributes.setLayout(QtWidgets.QVBoxLayout())
        self.recorded_attributes.setFixedWidth(250)
        self.rec_attribute_list = QtWidgets.QListWidget()

        self.recorded_attributes.layout().addWidget(self.rec_attribute_list)
        # Update recorded attributes
        for match_string in config.CONF_REC_ATTRIBUTES:
            self.rec_attribute_list.addItem(QtWidgets.QListWidgetItem(match_string))
        # self.layout().addWidget(self.recorded_attributes)

        # Data compression
        self.layout().addWidget(QLabel('Compression'))
        self.compression_method = QtWidgets.QComboBox()
        self.compression_opts = QtWidgets.QComboBox()
        self.compression_method.addItems(['None', 'GZIP', 'LZF'])
        self.layout().addWidget(self.compression_method)
        self.layout().addWidget(self.compression_opts)
        self.compression_method.currentTextChanged.connect(self.set_compression_method)
        self.compression_method.currentTextChanged.connect(self.update_compression_opts)
        self.compression_opts.currentTextChanged.connect(self.set_compression_opts)

    def get_compression_opts(self):
        method = self.compression_method.currentText()
        opts = self.compression_opts.currentText()

        shuffle = opts.lower().find('shuffle') >= 0
        if len(opts) > 0 and method == 'GZIP':
            opts = dict(shuffle=shuffle,
                        compression_opts=int(opts[0]))
        elif method == 'LZF':
            opts = dict(shuffle=shuffle)
        else:
            opts = dict()

        return opts

    def update_compression_opts(self):
        self.compression_opts.clear()

        compr = self.compression_method.currentText()
        if compr == 'None':
            self.compression_opts.addItem('None')
        elif compr == 'GZIP':
            levels = range(10)
            self.compression_opts.addItems([f'{i} (shuffle)' for i in levels])
            self.compression_opts.addItems([str(i) for i in levels])
        elif compr == 'LZF':
            self.compression_opts.addItems(['None', 'Shuffle'])

    def get_compression_method(self):
        method = self.compression_method.currentText()
        if method == 'None':
            method = None
        else:
            method = method.lower()

        return method

    def set_compression_method(self):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.set_compression_method, self.get_compression_method())

    def set_compression_opts(self):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.set_compression_opts, self.get_compression_opts())


class LoggingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Log', *args)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        self.txe_log = QtWidgets.QTextEdit()
        self.font = QtGui.QFont()
        self.font.setPointSize(10)
        self.font.setFamily('Courier')
        self.txe_log.setReadOnly(True)
        # self.format = QtGui.QTextBlockFormat()
        # self.format.setIndent(10)
        # self.txe_log.textCursor().setBlockFormat(self.format)
        self.txe_log.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.layout().addWidget(self.txe_log)

        # Set initial log line count
        self.logccount = 0

        self.loglevelname_limit = 30

        # Set timer for updating of log
        self.timer_logging = QtCore.QTimer()
        self.timer_logging.timeout.connect(self.print_log)
        self.timer_logging.start(50)

    def print_log(self):
        self.txe_log.setFont(self.font)

        if len(vxlogger.get_history()) > self.logccount:
            for rec in vxlogger.get_history()[self.logccount:]:

                self.logccount += 1

                # Skip for debug and unset
                if rec.levelno < 20:
                    continue

                # Info
                if rec.levelno == 20:
                    self.txe_log.setTextColor(QtGui.QColor('white'))
                    # self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)
                # Warning
                elif rec.levelno == 30:
                    self.txe_log.setTextColor(QtGui.QColor('orange'))
                    # self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Error and critical
                elif rec.levelno > 30:
                    self.txe_log.setTextColor(QtGui.QColor('red'))
                    # self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Fallback
                else:
                    self.txe_log.setTextColor(QtGui.QColor('white'))
                    # self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)

                # Crop name if necessary
                name = rec.name
                if len(name) > self.loglevelname_limit:
                    name = name[:5] + '..' + name[-(self.loglevelname_limit - 7):]

                # Format line
                str_format = '{:7} {} {:' + str(self.loglevelname_limit) + '} {}'
                line = str_format.format(rec.levelname, rec.asctime[-12:], name, rec.msg)

                # Add line
                self.txe_log.append(line)


class Protocols(IntegratedWidget):

    def __init__(self, *args, **kwargs):
        IntegratedWidget.__init__(self, 'Protocols', *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        # Create selection widget
        self.selection = QtWidgets.QWidget()
        self.selection.setLayout(QtWidgets.QVBoxLayout())
        self.tab_widget.addTab(self.selection, 'Selection')

        self.protocol_list = QtWidgets.QListWidget()
        self.selection.layout().addWidget(self.protocol_list)

        # Start button
        self.start_btn = QtWidgets.QPushButton('Start protocol')
        self.start_btn.clicked.connect(self.start_protocol)
        self.selection.layout().addWidget(self.start_btn)

        # Create progress widget
        self.progress = QtWidgets.QWidget()
        self.progress.setLayout(QtWidgets.QVBoxLayout())
        self.tab_widget.addTab(self.progress, 'Progress')
        self.tab_widget.setTabEnabled(1, False)

        self.time_info = QtWidgets.QLineEdit()
        self.time_info.setReadOnly(True)
        self.progress.layout().addWidget(self.time_info)

        # Overall protocol progress
        self.protocol_progress_bar = QtWidgets.QProgressBar()
        self.protocol_progress_bar.setMinimum(0)
        self.protocol_progress_bar.setTextVisible(True)
        self.progress.layout().addWidget(self.protocol_progress_bar)

        # Phase progress
        self.phase_progress_bar = QtWidgets.QProgressBar()
        self.phase_progress_bar.setMinimum(0)
        self.phase_progress_bar.setTextVisible(True)
        self.progress.layout().addWidget(self.phase_progress_bar)

        # Show current visual information
        self.progress.layout().addWidget(QtWidgets.QLabel('Visual properties'))
        self.current_visual_name = QtWidgets.QLineEdit('')
        self.current_visual_name.setDisabled(True)
        self.progress.layout().addWidget(self.current_visual_name)

        self.visual_properties = QtWidgets.QTableWidget()
        self.visual_properties.setColumnCount(2)
        self.visual_properties.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.progress.layout().addWidget(self.visual_properties)

        # Abort button
        self.abort_btn = QtWidgets.QPushButton('Abort protocol')
        self.abort_btn.clicked.connect(self.abort_protocol)
        self.progress.layout().addWidget(self.abort_btn)

        # Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(50)
        self._tmr_update.timeout.connect(self.update_ui)
        self._tmr_update.timeout.connect(self.check_status)
        self._tmr_update.start()

        self.current_protocol = None
        self.last_protocol = None
        self.current_phase = None
        self.last_phase = None

        # Once set up: compile file list for first time
        self.load_protocol_list()

    def load_protocol_list(self):
        self.protocol_list.clear()
        self.start_btn.setEnabled(False)

        protocol_paths = vxprotocol.get_available_protocol_paths()
        for path in protocol_paths:
            item = QtWidgets.QListWidgetItem(self.protocol_list)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            # Shorten display path
            parts = path.split('.')
            new_parts = [parts[0], *parts[-2:]]
            if len(parts) > 3:
                new_parts.insert(1, '..')
            item.setText('.'.join(new_parts))
            item.setToolTip(path)
            self.protocol_list.addItem(item)

    def check_status(self):

        phase_id = vxipc.Control.Protocol[ProtocolCtrl.phase_id]

        if self.current_protocol is None or phase_id is None:
            return

        if self.current_phase == self.current_protocol.get_phase(phase_id):
            return

        self.current_phase = self.current_protocol.get_phase(phase_id)

        if self.current_phase is None:
            return

        self.current_visual_name.setText(self.current_phase.visual.__qualname__)

        # Update current visual properties in table
        self.visual_properties.clearContents()
        self.visual_properties.setRowCount(len(self.current_phase.visual_parameters))
        for i, (name, value) in enumerate(self.current_phase.visual_parameters.items()):
            self.visual_properties.setItem(i, 0, QtWidgets.QTableWidgetItem(str(name)))
            self.visual_properties.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.visual_properties.resizeColumnToContents(0)
        self.visual_properties.resizeColumnToContents(1)

    def update_ui(self):
        # Enable/Disable control elements
        ctrl_is_idle = vxipc.in_state(State.IDLE, PROCESS_CONTROLLER)
        self.start_btn.setEnabled(ctrl_is_idle)
        self.protocol_list.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(vxipc.Control.Protocol[ProtocolCtrl.name])
        start_phase = vxipc.Control.Protocol[ProtocolCtrl.phase_start]
        phase_stop = vxipc.Control.Protocol[ProtocolCtrl.phase_stop]
        phase_id = vxipc.Control.Protocol[ProtocolCtrl.phase_id]

        if protocol_is_running:
            self.abort_btn.setEnabled(phase_stop is not None and time.time() <= phase_stop - .2)
        else:
            self.abort_btn.setEnabled(False)
            if self.tab_widget.currentWidget() == self.progress:
                self.tab_widget.setCurrentWidget(self.selection)
                self.tab_widget.widget(1).setEnabled(False)

        if vxipc.Control.Protocol[ProtocolCtrl.name] is None:
            self.phase_progress_bar.setEnabled(False)
            self.protocol_progress_bar.setEnabled(False)
            self.protocol_progress_bar.setTextVisible(False)
            self.phase_progress_bar.setTextVisible(False)
            self.protocol_progress_bar.setValue(0)
        else:
            self.phase_progress_bar.setEnabled(True)
            self.protocol_progress_bar.setEnabled(True)
            self.protocol_progress_bar.setTextVisible(True)
            self.phase_progress_bar.setTextVisible(True)

        if start_phase is None:
            self.phase_progress_bar.setValue(0)
            return

        if phase_stop is None:
            return

        # Update progress
        phase_diff = time.time() - start_phase
        phase_duration = phase_stop - start_phase
        if phase_stop is not None:
            # Update phase progress
            self.phase_progress_bar.setMaximum(int(phase_duration * 1000))
            if phase_diff > 0.:
                self.phase_progress_bar.setValue(int(phase_diff * 1000))
                self.phase_progress_bar.setFormat(f'{phase_diff:.1f}/{phase_duration:.1f}s')

            # Update protocol progress
            self.protocol_progress_bar.setMaximum(self.current_protocol.phase_count * 100)
            self.protocol_progress_bar.setValue(100 * phase_id + int(phase_diff / phase_duration * 100))
            self.protocol_progress_bar.setFormat(f'Phase {phase_id + 1}/{self.current_protocol.phase_count}')

            # Update time info
            total_time = int(self.current_protocol.duration)
            total_min = total_time // 60
            total_sec = total_time % 60
            elapsed_time = int(self.current_protocol.get_duration_until_phase(phase_id) + phase_diff)
            elapsed_min = elapsed_time // 60
            elapsed_sec = elapsed_time % 60
            self.time_info.setText(f'{elapsed_min}:{elapsed_sec:02d} of {total_min}:{total_sec:02d}min')

    def start_protocol(self):
        protocol_path = self.protocol_list.currentItem().data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_protocol = vxprotocol.get_protocol(protocol_path)()
        self.tab_widget.setCurrentWidget(self.progress)
        self.tab_widget.setTabEnabled(1, True)
        self.protocol_progress_bar.setFormat('Preparing...')
        self.phase_progress_bar.setFormat('Preparing...')

        # Start recording
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.start_recording)

        # Start protocol
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.run_protocol, protocol_path)

    def abort_protocol(self):
        self.phase_progress_bar.setValue(0)
        self.phase_progress_bar.setEnabled(False)
        self.tab_widget.setCurrentWidget(self.selection)
        self.tab_widget.setTabEnabled(1, False)
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.abort_protocol)
