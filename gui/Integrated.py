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

import logging
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

        ### Finally: stop recording
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

        self._txe_log = QtWidgets.QTextEdit()
        self._txe_log.setReadOnly(True)
        self._txe_log.setFontFamily('Courier')
        self._txe_log.setFontPointSize(10)
        self.layout().addWidget(self._txe_log)

        ### Set initial log line count
        self.logccount = 0

        ### Set timer for updating of log
        self._tmr_logger = QtCore.QTimer()
        self._tmr_logger.timeout.connect(self.printLog)
        self._tmr_logger.start(50)


    def printLog(self):
        if IPC.Log.File is None:
            return

        if len(IPC.Log.History) > self.logccount:
            for record in IPC.Log.History[self.logccount:]:
                if record['levelno'] > 10:
                    line = '{} : {:10} : {:10} : {}'\
                        .format(record['asctime'], record['name'], record['levelname'], record['msg'])
                    self._txe_log.append(line)

                self.logccount += 1


class Camera(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Camera', *args)

        self.stream_fps = 30

        self._setup_ui()

    def _setup_ui(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        # FPS counter
        self.fps_counter = QtWidgets.QWidget(parent=self)
        self.fps_counter.setEnabled(False)
        self.fps_counter.setLayout(QtWidgets.QHBoxLayout())
        self.fps_counter.layout().setContentsMargins(0, 0, 0, 0)
        # Spacer
        self.fps_counter.spacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.fps_counter.layout().addItem(self.fps_counter.spacer)
        # Lineedit
        self.fps_counter.le = QtWidgets.QLineEdit('FPS N/A')
        self.fps_counter.le.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.fps_counter.layout().addWidget(self.fps_counter.le)
        self.layout().addWidget(self.fps_counter)

        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        ### Add camera addons
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
                Logging.write(logging.WARNING, 'Addon {} could not be activated'
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

            Logging.write(Logging.INFO, f'Camera UI using routine "{routine}"')

            # Set frame update timer
            self.timer_frame_update = QtCore.QTimer()
            self.timer_frame_update.setInterval(1000 // self.stream_fps)
            self.timer_frame_update.timeout.connect(self.update_frames)
            self.timer_frame_update.start()

    def update_frames(self):

        # Update frames in tabbed widgets
        for idx in range(self.tab_widget.count()):
            self.tab_widget.widget(idx).update_frame()

        # Update FPS counter
        target_fps = Config.Camera[Def.CameraCfg.fps]
        # Grab times for first random attribute
        first_attr_name = self.used_buffer.list_attributes()[0]
        frametimes = getattr(self.used_buffer, first_attr_name).get_times(target_fps)

        if any([t is None for t in frametimes]):
            return

        # Display FPS
        frame_dts = [v2-v1 for v1, v2 in zip(frametimes[:-1], frametimes[1:])]
        mean_frame_dt = sum(frame_dts) / (len(frametimes)-1)
        fps = 1./mean_frame_dt
        if any([dt < 0 for dt in frame_dts]):
            print('FPS:', fps, frametimes)
        self.fps_counter.le.setText('FPS {:.1f}/{:.1f}'.format(fps, target_fps))

import numpy as np
from routines.camera.CameraRoutines import  EyePosDetectRoutine
from routines.io.IoRoutines import TriggerLedArenaFlash

class Plotter(IntegratedWidget):
    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Plotter', *args)

        #self.exposed.append(Plotter.add_line)

        self.setLayout(QtWidgets.QGridLayout())

        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.plot_item = pg.PlotItem()
        self.graphics_widget.addItem(self.plot_item)#addPlot(0,0,1,10)
        self.layout().addWidget(self.graphics_widget, 0, 0)

        ### Start timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(50)
        self._tmr_update.timeout.connect(self.update_data)
        self._tmr_update.start()

        self.start_time = time.time()

        # TODO: basically everything here is temporary for Giulia's experiments
        self.le_pos_t = []
        self.le_pos = []
        pg.mkPen()
        self.le_pos_item = pg.PlotDataItem(pen=(255,0,0))
        self.plot_item.addItem(self.le_pos_item)
        self.re_pos_item = pg.PlotDataItem(pen=(0,0,255))
        self.plot_item.addItem(self.re_pos_item)
        self.le_sacc_item = pg.PlotDataItem(pen=pg.mkPen(color=(255,0,0), style=QtCore.Qt.DashLine, width=2))
        self.plot_item.addItem(self.le_sacc_item)
        self.re_sacc_item = pg.PlotDataItem(pen=pg.mkPen(color=(0,0,255), style=QtCore.Qt.DashLine, width=2))
        self.plot_item.addItem(self.re_sacc_item)
        self.trigger_item = pg.PlotDataItem(pen=pg.mkPen(color=(255,255,255), style=QtCore.Qt.DashLine, width=1))
        self.plot_item.addItem(self.trigger_item)
        self.flash_item = pg.PlotDataItem(pen=pg.mkPen(color=(255,255,0), style=QtCore.Qt.DashLine, width=1))
        self.plot_item.addItem(self.flash_item)

    def update_data(self):
        eye_routine = EyePosDetectRoutine
        eye_rout_n = eye_routine.__name__
        _, _, le_pos = IPC.Routines.Camera.read(f'{eye_rout_n}/{eye_routine.ang_le_pos_prefix}0', last=300)
        _, _, re_pos = IPC.Routines.Camera.read(f'{eye_rout_n}/{eye_routine.ang_re_pos_prefix}0', last=300)
        _, _, le_sacc = IPC.Routines.Camera.read(f'{eye_rout_n}/{eye_routine.le_sacc_prefix}0', last=300)
        _, eye_times, re_sacc = IPC.Routines.Camera.read(f'{eye_rout_n}/{eye_routine.re_sacc_prefix}0', last=300)

        io_routine = TriggerLedArenaFlash
        io_rout_n = io_routine.__name__
        _, _, trigger = IPC.Routines.Io.read(f'{io_rout_n}/trigger_set', last=15000)
        _, io_times, flash = IPC.Routines.Io.read(f'{io_rout_n}/flash_state', last=15000)
        if eye_times[0] is None:
            return

        y_max_scale = max(np.max(le_pos), np.max(re_pos))
        self.le_pos_item.setData(x=eye_times, y=le_pos.flatten())
        self.re_pos_item.setData(x=eye_times, y=re_pos.flatten())
        self.le_sacc_item.setData(x=eye_times, y=le_sacc.flatten() * y_max_scale)
        self.re_sacc_item.setData(x=eye_times, y=re_sacc.flatten() * y_max_scale)

        if io_times[0] is None:
            return

        self.trigger_item.setData(x=io_times, y=trigger.flatten() * y_max_scale)
        self.flash_item.setData(x=io_times, y=flash.flatten() * y_max_scale)
