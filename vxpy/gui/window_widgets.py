
import h5py
import numpy as np
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel
import pyqtgraph as pg

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.definitions import *
from vxpy import Logging
from vxpy.api.attribute import read_attribute
from vxpy.core.gui import WindowWidget, WindowTabWidget


class CameraWindow(WindowTabWidget):

    def __init__(self, *args):
        WindowTabWidget.__init__(self, 'Camera', *args)
        self.create_addon_tabs(PROCESS_CAMERA)

        # Select routine for FPS estimation (if any available)
        # If no routines are set, don't even start frame update timer
        self.stream_fps = 20
        if bool(config.Camera[definitions.CameraCfg.routines]):
            # Set frame update timer
            self.timer_frame_update = QtCore.QTimer()
            self.timer_frame_update.setInterval(1000 // self.stream_fps)
            self.timer_frame_update.timeout.connect(self.update_frames)
            self.timer_frame_update.start()

    def update_frames(self):
        # Update frames in tabbed widgets
        for idx in range(self.tab_widget.count()):
            self.tab_widget.widget(idx).update_frame()


class DisplayWindow(WindowTabWidget):

    def __init__(self, *args):
        WindowTabWidget.__init__(self, 'Display', *args)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.create_addon_tabs(PROCESS_DISPLAY)


class IoWindow(WindowTabWidget):

    def __init__(self, *args):
        WindowTabWidget.__init__(self, 'I/O', *args)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.create_addon_tabs(PROCESS_IO)


class PlottingWindow(WindowWidget):

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

        self.exposed.append(PlottingWindow.add_buffer_attribute)

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
                    n_idcs, n_times, n_data = read_attribute(attr_name)
                    if n_times[0] is None:
                        continue
                    data['last_idx'] = n_idcs[0]
                else:
                    # Read this attribute starting from the last_idx
                    n_idcs, n_times, n_data = read_attribute(attr_name, from_idx=last_idx)


            except Exception as exc:
                Logging.write(Logging.WARNING,
                              f'Problem trying to read attribute "{attr_name}" from_idx={data["last_idx"]}'
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
