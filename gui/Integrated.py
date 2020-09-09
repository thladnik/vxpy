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
import numpy as np
from PyQt5 import QtCore, QtWidgets
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


class Protocols(QtWidgets.QGroupBox):

    def __init__(self, _main):
        self.main = _main
        QtWidgets.QGroupBox.__init__(self, 'Protocols', parent=_main)

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())

        ### File list
        self._lwdgt_files = QtWidgets.QListWidget()
        self._lwdgt_files.itemSelectionChanged.connect(self.updateFileList)
        self.layout().addWidget(QtWidgets.QLabel('Files'), 0, 0)
        self.layout().addWidget(self._lwdgt_files, 1, 0)
        ### Protocol list
        self.lwdgt_protocols = QtWidgets.QListWidget()
        #self._lwdgt_protocols.itemSelectionChanged.connect(self._updateProtocolInfo)
        self.layout().addWidget(QtWidgets.QLabel('Protocols'), 0, 1)
        self.layout().addWidget(self.lwdgt_protocols, 1, 1)

        ### Protocol (phase) progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setTextVisible(False)
        self.layout().addWidget(self.progress, 0, 2)

        ### Start button
        self.wdgt_controls = QtWidgets.QWidget()
        self.layout().addWidget(self.wdgt_controls, 1, 2)
        self.wdgt_controls.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt_controls.btn_start = QtWidgets.QPushButton('Start protocol')
        self.wdgt_controls.btn_start.clicked.connect(self.startProtocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_start)
        ### Abort protocol button
        self.wdgt_controls.btn_abort = QtWidgets.QPushButton('Abort protocol')
        self.wdgt_controls.btn_abort.clicked.connect(self.abortProtocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_abort)


        ### Spacer
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.wdgt_controls.layout().addItem(vSpacer)

        ### Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(200)
        self._tmr_update.timeout.connect(self.updateGUI)
        self._tmr_update.start()

        ### Once set up: compile file list for first time
        self._compileFileList()

    def _compileFileList(self):
        self._lwdgt_files.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for file in protocols.all():
            self._lwdgt_files.addItem(file)

    def updateFileList(self):
        self.lwdgt_protocols.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for protocol in protocols.read(protocols.open(self._lwdgt_files.currentItem().text())):
            self.lwdgt_protocols.addItem(protocol.__name__)

    def updateGUI(self):

        ### Enable/Disable control elements
        ctrl_is_idle = IPC.inState(Def.State.IDLE, Def.Process.Controller)
        self.wdgt_controls.btn_start.setEnabled(ctrl_is_idle and len(self.lwdgt_protocols.selectedItems()) > 0)
        self.lwdgt_protocols.setEnabled(ctrl_is_idle)
        self._lwdgt_files.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])
        self.wdgt_controls.btn_abort.setEnabled(protocol_is_running)

        ### Update progress
        start_phase = IPC.Control.Protocol[Def.ProtocolCtrl.phase_start]
        if not(start_phase is None):
            self.progress.setEnabled(True)
            phase_diff = time.time() - start_phase
            self.progress.setMaximum(int((IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] - start_phase) * 10))
            if phase_diff > 0.:
                self.progress.setValue(int(phase_diff * 10))

        if not(bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])):
            self.progress.setEnabled(False)


    def startProtocol(self):
        file_name = self._lwdgt_files.currentItem().text()
        protocol_name = self.lwdgt_protocols.currentItem().text()

        IPC.rpc(Def.Process.Controller, Controller.startProtocol,
                      '.'.join([file_name, protocol_name]))

    def abortProtocol(self):
        IPC.rpc(Controller.name, Controller.abortProtocol)

