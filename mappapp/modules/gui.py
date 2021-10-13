"""
MappApp ./modules/uiutils.py
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

from mappapp import Config
from mappapp import Def
from mappapp import modules
from mappapp.core import process, ipc
from mappapp import gui


class Gui(process.AbstractProcess):
    name = Def.Process.Gui

    app: QtWidgets.QApplication

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)
        # Create application
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication(sys.argv)

        self.window = Window()

        # Run event loop
        self.run(interval=1/40)

    def main(self):
        self.app.processEvents()

    def prompt_shutdown_confirmation(self):
        reply = QtWidgets.QMessageBox.question(self.window, 'Confirm shutdown', 'Program is still busy. Shut down anyways?',
                                               QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Yes,
                                               QtWidgets.QMessageBox.Cancel)

        if reply == QtWidgets.QMessageBox.Yes:
            ipc.rpc(modules.Controller.name, modules.Controller._force_shutdown)

    def _start_shutdown(self):
        self.window.close()

        ipc.Process.set_state(Def.State.STOPPED)


class Window(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        # Set icon
        if sys.platform == 'win32':
            self.setWindowIcon(QtGui.QIcon('MappApp.ico'))
        elif sys.platform == 'linux':
            self.setWindowIcon(QtGui.QIcon('mappapp/testicon.png'))

        # Setup basic UI
        self.setup_ui()

    def setup_ui(self):

        # Set up main window
        self.setWindowTitle('MappApp')

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        # Upper
        self.upper_widget = QtWidgets.QWidget()
        self.upper_widget.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.upper_widget)

        # Display
        if Config.Display[Def.DisplayCfg.use]:
            self.display = gui.Display(self)
            self.display.create_hooks()
            self.upper_widget.layout().addWidget(self.display)

        # Display
        if Config.Io[Def.IoCfg.use]:
            self.io = gui.Io(self)
            self.io.create_hooks()
            self.upper_widget.layout().addWidget(self.io)

        # Camera
        if Config.Camera[Def.CameraCfg.use]:
            self.camera = gui.Camera(self)
            self.camera.create_hooks()
            self.upper_widget.layout().addWidget(self.camera)

        # Middle
        # Add Plotter
        self.plotter = gui.Plotter(self)
        self.plotter.setMinimumHeight(300)
        self.plotter.setMaximumHeight(400)
        self.plotter.create_hooks()
        self.centralWidget().layout().addWidget(self.plotter)

        # Lower
        self.lower_widget = QtWidgets.QWidget()
        self.lower_widget.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.lower_widget)

        # Process monitor
        self.process_monitor = gui.ProcessMonitor(self)
        self.process_monitor.setMaximumHeight(400)
        self.process_monitor.create_hooks()
        self.lower_widget.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = gui.Recording(self)
        self.recordings.setMaximumHeight(400)
        self.recordings.create_hooks()
        self.lower_widget.layout().addWidget(self.recordings)

        # Logger
        self.log_display = gui.Logger(self)
        self.log_display.setMinimumHeight(200)
        self.log_display.setMaximumHeight(400)
        self.lower_widget.layout().addWidget(self.log_display)

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

        # Set geometry
        # self.move(0, 0)
        self.screenGeo = ipc.Process.app.primaryScreen().geometry()
        w, h = self.screenGeo.width(), self.screenGeo.height()
        x,y = self.screenGeo.x(), self.screenGeo.y()

        self.move(x, y)
        if w > 1920 or h > 1080:
            if w > 1920:
                w = self.screenGeo.width()
            self.resize(w, 75 * h // 100)
            self.show()
        else:
            self.showMaximized()

    def restart_camera(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.initialize_process, modules.Camera)

    def restart_display(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.initialize_process, modules.Display)

    def _bind_shortcuts(self):

        # Restart display modules
        self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
        self.menu_process.restart_display.setAutoRepeat(False)
        # Restart camera modules
        if Config.Camera[Def.CameraCfg.use]:
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if a0 is not None:
            # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
            # while len(ipc.Log.History) > 0:
            #     ipc.Process.main()

            # Inform controller of close event
            ipc.send(Def.Process.Controller, Def.Signal.shutdown)
            a0.setAccepted(False)
