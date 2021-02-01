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

from PyQt5 import QtCore, QtGui, QtWidgets
import sys

import Def
import Config
import process
import IPC
import gui.Camera
import gui.Integrated
import gui.Io


class Gui(QtWidgets.QMainWindow, process.AbstractProcess):
    name = Def.Process.GUI

    app : QtWidgets.QApplication

    def __init__(self, _app=QtWidgets.QApplication(sys.argv), **kwargs):
        # Create application
        self.app = _app

        # Set up parents
        process.AbstractProcess.__init__(self, **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        # Set icon
        self.setWindowIcon(QtGui.QIcon('MappApp.ico'))

        # Setup basic UI
        self.setup_ui()

        # Run event loop
        self.run(interval=0.005)

    def main(self):
        self.app.processEvents()

    def setup_ui(self):

        # Set up main window
        self.setWindowTitle('MappApp')
        self.move(0, 0)
        self.screenGeo = self.app.primaryScreen().geometry()
        w, h = self.screenGeo.width(), self.screenGeo.height()
        print(w,h)
        if w > 1920 and h > 1080:
            print('YAY?')
            self.resize(1920, 1080)
        else:
            self.resize(1800, 1000)
            print('NO?')
            #self.showMaximized()
        self.show()

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        # Protocols
        self.protocols = gui.Integrated.Protocols(self)
        self.centralWidget().layout().addWidget(self.protocols, 0, 0, 1, 3)

        # Camera
        self.camera = gui.Integrated.Camera(self)
        self.camera.create_hooks()
        self.centralWidget().layout().addWidget(self.camera, 0, 3, 1, 1)

        # Add Plotter
        self.plotter = gui.Integrated.Plotter(self)
        self.plotter.setMinimumHeight(300)
        self.plotter.setMaximumHeight(400)
        self.plotter.create_hooks()
        self.centralWidget().layout().addWidget(self.plotter, 1, 0, 1, 4)

        # Process monitor
        self.process_monitor = gui.Integrated.ProcessMonitor(self)
        self.process_monitor.setMaximumHeight(400)
        self.centralWidget().layout().addWidget(self.process_monitor, 2, 0)

        # Recordings
        self.recordings = gui.Integrated.Recording(self)
        self.recordings.setMaximumHeight(400)
        self.centralWidget().layout().addWidget(self.recordings, 2, 1)

        # Logger
        self.log_display = gui.Integrated.Log(self)
        self.log_display.setMinimumHeight(200)
        self.log_display.setMaximumHeight(400)
        self.centralWidget().layout().addWidget(self.log_display, 2, 2, 1, 2)

        # Setup menubar
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
        self._bind_shortcuts()


    def restart_camera(self):
        IPC.rpc(Def.Process.Controller,
                process.Controller.initialize_process,
                process.Camera)

    def restart_display(self):
        IPC.rpc(Def.Process.Controller,
                process.Controller.initialize_process,
                process.Display)

    def _bind_shortcuts(self):

        # Restart display process
        self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
        self.menu_process.restart_display.setAutoRepeat(False)
        # Restart camera process
        if Config.Camera[Def.CameraCfg.use]:
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Inform controller of close event
        IPC.send(Def.Process.Controller, Def.Signal.shutdown)

        # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
        IPC.set_state(Def.State.STOPPED)
