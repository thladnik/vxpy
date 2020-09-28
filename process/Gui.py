"""
MappApp .process/Gui.py - Graphical user interface for easier UX.
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
import gui.Camera
import gui.Integrated
import gui.Io

import process.Controller
import process.Camera
import process.Display

class Gui(QtWidgets.QMainWindow, Process.AbstractProcess):
    name = Def.Process.GUI

    app : QtWidgets.QApplication

    def __init__(self, _app=QtWidgets.QApplication(sys.argv), **kwargs):
        ### Create application
        self.app = _app

        ### Set up parents
        Process.AbstractProcess.__init__(self, **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        ### Set icon
        self.setWindowIcon(QtGui.QIcon('MappApp.ico'))

        ### Setup basic UI
        self.setup_ui()

        ### Run event loop
        self.run(interval=0.005)

    def main(self):
        self.app.processEvents()

    def setup_ui(self):

        ### Set up main window
        self.setWindowTitle('MappApp')
        self.move(0, 0)
        self.screenGeo = self.app.primaryScreen().geometry()
        w, h = self.screenGeo.width(), self.screenGeo.height()
        if w > 1920 and h > 1080:
            self.resize(1920, 1080)
        else:
            self.resize(w,h)

        ### Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        ### Add spacers
        hvSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        #hSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        ## Protocols
        self.protocols = gui.Integrated.Protocols(self)
        self.centralWidget().layout().addWidget(self.protocols, 0, 0, 1, 3)

        ## Camera
        self.camera = gui.Integrated.Camera(self)
        self.camera.setMinimumWidth(int(Config.Camera[Def.CameraCfg.res_x][0] * 1.0))
        self.camera.setMaximumWidth(int(Config.Camera[Def.CameraCfg.res_x][0] * 2.0))
        self.centralWidget().layout().addWidget(self.camera, 0, 3, 2, 1)

        ## Add Plotter
        self.plotter = gui.Io.IoWidget(self)
        self.centralWidget().layout().addWidget(self.plotter, 1, 0, 1, 3)

        ## Process monitor
        self.process_monitor = gui.Integrated.ProcessMonitor(self)
        self.process_monitor.setMaximumHeight(500)
        self.centralWidget().layout().addWidget(self.process_monitor, 2, 0)

        ## Recordings
        self.recordings = gui.Integrated.Recording(self)
        self.recordings.setMaximumHeight(500)
        self.centralWidget().layout().addWidget(self.recordings, 2, 1)

        ## Logger
        self.log_display = gui.Integrated.Log(self)
        self.log_display.setMaximumHeight(500)
        self.centralWidget().layout().addWidget(self.log_display, 2, 2, 1, 2)

        ### Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        ## Menu windows
        self.menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self.menu_windows)
        ## Menu processes
        self.menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self.menu_process)
        self.menuBar().addMenu(self.menu_windows)
        # Restart camera
        self.menu_process.restart_camera = QtWidgets.QAction('Restart camera')
        self.menu_process.restart_camera.triggered.connect(self.restart_camera)
        self.menu_process.addAction(self.menu_process.restart_camera)
        # Restart display
        self.menu_process.restart_display = QtWidgets.QAction('Restart display')
        self.menu_process.restart_display.triggered.connect(self.restart_display)
        self.menu_process.addAction(self.menu_process.restart_display)

        # Bind shortcuts
        self._bindShortcuts()

        self.show()

    def restart_camera(self):
        IPC.rpc(Def.Process.Controller,
                process.Controller.initialize_process,
                process.Camera)

    def restart_display(self):
        IPC.rpc(Def.Process.Controller,
                process.Controller.initialize_process,
                process.Display)

    def _bindShortcuts(self):

        ### Restart display process
        self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
        self.menu_process.restart_display.setAutoRepeat(False)
        ### Restart camera process
        if Config.Camera[Def.CameraCfg.use]:
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        ### Inform controller of close event
        IPC.send(Def.Process.Controller, Def.Signal.Shutdown)

        # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
        IPC.set_state(Def.State.STOPPED)
