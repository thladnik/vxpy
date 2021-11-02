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

from PyQt6 import QtCore, QtGui, QtWidgets
import sys

from vxpy import Config
from vxpy import Def
from vxpy import modules
from vxpy.core import process, ipc
from vxpy import gui


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
                                               QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Yes,
                                               QtWidgets.QMessageBox.StandardButton.Cancel)

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            ipc.rpc(modules.Controller.name, modules.Controller._force_shutdown)

    def _start_shutdown(self):
        self.window.close()

        ipc.Process.set_state(Def.State.STOPPED)


class Window(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.WindowType.Window)

        controls_default_height = 400
        plotter_default_height = 300
        display_default_dims = (600, 500)
        camera_default_dims = (600, 500)
        io_default_dims = (600, 500)

        # Set icon
        if sys.platform == 'win32':
            self.setWindowIcon(QtGui.QIcon('MappApp.ico'))
        elif sys.platform == 'linux':
            self.setWindowIcon(QtGui.QIcon('mappapp/testicon.png'))

        self.subwindows = []

        # Set up main window
        self.setWindowTitle('MappApp - a thing to do stuff')

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, flags=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        self.screenGeo = ipc.Process.app.primaryScreen().geometry()
        w, h = self.screenGeo.width(), self.screenGeo.height()
        x, y = self.screenGeo.x(), self.screenGeo.y()

        # Set main controls window

        # Main controls widget
        self.controls = QtWidgets.QWidget()
        self.controls.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.controls)

        # Process monitor
        self.process_monitor = gui.ProcessMonitor(self)
        self.process_monitor.create_hooks()
        self.controls.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = gui.Recording(self)
        self.recordings.create_hooks()
        self.controls.layout().addWidget(self.recordings)

        # Logger
        self.log_display = gui.Logger(self)
        self.controls.layout().addWidget(self.log_display)

        # Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        # Menu windows
        self.menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self.menu_windows)
        self.window_toggles = []
        for subwin in self.subwindows:
            self.window_toggles.append(QtGui.QAction(f'Toggle {subwin.windowTitle()}'))
            self.window_toggles[-1].triggered.connect(subwin.toggle_visibility)
            self.menu_windows.addAction(self.window_toggles[-1])
        # Menu processes
        self.menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self.menu_process)
        self.menuBar().addMenu(self.menu_windows)
        # Restart camera
        self.menu_process.restart_camera = QtGui.QAction('Restart camera')
        self.menu_process.restart_camera.triggered.connect(self.restart_camera)
        self.menu_process.addAction(self.menu_process.restart_camera)
        # Restart display
        self.menu_process.restart_display = QtGui.QAction('Restart display')
        self.menu_process.restart_display.triggered.connect(self.restart_display)
        self.menu_process.addAction(self.menu_process.restart_display)

        # Bind shortcuts
        # Restart display modules
        self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
        self.menu_process.restart_display.setAutoRepeat(False)
        # Restart camera modules
        if Config.Camera[Def.CameraCfg.use]:
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

        # Set geometry
        self.move(x, y)
        self.resize(w, controls_default_height)

        # Optional sub windows


        # Display
        if Config.Display[Def.DisplayCfg.use] \
                and Def.Process.Display in Config.Gui[Def.GuiCfg.addons] \
                and bool(Config.Gui[Def.GuiCfg.addons][Def.Process.Display]):
            self.display = gui.Display(self)
            self.display.create_hooks()
            self.display.move(x, self.controls.size().height())
            self.display.resize(*display_default_dims)
            self.subwindows.append(self.display)

        # Camera
        if Config.Camera[Def.CameraCfg.use] \
                and Def.Process.Camera in Config.Gui[Def.GuiCfg.addons] \
                and bool(Config.Gui[Def.GuiCfg.addons][Def.Process.Camera]):
            self.camera = gui.Camera(self)
            self.camera.create_hooks()
            self.camera.move(x + display_default_dims[0] + 75, self.controls.size().height())
            self.camera.resize(*camera_default_dims)
            self.subwindows.append(self.camera)

        # Io
        if Config.Io[Def.IoCfg.use] \
                and Def.Process.Io in Config.Gui[Def.GuiCfg.addons] \
                and bool(Config.Gui[Def.GuiCfg.addons][Def.Process.Io]):
            self.io = gui.Io(self)
            self.io.create_hooks()
            self.io.move(x + display_default_dims[0] + camera_default_dims[0] + 75, self.controls.size().height())
            self.io.resize(*io_default_dims)
            self.subwindows.append(self.io)

        # Add Plotter
        self.plotter = gui.Plotter(self)
        self.plotter.setMinimumHeight(300)
        if sys.platform == 'linux':
            self.plotter.move(x, h-plotter_default_height)
            self.plotter.resize(w, plotter_default_height)
        else:
            self.plotter.move(x, 0.9 * h - plotter_default_height)
            self.plotter.resize(w, plotter_default_height + int(0.05 * h))
        self.plotter.create_hooks()
        self.subwindows.append(self.plotter)

        self.show()

    def restart_camera(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.initialize_process, modules.Camera)

    def restart_display(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.initialize_process, modules.Display)

    def raise_subwindows(self):
        for w in self.subwindows:
            w.raise_()

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            self.raise_subwindows()
            self.raise_()

        return QtWidgets.QWidget.event(self, event)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if a0 is not None:
            # TODO: postpone closing of GUI and keep GUI respponsive while other processes are still running.
            # while len(ipc.Log.History) > 0:
            #     ipc.Process.main()

            # Inform controller of close event
            ipc.send(Def.Process.Controller, Def.Signal.shutdown)
            a0.setAccepted(False)
