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

import Def
import Config
import Process
import IPC
import Logging
import gui.Controls
import gui.Integrated
import gui.CameraAddons

import process.Camera
import process.Display
import process.Logger

class Main(QtWidgets.QMainWindow, Process.AbstractProcess):
    name = Def.Process.GUI

    _app : QtWidgets.QApplication

    def __init__(self, _app=QtWidgets.QApplication(sys.argv), **kwargs):
        ### Create application
        self._app = _app

        ### Set up superclasses
        Process.AbstractProcess.__init__(self, **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        ### Set icon
        self.setWindowIcon(QtGui.QIcon('MappApp.ico'))

        ### Setup basic UI
        self._setupUI()

        ### Setup addons
        #self._setupAddons()

        ### Run event loop
        self.run()

    def run(self):
        #Logging.write(logging.INFO, 'RUN GUI')
        IPC.setState(Def.State.IDLE)
        ### Set timer for handling of communication
        self._tmr_handlePipe = QtCore.QTimer()
        self._tmr_handlePipe.timeout.connect(self._handleInbox)
        self._tmr_handlePipe.start(10)

        ### Run QApplication event loop
        self._app.exec_()

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
        hvSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        #hSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        #self.hSplitter = QtWidgets.QSplitter()

        ### Add integrated addons
        ## Add controls
        self._grp_controls = gui.Integrated.Controls(self)
        self.centralWidget().layout().addWidget(self._grp_controls, 0, 0, 2, 2)

        ## Add camera
        self._grp_camera = gui.Integrated.Camera(self)
        self.centralWidget().layout().addWidget(self._grp_camera, 0, 2)

        ## Add topright
        self._grp_topright = QtWidgets.QWidget()
        self._grp_topright.setLayout(QtWidgets.QHBoxLayout())
        self._grp_topright.layout().addItem(hvSpacer)
        self.centralWidget().layout().addWidget(self._grp_topright, 0, 3)

        ## Add IO monitor
        self._grp_io = QtWidgets.QWidget()
        self._grp_io.setLayout(QtWidgets.QHBoxLayout())
        self._grp_io.layout().addItem(hvSpacer)
        self.centralWidget().layout().addWidget(self._grp_io, 1, 3, 1, 2)

        ## Process monitor
        self._grp_processStatus = gui.Integrated.ProcessMonitor(self)
        self._grp_processStatus.setMaximumHeight(300)
        self.centralWidget().layout().addWidget(self._grp_processStatus, 2, 0)

        ## Recordings
        self._grp_recordings = gui.Integrated.Recording(self)
        self._grp_recordings.setMaximumHeight(300)
        self.centralWidget().layout().addWidget(self._grp_recordings, 2, 1)

        ## Logger
        self._grp_log = gui.Integrated.Log(self)
        self._grp_log.setMaximumHeight(300)
        self.centralWidget().layout().addWidget(self._grp_log, 2, 2, 1, 2)

        ### Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        ## Menu windows
        self._menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self._menu_windows)
        ## Menu processes
        self._menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self._menu_process)
        self.menuBar().addMenu(self._menu_windows)
        # Restart display
        self._menu_process_redisp = QtWidgets.QAction('Restart display')
        self._menu_process_redisp.triggered.connect(
            lambda: IPC.rpc(Def.Process.Controller, Process.Controller.initializeProcess, process.Display))
        self._menu_process.addAction(self._menu_process_redisp)
        # Restart camera
        self._menu_process_recam = QtWidgets.QAction('Restart camera')
        self._menu_process_recam.triggered.connect(
            lambda: IPC.rpc(Def.Process.Controller, Process.Controller.initializeProcess, process.Camera))
        self._menu_process.addAction(self._menu_process_recam)
        # Restart IO
        self._menu_process_relog = QtWidgets.QAction('Restart logger')
        self._menu_process_relog.triggered.connect(
            lambda: IPC.rpc(Def.Process.Controller, Process.Controller.initializeProcess, process.Logger))
        self._menu_process.addAction(self._menu_process_relog)

        # Bind shortcuts
        self._bindShortcuts()

        self.showMaximized()

    def _bindShortcuts(self):

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

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        ### Inform controller of close event
        IPC.send(Def.Process.Controller, Def.Signal.Shutdown)

        # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
        IPC.setState(Def.State.STOPPED)
