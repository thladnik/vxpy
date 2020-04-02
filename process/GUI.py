"""
MappApp .process/GUI.py - Graphical user interface for easier UX.
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
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from time import strftime, sleep

import Def
import Buffer
import Config
import Controller
import IPC
import Logging
import gui.DisplaySettings
import gui.ProtocolControl
import gui.Integrated
import gui.CameraStream
import gui.addons

import process.Camera
import process.Display
import process.Logger

class Main(QtWidgets.QMainWindow, Controller.BaseProcess):
    name = Def.Process.GUI

    _app         : QtWidgets.QApplication

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, _app=QtWidgets.QApplication(sys.argv), **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        ### Set icon
        self.setWindowIcon(QtGui.QIcon('MappApp.ico'))

        ### Setup basic UI
        self._setupUI()

        ### Setup addons
        self._setupAddons()

        ### Set initial log line count
        self.logccount = 0

        ### Run event loop
        self.run()

    def run(self):
        IPC.State.Gui.value = self.State.IDLE
        ### Set timer for handling of communication
        self._tmr_handlePipe = QtCore.QTimer()
        self._tmr_handlePipe.timeout.connect(self._handleInbox)
        self._tmr_handlePipe.start(10)

        ### Set timer for updating of log
        self._tmr_logger = QtCore.QTimer()
        self._tmr_logger.timeout.connect(self.printLog)
        self._tmr_logger.start(50)

        ### Run QApplication event loop
        self._app.exec_()

    def _setupAddons(self):
        self.addons = dict()
        for addonName in Config.Gui[Def.GuiCfg.addons]:
            if not(bool(addonName)):
                continue

            self.addons[addonName] = getattr(gui.addons, addonName)(self)
            if not(self.addons[addonName].moduleIsActive):
                Logging.write(logging.WARNING, 'Addon {} could not be activated'.format(addonName))
                continue
            self.addons[addonName].show()

    def _setupUI(self):

        ### Set up main window
        self.setWindowTitle('MappApp')
        self.move(0, 0)
        self.screenGeo = self._app.primaryScreen().geometry()
        self.resize(self.screenGeo.width()-2, self.screenGeo.height()//3)

        ### Setup central widget
        self._centralwidget = QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget)
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        ### Add spacers
        hSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.centralWidget().layout().addItem(hSpacer, 0, 1)
        self.centralWidget().layout().addItem(hSpacer, 0, 2)

        ### Add integrated addons
        ## Process monitor
        self._grp_processStatus = gui.Integrated.ProcessMonitor(self)
        self.centralWidget().layout().addWidget(self._grp_processStatus, 0, 0)

        ## Recordings
        self._grp_recordings = gui.Integrated.Recording(self)
        self.centralWidget().layout().addWidget(self._grp_recordings, 1, 0)


        ## Logger
        self._grp_log = QtWidgets.QGroupBox()
        self._grp_log.setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().addWidget(self._grp_log, 1, 1, 1, 2)
        self._txe_log = QtWidgets.QTextEdit()
        self._txe_log.setReadOnly(True)
        self._txe_log.setFontFamily('Courier')
        self._txe_log.setFontPointSize(10)
        self._grp_log.layout().addWidget(QtWidgets.QLabel('Log'))
        self._grp_log.layout().addWidget(self._txe_log)

        ### Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        ## Menu windows
        self._menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self._menu_windows)
        # Display settings
        self._menu_act_dispSettings = QtWidgets.QAction('Display settings')
        self._menu_act_dispSettings.triggered.connect(self._openDisplaySettings)
        self._menu_windows.addAction(self._menu_act_dispSettings)
        # Stimulation protocols
        self._menu_act_stimProtocols = QtWidgets.QAction('Stimulation protocols')
        self._menu_act_stimProtocols.triggered.connect(self._openStimProtocols)
        self._menu_windows.addAction(self._menu_act_stimProtocols)
        # Video streamer
        self._menu_act_vidStream = QtWidgets.QAction('Video streamer')
        self._menu_act_vidStream.triggered.connect(self._openVideoStreamer)
        self._menu_windows.addAction(self._menu_act_vidStream)
        ## Menu processes
        self._menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self._menu_process)
        self.menuBar().addMenu(self._menu_windows)
        # Restart display
        self._menu_process_redisp = QtWidgets.QAction('Restart display')
        self._menu_process_redisp.triggered.connect(
            lambda: self.rpc(Def.Process.Controller, Controller.Controller.initializeProcess, process.Display))
        self._menu_process.addAction(self._menu_process_redisp)
        # Restart camera
        self._menu_process_recam = QtWidgets.QAction('Restart camera')
        self._menu_process_recam.triggered.connect(
            lambda: self.rpc(Def.Process.Controller, Controller.Controller.initializeProcess, process.Camera))
        self._menu_process.addAction(self._menu_process_recam)
        # Restart IO
        self._menu_process_relog = QtWidgets.QAction('Restart logger')
        self._menu_process_relog.triggered.connect(
            lambda: self.rpc(Def.Process.Controller, Controller.Controller.initializeProcess, process.Logger))
        self._menu_process.addAction(self._menu_process_relog)

        ## Display Settings
        displayType = Config.Display[Def.DisplayCfg.type]
        if displayType == 'spherical':
            self._wdgt_dispSettings = gui.DisplaySettings.SphericalDisplaySettings(self)
        elif displayType == 'planar':
            self._wdgt_dispSettings = gui.DisplaySettings.PlanarDisplaySettings(self)
        else:
            Exception('No valid GUI found for current display type "{}"'.format(displayType))
        self._openDisplaySettings()

        ## Stimulus Protocols
        self._wdgt_stimProtocols = gui.ProtocolControl.Protocols(self)
        self._openStimProtocols()

        # Video Streamer
        if Config.Camera[Def.CameraCfg.use]:
            self._wdgt_camera = gui.CameraStream.Camera(self, flags=QtCore.Qt.Window)
            self._openVideoStreamer()

        # Bind shortcuts
        self._bindShortcuts()

        self.show()

    def _bindShortcuts(self):
        ### Reset Display settings view
        self._menu_act_dispSettings.setShortcut('Ctrl+s')
        self._menu_act_dispSettings.setAutoRepeat(False)
        ### Reset Stimulation protocols view
        self._menu_act_stimProtocols.setShortcut('Ctrl+p')
        self._menu_act_stimProtocols.setAutoRepeat(False)
        ### Reset Video streamer view
        if Config.Camera[Def.CameraCfg.use]:
            self._menu_act_vidStream.setShortcut('Ctrl+v')
            self._menu_act_vidStream.setAutoRepeat(False)

        ### Restart display process
        self._menu_process_redisp.setShortcut('Ctrl+Alt+Shift+m')
        self._menu_process_redisp.setAutoRepeat(False)
        ### Restart camera process
        if Config.Camera[Def.CameraCfg.use]:
            self._menu_process_recam.setShortcut('Ctrl+Alt+Shift+c')
            self._menu_process_recam.setAutoRepeat(False)
        ### Restart display process
        self._menu_process_relog.setShortcut('Ctrl+Alt+Shift+l')
        self._menu_process_relog.setAutoRepeat(False)

    def printLog(self):
        if IPC.Buffer.Logfile is None:
            return

        with open(os.path.join(Def.Path.Log, IPC.Buffer.Logfile.value), 'r') as fobj:
            lines = fobj.read().split('<<\n')
            for line in lines[self.logccount:]:
                if len(line) == 0:
                    continue
                record = line.split(' <<>> ')
                if record[2].find('INFO') > -1 or record[2].find('WARN') > -1 or record[2].find('EXE') > -1 :
                    line = '{} :: {:10} :: {:8} :: {}'\
                        .format(record[0], record[1].replace(' ', ''), record[2].replace(' ', ''), record[3])

                    self._txe_log.append(line)
                self.logccount += 1

    def _openDisplaySettings(self):
        self._wdgt_dispSettings.showNormal()
        self._wdgt_dispSettings.move(0, self.screenGeo.height()//3+50)
        self._wdgt_dispSettings.show()

    def _openStimProtocols(self):
        self._wdgt_stimProtocols.showNormal()
        self._wdgt_stimProtocols.move(400, self.screenGeo.height()//3+50)
        self._wdgt_stimProtocols.show()

    def _openVideoStreamer(self):
        if not(Config.Camera[Def.CameraCfg.use]):
            return

        self._wdgt_camera.showNormal()
        self._wdgt_camera.move(800, self.screenGeo.height()//3+50)
        self._wdgt_camera.show()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        ### Inform controller of close event
        self.send(Def.Process.Controller, Controller.BaseProcess.Signal.Shutdown)

        # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
        self.setState(self.State.stopped)

        ### Close child widgets
        self._wdgt_dispSettings.close()
        self._wdgt_stimProtocols.close()
        if Config.Camera[Def.CameraCfg.use]:
            self._wdgt_camera.close()