class ProcessMonitor(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Process monitor')
        self._main : Gui.Main = _main

        self._setupUi()

    def _setupUi(self):

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

        self._setProcessState(self._le_controllerState, IPC.getState(Def.Process.Controller))
        self._setProcessState(self._le_cameraState, IPC.getState(Def.Process.Camera))
        self._setProcessState(self._le_displayState, IPC.getState(Def.Process.Display))
        self._setProcessState(self._le_guiState, IPC.getState(Def.Process.GUI))
        self._setProcessState(self._le_ioState, IPC.getState(Def.Process.Io))
        self._setProcessState(self._le_workerState, IPC.getState(Def.Process.Worker))


################################
# Recordings widget

class Recording(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Recordings')
        self._main : Gui.Main = _main
        self.setObjectName('RecGroupBox')

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        ### Create inner widget
        self.setLayout(QtWidgets.QGridLayout())

        ### Basic properties
        self.setCheckable(True)
        self.setFixedWidth(250)

        ### Current folder
        self._le_folder = QtWidgets.QLineEdit()
        self._le_folder.setEnabled(False)
        self.layout().addWidget(QtWidgets.QLabel('Folder'), 0, 0)
        self.layout().addWidget(self._le_folder, 1, 0)

        ### GroupBox
        self.clicked.connect(self.toggleEnable)

        ### Buttons
        ## Start
        self._btn_start = QtWidgets.QPushButton('Start')
        self._btn_start.clicked.connect(lambda: IPC.rpc(Def.Process.Controller, Controller.startRecording))
        self.layout().addWidget(self._btn_start, 2, 0)
        ## Pause
        self._btn_pause = QtWidgets.QPushButton('Pause')
        self._btn_pause.clicked.connect(lambda: IPC.rpc(Def.Process.Controller, Controller.pauseRecording))
        self.layout().addWidget(self._btn_pause, 3, 0)
        ## Stop
        self._btn_stop = QtWidgets.QPushButton('Stop')
        self._btn_stop.clicked.connect(self.finalizeRecording)
        self.layout().addWidget(self._btn_stop, 4, 0)

        ### Show recorded routines
        self._gb_routines = QtWidgets.QGroupBox('Recording routines')
        self._gb_routines.setLayout(QtWidgets.QVBoxLayout())
        for routine_id in Config.Recording[Def.RecCfg.routines]:
            self._gb_routines.layout().addWidget(QtWidgets.QLabel(routine_id))
        self.layout().addWidget(self._gb_routines, 5, 0)
        self.layout().addItem(vSpacer, 6, 0)

        ### Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(200)
        self._tmr_updateGUI.timeout.connect(self.updateGui)
        self._tmr_updateGUI.start()

    def finalizeRecording(self):
        ### First: pause recording
        IPC.rpc(Def.Process.Controller, Controller.pauseRecording)

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
        IPC.rpc(Def.Process.Controller, Controller.stopRecording)

    def toggleEnable(self, newstate):
        IPC.rpc(Def.Process.Controller, Controller.toggleEnableRecording, newstate)

    def updateGui(self):
        """(Periodically) update UI based on shared configuration"""

        enabled = Config.Recording[Def.RecCfg.enabled]
        active = IPC.Control.Recording[Def.RecCtrl.active]
        current_folder = IPC.Control.Recording[Def.RecCtrl.folder]

        if active:
            self.setStyleSheet('QGroupBox#RecGroupBox {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.setStyleSheet('QGroupBox#RecGroupBox {background: rgba(0, 0, 0, 0.0);}')

        ### Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        ### Set current folder
        self._le_folder.setText(IPC.Control.Recording[Def.RecCtrl.folder])

        ### Set buttons dis-/enabled
        ## Start
        self._btn_start.setEnabled(not(active) and enabled)
        self._btn_start.setText('Start' if IPC.inState(Def.State.IDLE, Def.Process.Controller) else 'Resume')
        ## Pause // TODO: implement pause functionality during non-protocol recordings?
        #self._btn_pause.setEnabled(active and enabled)
        self._btn_pause.setEnabled(False)
        ## Stop
        self._btn_stop.setEnabled(bool(IPC.Control.Recording[Def.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(IPC.Control.Protocol[Def.ProtocolCtrl.name]):
            self._btn_stop.setEnabled(False)

class Log(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Log')
        self._main : Gui.Main = _main

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
                if record.levelno > 10:
                    line = '{} : {:10} : {:10} : {}'\
                        .format(record.asctime, record.name, record.levelname, record.msg)
                    self._txe_log.append(line)

                self.logccount += 1

class Controls(QtWidgets.QTabWidget):

    def __init__(self, _main):
        QtWidgets.QTabWidget.__init__(self)
        self._main : Gui.Main = _main

        ### Display Settings
        if Config.Display[Def.DisplayCfg.use]:
            if Config.Display[Def.DisplayCfg.type] == 'spherical':
                self.tabWdgt_Display = gui.Controls.SphericalDisplaySettings(self)
            elif Config.Display[Def.DisplayCfg.type] == 'planar':
                self.tabWdgt_Display = gui.Controls.PlanarDisplaySettings(self)
            else:
                raise Exception('No valid display settings widget found for display type "{}"'
                                .format(Config.Display[Def.DisplayCfg.type]))

            self.addPaddedTab(self.tabWdgt_Display, 'Display')

        ### Protocols
        #self.tabWdgt_Protocols = gui.Controls.Protocol(self)
        #self.addPaddedTab(self.tabWdgt_Protocols, 'Protocols')

        ### Camera
        self.tabWdgt_Camera = gui.Controls.Camera(self)
        self.addPaddedTab(self.tabWdgt_Camera, 'Camera')

    def addPaddedTab(self, wdgt, name):
        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(QtWidgets.QGridLayout())
        wrapper.layout().addWidget(wdgt, 0, 0)
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        hSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        wrapper.layout().addItem(vSpacer, 1, 0)
        #wrapper.layout().addItem(hSpacer, 0, 1)
        self.addTab(wrapper, name)

class Camera(QtWidgets.QTabWidget):

    def __init__(self, _main):
        self.main = _main
        QtWidgets.QTabWidget.__init__(self)

        self.streamFps = 10

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QVBoxLayout())

        ### Add camera addons
        if len(Config.Gui[Def.GuiCfg.addons]) == 0:
            addons = ['LiveCamera']
        else:
            addons = Config.Gui[Def.GuiCfg.addons]

        for addon_name in addons:
            if not(bool(addon_name)):
                continue

            wdgt = getattr(gui.Camera, addon_name)(self)
            if not(wdgt.moduleIsActive):
                Logging.write(logging.WARNING, 'Addon {} could not be activated'
                              .format(addon_name))
                continue
            self.addTab(wdgt, addon_name)

        ### Set frame update timer
        self.imTimer = QtCore.QTimer()
        self.imTimer.setInterval(1000 // self.streamFps)
        self.imTimer.timeout.connect(self.updateFrames)
        self.imTimer.start()

    def updateFrames(self):
        for idx in range(self.count()):
            self.widget(idx).updateFrame()

class DisplayView(QtWidgets.QGroupBox):

    def __init__(self, _main):
        self.main = _main
        QtWidgets.QGroupBox.__init__(self, 'Display View')
        self.setCheckable(True)
        self.toggled.connect(self.setTimer)

        self.setLayout(QtWidgets.QVBoxLayout())
        from glumpy import app
        app.use('qt5')

        self._glWindow = QtWidgets.QOpenGLWidget(self) # app.Window()#
        #self.native_win = self._glWindow._native_window
        self.layout().addWidget(self._glWindow)


        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateGl)

        self.current_protocol = None
        self.current_phase_id = None
        self.current_visual = None

        self.setChecked(True)

    def setTimer(self, bool):
        if bool and not(self.timer.isActive()):
            return
            self.timer.start(1/20)
        else:
            if self.timer.isActive():
                self.timer.stop()

    def updateGl(self):
        if self.current_protocol is None:

            if IPC.Control.Protocol[Def.ProtocolCtrl.name] is None or not(IPC.Control.Protocol[Def.ProtocolCtrl.name]):
                return

            print('SET protocol to {}'.format(IPC.Control.Protocol[Def.ProtocolCtrl.name]))

            self.current_protocol = protocols.load(IPC.Control.Protocol[Def.ProtocolCtrl.name])(self)
            return

        if self.current_phase_id != IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]:
            self.current_phase_id = IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]

            new_phase = self.current_protocol._phases[self.current_phase_id]
            new_visual, kwargs, duration = new_phase['visuals'][0]
            self.current_visual = new_visual(self.current_protocol, self, **kwargs)

        if self.current_visual is None:
            return

        print('draw?')
        self.current_visual.triggerOnDraw(0, 0.0)