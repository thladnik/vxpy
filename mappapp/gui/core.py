"""
MappApp ./gui/core.py
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
import h5py
import numpy as np
from os.path import abspath
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel
import pyqtgraph as pg
import time

from mappapp import Config
from mappapp import Def
from mappapp import IPC
from mappapp import Logging
from mappapp import process
from mappapp.core.gui import IntegratedWidget


class ProcessMonitor(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self,  'Process monitor', *args)

        self.exposed.append(ProcessMonitor.update_process_interval)

        self._setup_ui()

    def _setup_ui(self):

        self.setFixedWidth(250)

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.process_intervals = dict()

        # Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        self.setMinimumSize(QtCore.QSize(0,0))
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.layout().setColumnMinimumWidth(2, 150)

        # Controller process status
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Controller),0,0)
        self.controller_state = QtWidgets.QLineEdit('')
        self.controller_state.setDisabled(True)
        self.layout().addWidget(self.controller_state, 0, 1)
        self.controller_interval = QtWidgets.QLineEdit('')
        self.controller_interval.setDisabled(True)
        self.layout().addWidget(self.controller_interval, 0, 2)
        self.process_intervals[Def.Process.Controller] = self.controller_interval

        # Camera process status
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Camera),1,0)
        self.camera_state = QtWidgets.QLineEdit('')
        self.camera_state.setDisabled(True)
        self.layout().addWidget(self.camera_state, 1, 1)
        self.camera_interval = QtWidgets.QLineEdit('')
        self.camera_interval.setDisabled(True)
        self.layout().addWidget(self.camera_interval, 1, 2)
        self.process_intervals[Def.Process.Camera] = self.camera_interval

        # Display process status
        self.display_state = QtWidgets.QLineEdit('')
        self.display_state.setDisabled(True)
        self.display_interval = QtWidgets.QLineEdit('')
        self.display_interval.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Display),2,0)
        self.layout().addWidget(self.display_state, 2, 1)
        self.layout().addWidget(self.display_interval, 2, 2)
        self.process_intervals[Def.Process.Display] = self.display_interval

        # Gui process status
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Gui),3,0)
        self.gui_state = QtWidgets.QLineEdit('')
        self.gui_state.setDisabled(True)
        self.layout().addWidget(self.gui_state, 3, 1)
        self.gui_interval = QtWidgets.QLineEdit('')
        self.gui_interval.setDisabled(True)
        self.layout().addWidget(self.gui_interval, 3, 2)
        self.process_intervals[Def.Process.Gui] = self.gui_interval

        # IO process status
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Io),4,0)
        self.io_state = QtWidgets.QLineEdit('')
        self.layout().addWidget(self.io_state, 4, 1)
        self.io_state.setDisabled(True)
        self.io_interval = QtWidgets.QLineEdit('')
        self.io_interval.setDisabled(True)
        self.layout().addWidget(self.io_interval, 4, 2)
        self.process_intervals[Def.Process.Io] = self.io_interval

        # Worker process status
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Worker),5,0)
        self.worker_state = QtWidgets.QLineEdit('')
        self.worker_state.setDisabled(True)
        self.layout().addWidget(self.worker_state, 5, 1)
        self.worker_interval = QtWidgets.QLineEdit('')
        self.worker_interval.setDisabled(True)
        self.layout().addWidget(self.worker_interval, 5, 2)
        self.process_intervals[Def.Process.Worker] = self.worker_interval

        self.layout().addItem(vSpacer, 6, 0)

        # Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._update_states)
        self._tmr_updateGUI.start()


    def update_process_interval(self, process_name, target_inval, mean_inval, std_inval):
        if process_name in self.process_intervals:
            self.process_intervals[process_name].setText('{:.1f}/{:.1f} ({:.1f}) ms'
                                                         .format(mean_inval * 1000,
                                                                 target_inval * 1000,
                                                                 std_inval * 1000))
        else:
            print(process_name, '{:.2f} +/- {:.2f}ms'.format(mean_inval * 1000, std_inval * 1000))

    def _set_process_state(self,le: QtWidgets.QLineEdit,code):
        # Set text
        le.setText(Def.MapStateToStr[code] if code in Def.MapStateToStr else '')

        # Set style
        if code == Def.State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif code == Def.State.STARTING:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.STOPPED:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        elif code == Def.State.RUNNING:
            le.setStyleSheet('color: #deb737; font-weight:bold;')
        else:
            le.setStyleSheet('color: #000000')

    def _update_states(self):
        self._set_process_state(self.controller_state, IPC.get_state(Def.Process.Controller))
        self._set_process_state(self.camera_state, IPC.get_state(Def.Process.Camera))
        self._set_process_state(self.display_state, IPC.get_state(Def.Process.Display))
        self._set_process_state(self.gui_state, IPC.get_state(Def.Process.Gui))
        self._set_process_state(self.io_state, IPC.get_state(Def.Process.Io))
        self._set_process_state(self.worker_state, IPC.get_state(Def.Process.Worker))


class Recording(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Recordings', *args)
        # Create inner widget
        self.setLayout(QtWidgets.QVBoxLayout())

        self.wdgt = QtWidgets.QWidget()
        self.wdgt.setLayout(QtWidgets.QGridLayout())
        self.wdgt.setObjectName('RecordingWidget')
        self.layout().addWidget(self.wdgt)

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        # Basic properties
        self.setCheckable(True)
        self.setMaximumWidth(400)

        # Current folder
        self.folder_wdgt = QtWidgets.QWidget()
        self.folder_wdgt.setLayout(QtWidgets.QGridLayout())
        self.folder_wdgt.layout().setContentsMargins(0, 0, 0, 0)

        self.folder_wdgt.layout().addWidget(QLabel('Base dir.'), 0, 0)
        self.base_dir = QtWidgets.QLineEdit('')
        self.base_dir.setDisabled(True)
        self.folder_wdgt.layout().addWidget(self.base_dir, 0, 1, 1, 2)

        self.select_folder = QtWidgets.QPushButton('Select...')
        self.select_folder.setDisabled(True)
        self.folder_wdgt.layout().addWidget(self.select_folder, 1, 1)
        self.open_folder = QtWidgets.QPushButton('Open')
        self.open_folder.clicked.connect(self.open_base_folder)
        self.folder_wdgt.layout().addWidget(self.open_folder, 1, 2)

        self.folder_wdgt.layout().addWidget(QLabel('Folder'), 2, 0)
        self.rec_folder = QtWidgets.QLineEdit()
        self.rec_folder.setEnabled(False)
        self.folder_wdgt.layout().addWidget(self.rec_folder, 2, 1, 1, 2)

        self.wdgt.layout().addWidget(self.folder_wdgt, 1, 0, 1, 2)
        self.hsep = QtWidgets.QFrame()
        self.hsep.setFrameShape(QtWidgets.QFrame.HLine)
        self.wdgt.layout().addWidget(self.hsep, 2, 0, 1, 2)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Left widget
        self.left_wdgt = QtWidgets.QWidget()
        self.left_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.left_wdgt.layout().setContentsMargins(0,0,0,0)
        self.wdgt.layout().addWidget(self.left_wdgt, 5, 0)

        # Data compression
        self.left_wdgt.layout().addWidget(QLabel('Compression'))
        self.compr = QtWidgets.QComboBox()
        self.compr_opts = QtWidgets.QComboBox()
        self.compr.currentTextChanged.connect(self.update_compression_opts)
        self.compr.addItems(['None', 'GZIP', 'LZF'])
        self.left_wdgt.layout().addWidget(self.compr)
        self.left_wdgt.layout().addWidget(self.compr_opts)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_start.clicked.connect(self.start_recording)
        self.left_wdgt.layout().addWidget(self.btn_start)
        # Pause
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.clicked.connect(self.pause_recording)
        self.left_wdgt.layout().addWidget(self.btn_pause)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.clicked.connect(self.finalize_recording)
        self.left_wdgt.layout().addWidget(self.btn_stop)

        # Show recorded routines
        self.rec_routines = QtWidgets.QGroupBox('Recording routines')
        self.rec_routines.setLayout(QtWidgets.QVBoxLayout())
        for routine_id in Config.Recording[Def.RecCfg.routines]:
            self.rec_routines.layout().addWidget(QtWidgets.QLabel(routine_id))
        self.rec_routines.layout().addItem(vSpacer)
        self.wdgt.layout().addWidget(self.rec_routines, 5, 1)

        # Set timer for GUI update
        self.tmr_update_gui = QtCore.QTimer()
        self.tmr_update_gui.setInterval(200)
        self.tmr_update_gui.timeout.connect(self.update_ui)
        self.tmr_update_gui.start()

    def open_base_folder(self):
        output_path = abspath(Config.Recording[Def.RecCfg.output_folder])
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(output_path.replace('\\', '/')))

    def start_recording(self):

        compression_method = self.get_compression_method()
        compression_opts = self.get_compression_opts()

        # Call controller
        IPC.rpc(Def.Process.Controller,process.Controller.start_recording,
                compression_method=compression_method,
                compression_opts=compression_opts)

    def pause_recording(self):
        IPC.rpc(Def.Process.Controller,process.Controller.pause_recording)

    def finalize_recording(self):
        # First: pause recording
        IPC.rpc(Def.Process.Controller,process.Controller.pause_recording)

        reply = QtWidgets.QMessageBox.question(self, 'Finalize recording', 'Give me session data and stuff...',
                                               QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard,
                                               QtWidgets.QMessageBox.Save)
        if reply == QtWidgets.QMessageBox.Save:
            print('Save metadata and stuff...')
        else:
            reply = QtWidgets.QMessageBox.question(self, 'Confirm discard', 'Are you sure you want to DISCARD all recorded data?',
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                print('Fine... I`ll trash it all..')
            else:
                print('Puh... good choice')

        # Finally: stop recording
        print('Stop recording...')
        IPC.rpc(Def.Process.Controller,process.Controller.stop_recording)

    def toggle_enable(self, newstate):
        IPC.rpc(Def.Process.Controller,process.Controller.set_enable_recording,newstate)

    def get_compression_method(self):
        method = self.compr.currentText()
        if method == 'None':
            method = None
        else:
            method = method.lower()

        return method

    def get_compression_opts(self):
        method = self.compr.currentText()
        opts = self.compr_opts.currentText()

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
        self.compr_opts.clear()

        compr = self.compr.currentText()
        if compr == 'None':
            self.compr_opts.addItem('None')
        elif compr == 'GZIP':
            levels = range(10)
            self.compr_opts.addItems([f'{i} (shuffle)' for i in levels])
            self.compr_opts.addItems([str(i) for i in levels])
        elif compr == 'LZF':
            self.compr_opts.addItems(['None', 'Shuffle'])

    def update_ui(self):
        """(Periodically) update UI based on shared configuration"""

        enabled = IPC.Control.Recording[Def.RecCtrl.enabled]
        active = IPC.Control.Recording[Def.RecCtrl.active]
        current_folder = IPC.Control.Recording[Def.RecCtrl.folder]

        if active and enabled:
            self.wdgt.setStyleSheet('QWidget#RecordingWidget {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.wdgt.setStyleSheet('QWidget#RecordingWidgetQGroupBox#RecGroupBox {background: rgba(0, 0, 0, 0.0);}')

        # Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        # Set current folder
        self.rec_folder.setText(IPC.Control.Recording[Def.RecCtrl.folder])

        # Set buttons dis-/enabled
        # Start
        self.btn_start.setEnabled(not(active) and enabled)
        self.btn_start.setText('Start' if IPC.in_state(Def.State.IDLE,Def.Process.Controller) else 'Resume')
        # Pause // TODO: implement pause functionality during non-protocol recordings?
        #self._btn_pause.setEnabled(active and enabled)
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(bool(IPC.Control.Recording[Def.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(IPC.Control.Protocol[Def.ProtocolCtrl.name]):
            self.btn_stop.setEnabled(False)

        self.base_dir.setText(Config.Recording[Def.RecCfg.output_folder])


class Logger(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Log', *args)

        self.setLayout(QtWidgets.QHBoxLayout())

        self.txe_log = QtWidgets.QTextEdit()
        self.txe_log.setReadOnly(True)
        self.txe_log.setFontFamily('Courier')
        self.layout().addWidget(self.txe_log)

        # Set initial log line count
        self.logccount = 0

        # Set timer for updating of log
        self.timer_logging = QtCore.QTimer()
        self.timer_logging.timeout.connect(self.print_log)
        self.timer_logging.start(50)


    def print_log(self):
        if IPC.Log.File is None:
            return

        if len(IPC.Log.History) > self.logccount:
            for record in IPC.Log.History[self.logccount:]:
                if record['levelno'] > 10:
                    line = '{} : {:10} : {:10} : {}'\
                        .format(record['asctime'], record['name'], record['levelname'], record['msg'])
                    self.txe_log.append(line)

                self.logccount += 1


class Camera(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Camera', *args)

        self.stream_fps = 20

        self.setMinimumSize(400, 400)
        self.setMaximumSize(800, 700)

        self.setLayout(QtWidgets.QHBoxLayout())

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        self.add_widgets(Def.Process.Camera)

        # Select routine for FPS estimation (if any available)
        # If no routines are set, don't even start frame update timer
        if bool(Config.Camera[Def.CameraCfg.routines]):
            # Set frame update timer
            self.timer_frame_update = QtCore.QTimer()
            self.timer_frame_update.setInterval(1000 // self.stream_fps)
            self.timer_frame_update.timeout.connect(self.update_frames)
            self.timer_frame_update.start()

    def update_frames(self):

        # Update frames in tabbed widgets
        for idx in range(self.tab_widget.count()):
            self.tab_widget.widget(idx).update_frame()


class Display(IntegratedWidget):

    def __init__(self,*args):
        IntegratedWidget.__init__(self,'Display',*args)
        self.setLayout(QtWidgets.QHBoxLayout())

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        self.add_widgets(Def.Process.Display)


class Io(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'I/O', *args)
        self.setLayout(QtWidgets.QVBoxLayout())

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        self.add_widgets(Def.Process.Io)


class Plotter(IntegratedWidget):

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
        IntegratedWidget.__init__(self, 'Plotter', *args)

        hspacer = QtWidgets.QSpacerItem(1, 1,
                                        QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Minimum)
        self.cmap = (np.array(self.cmap) * 255).astype(int)

        self.exposed.append(Plotter.add_buffer_attribute)

        self.setLayout(QtWidgets.QGridLayout())

        self.plot_widget = pg.PlotWidget()
        self.plot_item: pg.PlotItem = self.plot_widget.plotItem
        self.layout().addWidget(self.plot_widget, 1, 0, 1, 5)

        self.legend_item = pg.LegendItem()
        self.legend_item.setParentItem(self.plot_item)

        # Start timer
        self.tmr_update_data = QtCore.QTimer()
        self.tmr_update_data.setInterval(1000 // 20)
        self.tmr_update_data.timeout.connect(self.read_buffer_data)
        self.tmr_update_data.start()

        self.start_time = time.time()

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

        self.cache = h5py.File('_plotter_temp.h5', 'w')

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
        items = [o for o in self.plot_item.scene().items(a0.pos()) if isinstance(o, pg.AxisItem)]
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
                if current_pen.style() == 0:
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

    def add_buffer_attribute(self, routine_cls, attr_name, start_idx=0, name=None, axis=None):

        id = (routine_cls, attr_name)

        # Set axis
        if axis is None:
            axis = 'defaulty'

        # Set name
        if name is None:
            name = f'{routine_cls}:{attr_name}'

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
                                  'last_idx': start_idx,
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

        for (routine_cls, attr_name), data in self.plot_data.items():

            # Read new values from buffer
            process_name = routine_cls.process_name
            try:
                n_idcs, n_times, n_data = getattr(IPC,process_name).read(routine_cls,attr_name,from_idx=data['last_idx'])
            except Exception as exc:
                Logging.write(Logging.WARNING,
                              f'Problem trying to read {process_name}:{attr_name} from_idx={data["last_idx"]}'
                              f'// Exception: {exc}')
                continue

            if len(n_times) == 0:
                continue

            try:
                n_times = np.array(n_times) - self.start_time
                n_data = np.array(n_data)
            except Exception as exc:
                print(attr_name, self.start_time, n_times)
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
