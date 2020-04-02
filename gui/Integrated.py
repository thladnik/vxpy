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
from time import strftime

import Config
import Controller
import Def
from helper.Basic import Conversion
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

        self.setMaximumWidth(6 * 130)

        ## Setup widget
        self.setWindowTitle('Process monitor')
        self.setLayout(QtWidgets.QGridLayout())
        self.setMinimumSize(QtCore.QSize(0,0))
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        ## Controller process status
        self._le_controllerState = QtWidgets.QLineEdit('')
        self._le_controllerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Controller), 0, 0)
        self.layout().addWidget(self._le_controllerState, 1, 0)

        ## Camera process status
        self._le_cameraState = QtWidgets.QLineEdit('')
        self._le_cameraState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Camera), 0, 1)
        self.layout().addWidget(self._le_cameraState, 1, 1)

        ## Display process status
        self._le_displayState = QtWidgets.QLineEdit('')
        self._le_displayState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Display), 0, 2)
        self.layout().addWidget(self._le_displayState, 1, 2)

        ## Gui process status
        self._le_guiState = QtWidgets.QLineEdit('')
        self._le_guiState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.GUI), 0, 3)
        self.layout().addWidget(self._le_guiState, 1, 3)

        ## IO process status
        self._le_ioState = QtWidgets.QLineEdit('')
        self._le_ioState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.IO), 0, 4)
        self.layout().addWidget(self._le_ioState, 1, 4)

        ## Logger process status
        self._le_loggerState = QtWidgets.QLineEdit('')
        self._le_loggerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Logger), 0, 5)
        self.layout().addWidget(self._le_loggerState, 1, 5)

        ## Worker process status
        self._le_workerState = QtWidgets.QLineEdit('')
        self._le_workerState.setDisabled(True)
        self.layout().addWidget(QtWidgets.QLabel(Def.Process.Worker), 0, 6)
        self.layout().addWidget(self._le_workerState, 1, 6)

        ## Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._updateStates)
        self._tmr_updateGUI.start()

    def _getProcessStateStr(self, code):
        if code == self._main.State.stopped:
            return 'Stopped'
        elif code == self._main.State.READY:
            return 'Ready'
        elif code == self._main.State.IDLE:
            return 'Idle'
        elif code == self._main.State.RUNNING:
            return 'Running'
        elif code == self._main.State.starting:
            return 'Starting'
        else:
            return 'N/A'

    def _setProcessState(self, le: QtWidgets.QLineEdit, code):
        ### Set text
        le.setText(self._getProcessStateStr(code))

        ### Set style
        if code == self._main.State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif code == self._main.State.starting:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == self._main.State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == self._main.State.stopped:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        else:
            le.setStyleSheet('color: #FF0000')

    def _updateStates(self):
        """This method sets the process state according to the current global state variables.
        Additionally it modifies 
        """

        self._setProcessState(self._le_controllerState, self._main.getState(Def.Process.Controller))
        self._setProcessState(self._le_cameraState, self._main.getState(Def.Process.Camera))
        self._setProcessState(self._le_displayState, self._main.getState(Def.Process.Display))
        self._setProcessState(self._le_guiState, self._main.getState(Def.Process.GUI))
        self._setProcessState(self._le_ioState, self._main.getState(Def.Process.IO))
        self._setProcessState(self._le_loggerState, self._main.getState(Def.Process.Logger))
        self._setProcessState(self._le_workerState, self._main.getState(Def.Process.Worker))


################################
# Recordings widget

