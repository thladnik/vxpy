"""
MappApp ./Startup.py - Startup script is used for creation and
modification of program configuration files.
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

from configparser import ConfigParser
import os
import sys
from typing import Union

from PyQt5 import QtCore, QtWidgets

import Def
from helper import Basic

from devices.Camera import GetCamera

class StartupConfiguration(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self.configuration = Basic.Config()
        self._configfile = None
        self._currentConfigChanged = False

        self._setupUI()

    def _setupUI(self):

        ## Setup window
        self.setFixedSize(1000, 800)

        ## Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        ## Set file selection
        self.centralWidget().layout().addWidget(QtWidgets.QLabel('Select configuration file: '), 0, 0)
        self._cb_selectConfigfile = QtWidgets.QComboBox()
        self._cb_selectConfigfile.currentTextChanged.connect(self._openConfigfile)
        self.centralWidget().layout().addWidget(self._cb_selectConfigfile, 0, 1)
        self._pb_addConfigfile = QtWidgets.QPushButton('Add new configs file...')
        self._pb_addConfigfile.clicked.connect(self._addConfigfile)
        self.centralWidget().layout().addWidget(self._pb_addConfigfile, 0, 2)

        ## Set configs widget
        self._tabwdgt_config = QtWidgets.QTabWidget(self)
        self._tabwdgt_config.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self._tabwdgt_config, 1, 0, 1, 5)
        # Camera configuration
        self._wdgt_camera = CameraWidget(self)
        self._tabwdgt_config.addTab(self._wdgt_camera, 'Camera')
        # Next
        self._tabwdgt_config.addTab(QtWidgets.QWidget(self._tabwdgt_config), 'Hello2')

        self._pb_saveConfig = QtWidgets.QPushButton('Save changes')
        self._pb_saveConfig.clicked.connect(self.configuration.saveToFile)
        self.centralWidget().layout().addWidget(self._pb_saveConfig, 2, 3)

        self._pb_startApp = QtWidgets.QPushButton('Save and start')
        self._pb_startApp.clicked.connect(self._startApplication)
        self.centralWidget().layout().addWidget(self._pb_startApp, 2, 4)

        # Update and show
        self._updateConfigfileList()
        self.show()

    def _updateConfigfileList(self):
        self._cb_selectConfigfile.clear()
        for fname in os.listdir(Def.Path.Config):
            self._cb_selectConfigfile.addItem(fname[:-4])

    def _addConfigfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(Def.Path.Config):
                with open(os.path.join(Def.Path.Config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self._updateConfigfileList()
            self._cb_selectConfigfile.setCurrentText(name)


    def _openConfigfile(self):

        name = self._cb_selectConfigfile.currentText()
        if name == '':
            return

        self._configfile = '%s.ini' % name
        self.configuration = Basic.Config(self._configfile)


    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                self.configuration.saveToFile()

        event.accept()


    def _startApplication(self):
        self.configuration.saveToFile()
        global configfile
        _configfile = self._configfile
        self.close()

from devices import Camera
class CameraWidget(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Enabled')

        self.setCheckable(True)
        self.setLayout(QtWidgets.QHBoxLayout())

        self._vbox_cameras = QtWidgets.QWidget()
        self._vbox_cameras.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self._vbox_cameras)

        self._listw_cameras = QtWidgets.QListWidget()
        self._vbox_cameras.layout().addWidget(QtWidgets.QLabel('Camera types'))
        self._vbox_cameras.layout().addWidget(self._listw_cameras)
        for name in Camera.__dict__:
            if name.startswith('CAM_'):
                self._listw_cameras.addItem(name)


################################
# Recordings widget (SALVAGED FROM GUI INTEGRATED)

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
        self._btn_start.clicked.connect(lambda: IPC.rpc(Def.Process.Controller, Controller.startRecording))
        self.wdgt.layout().addWidget(self._btn_start, 1, 0)
        ## Pause
        self._btn_pause = QtWidgets.QPushButton('Pause')
        self._btn_pause.clicked.connect(lambda: IPC.rpc(Def.Process.Controller, Controller.pauseRecording))
        self.wdgt.layout().addWidget(self._btn_pause, 1, 1)
        ## Stop
        self._btn_stop = QtWidgets.QPushButton('Stop')
        self._btn_stop.clicked.connect(self.finalizeRecording)
        self.wdgt.layout().addWidget(self._btn_stop, 1, 2)

        ### Add routines
        self._cb_buffers = dict()
        ## Camera routines
        self._grp_cameraBuffers = QtWidgets.QGroupBox('Camera routines')
        self._grp_cameraBuffers.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt.layout().addWidget(self._grp_cameraBuffers, 2, 0, 1, 3)
        for bufferName in Config.Camera[Def.CameraCfg.routines]:
            bufferId = '{}/{}'.format(Def.Process.Camera, bufferName)
            self._cb_buffers[bufferId] = QtWidgets.QCheckBox(bufferId)
            self._cb_buffers[bufferId].clicked.connect(self.bufferStateChanged)
            self._cb_buffers[bufferId].setTristate(False)
            self._grp_cameraBuffers.layout().addWidget(self._cb_buffers[bufferId])
        ## IO routines
        self._grp_ioBuffers = QtWidgets.QGroupBox('I/O routines')
        self._grp_ioBuffers.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt.layout().addWidget(self._grp_ioBuffers, 3, 0, 1, 3)
        for bufferName in Config.IO[Def.IoCfg.routines]:
            bufferId = '{}/{}'.format(Def.Process.Io, bufferName)
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

    def bufferStateChanged(self):
        """Update shared buffer list for recordings based on UI selection.
        Because buffer list is shared (managed) list, appending and removing has to be done in weird way (below)"""

        for bufferId, cb in self._cb_buffers.items():
            # Add bufferId if checkstate == True and bufferId not in buffer list
            if Conversion.QtCheckstateToBool(cb.checkState()) and bufferId not in Config.Recording[Def.RecCfg.routines]:
                Config.Recording[Def.RecCfg.routines] = Config.Recording[Def.RecCfg.routines] + [bufferId]
            # Remove bufferId if checkstate == False and bufferId is in buffer list
            elif not(Conversion.QtCheckstateToBool(cb.checkState())) and bufferId in Config.Recording[Def.RecCfg.routines]:
                Config.Recording[Def.RecCfg.routines] = [bi for bi in Config.Recording[Def.RecCfg.routines] if bi != bufferId]

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
        self._btn_start.setText('Start' if IPC.inState(Def.State.IDLE, Def.Process.Controller) else 'Resume')
        #self._btn_pause.setEnabled(active and enabled)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(bool(IPC.Control.Recording[Def.RecCtrl.folder]) and enabled)

        ### Set buffer check states
        for bufferId, cb in self._cb_buffers.items():
            cb.setCheckState(Conversion.boolToQtCheckstate(bufferId in Config.Recording[Def.RecCfg.routines]))

        ### Enable/disable buffer groups during active recording
        self._grp_cameraBuffers.setDisabled(active or not(enabled))
        self._grp_ioBuffers.setDisabled(active or not(enabled))



if __name__ == '__main__':

    import process.Controller

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--ini', action='store', dest='ini_file', type=str)
    parser.add_argument('--skip_setup', action='store_true', dest='skip_setup', default=False)
    args = parser.parse_args(sys.argv[1:])

    if args.skip_setup:
        # process.Controller.configfile = 'default.ini'
        process.Controller.configfile = 'omr_behavior.ini'

    if not(args.ini_file is None):
        process.Controller.configfile = args.ini_file
        args.skip_setup = True

    if args.skip_setup:
        ctrl = process.Controller()

    else:

        configfile = None
        app = QtWidgets.QApplication([])
        window = StartupConfiguration()
        app.exec_()

        if configfile is None:
            exit()

        import process.Controller
        process.Controller()


