"""
MappApp ./gui/Integrated.py - GUI addons meant to be integrated into the main window.
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

import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QLabel
import pyqtgraph as pg
import time

import Config
from process.Controller import Controller
import Def
import gui.Camera
import IPC
import Logging
from process import Gui
import protocols

from core.routine import Routines

if Def.Env == Def.EnvTypes.Dev:
    pass

class IntegratedWidget(QtWidgets.QGroupBox):

    def __init__(self, group_name, main):
        QtWidgets.QGroupBox.__init__(self, group_name)
        self.main: Gui = main

        # List of exposed methods to register for rpc callbacks
        self.exposed = list()

    def create_hooks(self):
        for fun in self.exposed:
            fun_str = fun.__qualname__
            print('REG ', fun_str)
            self.main.register_rpc_callback(self, fun_str, fun)

class Protocols(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Protocols', *args)
        self.setLayout(QtWidgets.QGridLayout())

        # File list
        self._lwdgt_files = QtWidgets.QListWidget()
        self._lwdgt_files.itemSelectionChanged.connect(self.update_file_list)
        self.layout().addWidget(QtWidgets.QLabel('Files'), 0, 0)
        self.layout().addWidget(self._lwdgt_files, 1, 0)
        # Protocol list
        self.lwdgt_protocols = QtWidgets.QListWidget()
        #self._lwdgt_protocols.itemSelectionChanged.connect(self._updateProtocolInfo)
        self.layout().addWidget(QtWidgets.QLabel('Protocols'), 0, 1)
        self.layout().addWidget(self.lwdgt_protocols, 1, 1)

        # Protocol (phase) progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setTextVisible(False)
        self.layout().addWidget(self.progress, 0, 2)

        # Start button
        self.wdgt_controls = QtWidgets.QWidget()
        self.layout().addWidget(self.wdgt_controls, 1, 2)
        self.wdgt_controls.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt_controls.btn_start = QtWidgets.QPushButton('Start protocol')
        self.wdgt_controls.btn_start.clicked.connect(self.start_protocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_start)
        # Abort protocol button
        self.wdgt_controls.btn_abort = QtWidgets.QPushButton('Abort protocol')
        self.wdgt_controls.btn_abort.clicked.connect(self.abort_protocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_abort)

        # Spacer
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.wdgt_controls.layout().addItem(vSpacer)

        # Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(200)
        self._tmr_update.timeout.connect(self.update_ui)
        self._tmr_update.start()

        # Once set up: compile file list for first time
        self._compile_file_list()

    def _compile_file_list(self):
        self._lwdgt_files.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for file in protocols.all():
            self._lwdgt_files.addItem(file)

    def update_file_list(self):
        self.lwdgt_protocols.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for protocol in protocols.read(protocols.open_(self._lwdgt_files.currentItem().text())):
            self.lwdgt_protocols.addItem(protocol.__name__)

    def update_ui(self):

        # Enable/Disable control elements
        ctrl_is_idle = IPC.in_state(Def.State.IDLE, Def.Process.Controller)
        self.wdgt_controls.btn_start.setEnabled(ctrl_is_idle and len(self.lwdgt_protocols.selectedItems()) > 0)
        self.lwdgt_protocols.setEnabled(ctrl_is_idle)
        self._lwdgt_files.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])
        self.wdgt_controls.btn_abort.setEnabled(protocol_is_running)

        # Update progress
        start_phase = IPC.Control.Protocol[Def.ProtocolCtrl.phase_start]
        if not(start_phase is None):
            self.progress.setEnabled(True)
            phase_diff = time.time() - start_phase
            self.progress.setMaximum(int((IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] - start_phase) * 10))
            if phase_diff > 0.:
                self.progress.setValue(int(phase_diff * 10))

        if not(bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])):
            self.progress.setEnabled(False)

    def start_protocol(self):
        file_name = self._lwdgt_files.currentItem().text()
        protocol_name = self.lwdgt_protocols.currentItem().text()

        # Start recording
        self.main.recordings.start_recording()

        # Start protocol
        IPC.rpc(Def.Process.Controller, Controller.start_protocol,
                '.'.join([file_name, protocol_name]))

    def abort_protocol(self):
        IPC.rpc(Controller.name, Controller.abortProtocol)


class ProcessMonitor(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self,  'Process monitor', *args)

        self._setup_ui()

    def _setup_ui(self):

        self.setFixedWidth(150)

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        self.setMinimumSize(QtCore.QSize(0,0))
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        ## Controller process status
        self._le_controllerState = QtWidgets.QLineEdit('')
        self._le_controllerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Controller), 0, 0)
        self.layout().addWidget(self._le_controllerState, 0, 1)

        ## Camera process status
        self._le_cameraState = QtWidgets.QLineEdit('')
        self._le_cameraState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Camera), 1, 0)
        self.layout().addWidget(self._le_cameraState, 1, 1)

        ## Display process status
        self._le_displayState = QtWidgets.QLineEdit('')
        self._le_displayState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Display), 2, 0)
        self.layout().addWidget(self._le_displayState, 2, 1)

        ## Gui process status
        self._le_guiState = QtWidgets.QLineEdit('')
        self._le_guiState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.GUI), 3, 0)
        self.layout().addWidget(self._le_guiState, 3, 1)

        ## IO process status
        self._le_ioState = QtWidgets.QLineEdit('')
        self._le_ioState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Io), 4, 0)
        self.layout().addWidget(self._le_ioState, 4, 1)

        ## Worker process status
        self._le_workerState = QtWidgets.QLineEdit('')
        self._le_workerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Worker), 5, 0)
        self.layout().addWidget(self._le_workerState, 5, 1)

        self.layout().addItem(vSpacer, 6, 0)

        ## Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._updateStates)
        self._tmr_updateGUI.start()


    def _setProcessState(self, le: QtWidgets.QLineEdit, code):
        ### Set text
        le.setText(Def.MapStateToStr[code] if code in Def.MapStateToStr else '')

        ### Set style
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

    def _updateStates(self):
        """This method sets the process state according to the current global state variables.
        Additionally it modifies 
        """

        self._setProcessState(self._le_controllerState, IPC.get_state(Def.Process.Controller))
        self._setProcessState(self._le_cameraState, IPC.get_state(Def.Process.Camera))
        self._setProcessState(self._le_displayState, IPC.get_state(Def.Process.Display))
        self._setProcessState(self._le_guiState, IPC.get_state(Def.Process.GUI))
        self._setProcessState(self._le_ioState, IPC.get_state(Def.Process.Io))
        self._setProcessState(self._le_workerState, IPC.get_state(Def.Process.Worker))


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
        self.le_folder = QtWidgets.QLineEdit()
        self.le_folder.setEnabled(False)
        self.wdgt.layout().addWidget(QLabel('Folder'), 0, 0)
        self.wdgt.layout().addWidget(self.le_folder, 0, 1)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Data compression
        self.cb_compression = QtWidgets.QComboBox()
        self.cb_compression.currentTextChanged.connect(self.update_compression_opts)
        #self.cb_compression.currentTextChanged.connect(self.set_compression)
        self.wdgt.layout().addWidget(QLabel('Compression'), 1, 0)
        self.cb_compr_opts = QtWidgets.QComboBox()
        self.cb_compression.addItems(['None', 'GZIP', 'LZF'])
        #self.cb_compr_opts.currentTextChanged.connect(self.set_compression_opts)
        self.wdgt.layout().addWidget(self.cb_compression, 1, 1)
        self.wdgt.layout().addWidget(QLabel('Compr. options'), 2, 0)
        self.wdgt.layout().addWidget(self.cb_compr_opts, 2, 1)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_start.clicked.connect(self.start_recording)
        self.wdgt.layout().addWidget(self.btn_start, 3, 0, 1, 2)
        # Pause
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.clicked.connect(lambda: IPC.rpc(Def.Process.Controller, Controller.pause_recording))
        self.wdgt.layout().addWidget(self.btn_pause, 4, 0, 1, 2)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.clicked.connect(self.finalize_recording)
        self.wdgt.layout().addWidget(self.btn_stop, 5, 0, 1, 2)

        # Show recorded routines
        self.gb_routines = QtWidgets.QGroupBox('Recording routines')
        self.gb_routines.setLayout(QtWidgets.QVBoxLayout())
        for routine_id in Config.Recording[Def.RecCfg.routines]:
            self.gb_routines.layout().addWidget(QtWidgets.QLabel(routine_id))
        self.gb_routines.layout().addItem(vSpacer)
        self.wdgt.layout().addWidget(self.gb_routines, 0, 2, 7, 1)
        self.wdgt.layout().addItem(vSpacer, 6, 0)

        # Set timer for GUI update
        self.tmr_update_gui = QtCore.QTimer()
        self.tmr_update_gui.setInterval(200)
        self.tmr_update_gui.timeout.connect(self.update_ui)
        self.tmr_update_gui.start()

    def start_recording(self):

        compression_method = self.get_compression_method()
        compression_opts = self.get_compression_opts()

        # Call controller
        IPC.rpc(Def.Process.Controller, Controller.start_recording,
                compression_method=compression_method,
                compression_opts=compression_opts)

    def finalize_recording(self):
        # First: pause recording
        IPC.rpc(Def.Process.Controller, Controller.pause_recording)

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
        IPC.rpc(Def.Process.Controller, Controller.stop_recording)

    def toggle_enable(self, newstate):
        IPC.rpc(Def.Process.Controller, Controller.toggle_enable_recording, newstate)

    def get_compression_method(self):
        method = self.cb_compression.currentText()
        if method == 'None':
            method = None
        else:
            method = method.lower()

        return method

    def get_compression_opts(self):
        method = self.cb_compression.currentText()
        opts = self.cb_compr_opts.currentText()

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
        self.cb_compr_opts.clear()

        compr = self.cb_compression.currentText()
        if compr == 'None':
            self.cb_compr_opts.addItem('None')
        elif compr == 'GZIP':
            levels = range(10)
            self.cb_compr_opts.addItems([f'{i} (shuffle)' for i in levels])
            self.cb_compr_opts.addItems([str(i) for i in levels])
        elif compr == 'LZF':
            self.cb_compr_opts.addItems(['None', 'Shuffle'])

    def update_ui(self):
        """(Periodically) update UI based on shared configuration"""

        enabled = Config.Recording[Def.RecCfg.enabled]
        active = IPC.Control.Recording[Def.RecCtrl.active]
        current_folder = IPC.Control.Recording[Def.RecCtrl.folder]

        if active:
            self.wdgt.setStyleSheet('QWidget#RecordingWidget {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.wdgt.setStyleSheet('QWidget#RecordingWidgetQGroupBox#RecGroupBox {background: rgba(0, 0, 0, 0.0);}')

        # Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        # Set current folder
        self.le_folder.setText(IPC.Control.Recording[Def.RecCtrl.folder])

        # Set buttons dis-/enabled
        # Start
        self.btn_start.setEnabled(not(active) and enabled)
        self.btn_start.setText('Start' if IPC.in_state(Def.State.IDLE, Def.Process.Controller) else 'Resume')
        # Pause // TODO: implement pause functionality during non-protocol recordings?
        #self._btn_pause.setEnabled(active and enabled)
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(bool(IPC.Control.Recording[Def.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(IPC.Control.Protocol[Def.ProtocolCtrl.name]):
            self.btn_stop.setEnabled(False)


class Log(IntegratedWidget):

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
        self.timer_logging.timeout.connect(self.printLog)
        self.timer_logging.start(50)


    def printLog(self):
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
        IntegratedWidget.__init__(self, 'Camera>', *args)

        self.exposed.append(Camera.update_fps_estimate)

        self.stream_fps = 20

        self.setMinimumSize(400, 400)
        self.setMaximumSize(800, 700)

        self.setLayout(QtWidgets.QGridLayout())

        # Top-left spacer
        spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout().addItem(spacer, 0, 0)

        # FPS counter
        self.fps_counter = QtWidgets.QLineEdit('FPS N/A')
        self.fps_counter.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.fps_counter.setEnabled(False)
        self.layout().addWidget(self.fps_counter, 0, 1)

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget, 1, 0, 1, 2)

        # Add camera addons
        avail_addons = Config.Gui[Def.GuiCfg.addons]
        use_addons = list()
        if Def.Process.Camera in avail_addons:
            if len(avail_addons[Def.Process.Camera]) == 0:
                use_addons.append('LiveCamera')
            else:
                use_addons.extend(avail_addons[Def.Process.Camera])

        for addon_name in use_addons:
            if not(bool(addon_name)):
                continue

            # TODO: expand this to draw from all files in ./gui/
            wdgt = getattr(gui.Camera, addon_name)(self)
            if not(wdgt.moduleIsActive):
                Logging.write(Logging.WARNING, 'Addon {} could not be activated'
                              .format(addon_name))
                continue
            self.tab_widget.addTab(wdgt, addon_name)

        # Select routine for FPS estimation (if any available)
        # If no routines are set, don't even start frame update timer
        routines = Config.Camera[Def.CameraCfg.routines]
        if bool(routines):
            # Use first routine in list
            routine = routines[list(routines.keys())[0]][0]
            self.used_buffer = IPC.Routines.Camera.get_buffer(routine)
            # Grab times for first random attribute
            self.first_attr_name = self.used_buffer.list_attributes()[0]

            Logging.write(Logging.INFO,
                          f'Camera UI using attribute "{routine}/{self.first_attr_name}"'
                          'for FPS estimation')

            # Set frame update timer
            self.timer_frame_update = QtCore.QTimer()
            self.timer_frame_update.setInterval(1000 // self.stream_fps)
            self.timer_frame_update.timeout.connect(self.update_frames)
            self.timer_frame_update.start()

    def update_fps_estimate(self, fps):
        self.fps_counter.setText('FPS {:.1f}/{:.1f}'.format(fps, Config.Camera[Def.CameraCfg.fps]))

    def update_frames(self):

        # Update frames in tabbed widgets
        for idx in range(self.tab_widget.count()):
            self.tab_widget.widget(idx).update_frame()

        # Update FPS counter
        # target_fps = Config.Camera[Def.CameraCfg.fps]
        # frametimes = getattr(self.used_buffer, self.first_attr_name).get_times(target_fps//2)

        # if any([t is None for t in frametimes]):
        #     return

        # Display FPS
        # frame_dts = [v2-v1 for v1, v2 in zip(frametimes[:-1], frametimes[1:])]
        # mean_frame_dt = sum(frame_dts) / (len(frametimes)-1)
        # fps = 1./mean_frame_dt
        # if any([dt < 0 for dt in frame_dts]):
        #     print('FPS:', fps, frametimes)
        # self.fps_counter.setText('FPS {:.1f}/{:.1f}'.format(fps, target_fps))


import h5py

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

    def add_buffer_attribute(self, process_name, attr_name, start_idx=0, name=None, axis=None):

        id = (process_name, attr_name)

        # Set axis
        if axis is None:
            axis = 'defaulty'

        # Set name
        if name is None:
            name = f'{process_name}:{attr_name}'

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

        for (process_name, attr_name), data in self.plot_data.items():

            # Read new values from buffer
            routines: Routines = getattr(IPC.Routines, process_name)
            try:
                n_idcs, n_times, n_data = routines.read(attr_name, from_idx=data['last_idx'])
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