class Recording(QtWidgets.QGroupBox):

    def __init__(self, _main):
        QtWidgets.QGroupBox.__init__(self, 'Recordings')
        self._main : GUI.Main = _main

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.setLayout(QtWidgets.QHBoxLayout())
        ### Create inner widget
        self.wdgt = QtWidgets.QWidget(self)
        self.wdgt.setObjectName('InGroupBox')
        self.wdgt.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.wdgt)

        ### Basic properties
        self.setCheckable(True)

        ### Current folder
        self._le_folder = QtWidgets.QLineEdit()
        self._le_folder.setEnabled(False)
        self.wdgt.layout().addWidget(QtWidgets.QLabel('Folder'), 0, 0)
        self.wdgt.layout().addWidget(self._le_folder, 0, 1, 1, 2)

        ### GroupBox
        self.clicked.connect(self.toggleEnable)

        ### Buttons
        ## Start
        self._btn_start = QtWidgets.QPushButton('Start')
        self._btn_start.clicked.connect(lambda: self._main.rpc(Def.Process.Controller, Controller.Controller.startRecording))
        self.wdgt.layout().addWidget(self._btn_start, 1, 0)
        ## Pause
        self._btn_pause = QtWidgets.QPushButton('Pause')
        self._btn_pause.clicked.connect(lambda: self._main.rpc(Def.Process.Controller, Controller.Controller.pauseRecording))
        self.wdgt.layout().addWidget(self._btn_pause, 1, 1)
        ## Stop
        self._btn_stop = QtWidgets.QPushButton('Stop')
        self._btn_stop.clicked.connect(self.finalizeRecording)
        self.wdgt.layout().addWidget(self._btn_stop, 1, 2)

        ### Add buffers
        self._cb_buffers = dict()
        ## Camera buffers
        self._grp_cameraBuffers = QtWidgets.QGroupBox('Camera buffers')
        self._grp_cameraBuffers.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt.layout().addWidget(self._grp_cameraBuffers, 2, 0, 1, 3)
        for bufferName in Config.Camera[Def.CameraCfg.buffers]:
            bufferId = '{}/{}'.format(Def.Process.Camera, bufferName)
            self._cb_buffers[bufferId] = QtWidgets.QCheckBox(bufferId)
            self._cb_buffers[bufferId].clicked.connect(self.bufferStateChanged)
            self._cb_buffers[bufferId].setTristate(False)
            self._grp_cameraBuffers.layout().addWidget(self._cb_buffers[bufferId])
        ## IO buffers
        self._grp_ioBuffers = QtWidgets.QGroupBox('I/O buffers')
        self._grp_ioBuffers.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt.layout().addWidget(self._grp_ioBuffers, 3, 0, 1, 3)
        for bufferName in Config.IO[Def.IoCfg.buffers]:
            bufferId = '{}/{}'.format(Def.Process.IO, bufferName)
            self._cb_buffers[bufferId] = QtWidgets.QCheckBox(bufferId)
            self._cb_buffers[bufferId].clicked.connect(self.bufferStateChanged)
            self._cb_buffers[bufferId].setTristate(False)
            self._grp_ioBuffers.layout().addWidget(self._cb_buffers[bufferId])

        self.wdgt.layout().addItem(vSpacer, 4, 0)

        ### Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self.updateGui)
        self._tmr_updateGUI.start()

    def finalizeRecording(self):
        ### First: pause recording
        self._main.rpc(Def.Process.Controller, Controller.Controller.pauseRecording)

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
        self._main.rpc(Def.Process.Controller, Controller.Controller.stopRecording)

    def toggleEnable(self, newstate):
        self._main.rpc(Def.Process.Controller, Controller.Controller.toggleEnableRecording, newstate)

    def bufferStateChanged(self):
        """Update shared buffer list for recordings based on UI selection.
        Because buffer list is shared (managed) list, appending and removing has to be done in weird way (below)"""

        for bufferId, cb in self._cb_buffers.items():
            # Add bufferId if checkstate == True and bufferId not in buffer list
            if Conversion.QtCheckstateToBool(cb.checkState()) and bufferId not in Config.Recording[Def.RecCfg.buffers]:
                Config.Recording[Def.RecCfg.buffers] = Config.Recording[Def.RecCfg.buffers] + [bufferId]
            # Remove bufferId if checkstate == False and bufferId is in buffer list
            elif not(Conversion.QtCheckstateToBool(cb.checkState())) and bufferId in Config.Recording[Def.RecCfg.buffers]:
                Config.Recording[Def.RecCfg.buffers] = [bi for bi in Config.Recording[Def.RecCfg.buffers] if bi != bufferId]

    def updateGui(self):
        """(Periodically) update UI based on shared configuration"""

        enabled = Config.Recording[Def.RecCfg.enabled]
        active = IPC.Control.Recording[Def.RecCtrl.active]
        current_folder = IPC.Control.Recording[Def.RecCtrl.folder]


        if active:
            self.wdgt.setStyleSheet('QWidget#InGroupBox {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.wdgt.setStyleSheet('QWidget#InGroupBox {background: rgba(0, 0, 0, 0.0);}')

        ### Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        ### Set current folder
        self._le_folder.setText(IPC.Control.Recording[Def.RecCtrl.folder])

        ### Set buttons dis-/enabled
        self._btn_start.setEnabled(not(active) and enabled)
        self._btn_start.setText('Start' if self._main.inState(self._main.State.IDLE, Def.Process.Controller) else 'Resume')
        #self._btn_pause.setEnabled(active and enabled)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(bool(IPC.Control.Recording[Def.RecCtrl.folder]) and enabled)

        ### Set buffer check states
        for bufferId, cb in self._cb_buffers.items():
            cb.setCheckState(Conversion.boolToQtCheckstate(bufferId in Config.Recording[Def.RecCfg.buffers]))

        ### Enable/disable buffer groups during active recording
        self._grp_cameraBuffers.setDisabled(active or not(enabled))
        self._grp_ioBuffers.setDisabled(active or not(enabled))

