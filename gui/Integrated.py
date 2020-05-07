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
import gui.Controls
import gui.Camera
import IPC
import Logging
from process import GUI

if Def.Env == Def.EnvTypes.Dev:
    pass

class ProcessMonitor(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Process monitor')
        self._main : GUI.Main = _main

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

        ## Logger process status
        self._le_loggerState = QtWidgets.QLineEdit('')
        self._le_loggerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Logger), 5, 0)
        self.layout().addWidget(self._le_loggerState, 5, 1)

        ## Worker process status
        self._le_workerState = QtWidgets.QLineEdit('')
        self._le_workerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Worker), 6, 0)
        self.layout().addWidget(self._le_workerState, 6, 1)

        self.layout().addItem(vSpacer, 7, 0)


        ## Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._updateStates)
        self._tmr_updateGUI.start()

    def _getProcessStateStr(self, code):
        if code == Def.State.STOPPED:
            return 'Stopped'
        elif code == Def.State.READY:
            return 'Ready'
        elif code == Def.State.IDLE:
            return 'Idle'
        elif code ==Def.State.RUNNING:
            return 'Running'
        elif code == Def.State.STARTING:
            return 'Starting'
        else:
            return 'N/A'

    def _setProcessState(self, le: QtWidgets.QLineEdit, code):
        ### Set text
        le.setText(self._getProcessStateStr(code))

        ### Set style
        if code == Def.State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif code == Def.State.STARTING:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.STOPPED:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        else:
            le.setStyleSheet('color: #FF0000')

    def _updateStates(self):
        """This method sets the process state according to the current global state variables.
        Additionally it modifies 
        """

        self._setProcessState(self._le_controllerState, IPC.getState(Def.Process.Controller))
        self._setProcessState(self._le_cameraState, IPC.getState(Def.Process.Camera))
        self._setProcessState(self._le_displayState, IPC.getState(Def.Process.Display))
        self._setProcessState(self._le_guiState, IPC.getState(Def.Process.GUI))
        self._setProcessState(self._le_ioState, IPC.getState(Def.Process.Io))
        self._setProcessState(self._le_loggerState, IPC.getState(Def.Process.Logger))
        self._setProcessState(self._le_workerState, IPC.getState(Def.Process.Worker))


################################
# Recordings widget

class Recording(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Recordings')
        self._main : GUI.Main = _main
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
        self._main : GUI.Main = _main

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
        self._main : GUI.Main = _main

        ## Display Settings
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
        self.tabWdgt_Protocols = gui.Controls.Protocol(self)
        self.addPaddedTab(self.tabWdgt_Protocols, 'Protocols')

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
        wrapper.layout().addItem(hSpacer, 0, 1)
        self.addTab(wrapper, name)

class Camera(QtWidgets.QTabWidget):

    def __init__(self, _main):
        self.main = _main
        QtWidgets.QTabWidget.__init__(self)

        self.streamFps = 30

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QVBoxLayout())
        #self.setFixedSize(800, 600)

        ### Use default PlotWidget
        #self._wdgt_plot = Camera.CameraWidget(parent=self)
        #self._wdgt_plot.setFixedSize(self.size())
        #self.addTab(self._wdgt_plot, 'Live camera')

        ### Add camera addons
        for addonName in ['LiveCamera', *Config.Gui[Def.GuiCfg.addons]]:
        #for addonName in Config.Gui[Def.GuiCfg.addons]:
            if not(bool(addonName)):
                continue

            wdgt = getattr(gui.Camera, addonName)(self)
            if not(wdgt.moduleIsActive):
                Logging.write(logging.WARNING, 'Addon {} could not be activated'
                              .format(addonName))
                continue
            self.addTab(wdgt, addonName)

        ### Set frame update timer
        self.imTimer = QtCore.QTimer()
        self.imTimer.setInterval(1000 // self.streamFps)
        self.imTimer.timeout.connect(self.updateFrames)
        self.imTimer.start()

    def updateFrames(self):
        for idx in range(self.count()):
            self.widget(idx).updateFrame()
