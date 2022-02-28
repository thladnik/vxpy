"""
vxPy ./modules/gui.py
Copyright (C) 2022 Tim Hladnik

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
import os.path
from PySide6 import QtCore, QtGui, QtWidgets
import sys

import vxpy
from vxpy import config
from vxpy.definitions import *
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.process as vxprocess
import vxpy.modules as vxmodules
from vxpy.gui import window_controls
from vxpy.gui import window_widgets

log = vxlogger.getLogger(__name__)


class Gui(vxprocess.AbstractProcess):
    name = PROCESS_GUI

    app: QtWidgets.QApplication

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)
        # Create application
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication(sys.argv)

        self.window = Window()

        # Run event loop
        self.run(interval=1/30)

    def main(self):
        self.app.processEvents()

    def prompt_shutdown_confirmation(self):
        reply = QtWidgets.QMessageBox.question(self.window, 'Confirm shutdown', 'Program is still busy. Shut down anyways?',
                                               QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Yes,
                                               QtWidgets.QMessageBox.StandardButton.Cancel)

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            vxipc.rpc(vxmodules.Controller.name, vxmodules.Controller._force_shutdown)

    def _start_shutdown(self):
        self.window.close()

        vxipc.Process.set_state(State.STOPPED)


class Window(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.WindowType.Window)

        controls_default_height = 400
        plotter_default_height = 300
        display_default_dims = (600, 500)
        camera_default_dims = (600, 500)
        io_default_dims = (600, 500)

        # Set icon
        iconpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.svg')
        self.setWindowIcon(QtGui.QIcon(iconpath))

        self.subwindows = []

        # Set up main window
        self.setWindowTitle('vxPy - vision experiments in Python')

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        self.screenGeo = vxipc.Process.app.primaryScreen().geometry()
        w, h = self.screenGeo.width(), self.screenGeo.height()
        x, y = self.screenGeo.x(), self.screenGeo.y()

        # Set main controls window

        # Main controls widget
        self.controls = QtWidgets.QWidget()
        self.controls.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.controls)

        # Process monitor
        self.process_monitor = window_controls.ProcessMonitorWidget(self)
        self.process_monitor.create_hooks()
        self.controls.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = window_controls.RecordingWidget(self)
        self.recordings.create_hooks()
        self.controls.layout().addWidget(self.recordings)

        # Logger
        self.log_display = window_controls.LoggingWidget(self)
        self.controls.layout().addWidget(self.log_display)

        # Set geometry
        self.move(x, y)
        self.resize(w, controls_default_height)

        # Optional sub windows

        row2_yoffset = -20
        row2_xoffset = 10

        # Display
        self.display = None
        if config.CONF_DISPLAY_USE and PROCESS_DISPLAY in config.CONF_GUI_ADDONS:
            self.display = window_widgets.DisplayWindow(self)
            self.display.create_hooks()
            self.display.move(x + row2_xoffset,
                              y + self.controls.size().height() + row2_yoffset)
            self.display.resize(*display_default_dims)
            self.subwindows.append(self.display)

        # Camera
        self.camera = None
        if config.CONF_CAMERA_USE and PROCESS_CAMERA in config.CONF_GUI_ADDONS:
            self.camera = window_widgets.CameraWindow(self)
            self.camera.create_hooks()
            self.camera.move(x + self.get_display_size()[0] + 2 * row2_xoffset,
                             y + self.controls.size().height() + row2_yoffset)
            self.camera.resize(*camera_default_dims)
            self.subwindows.append(self.camera)

        # Io
        self.io = None
        if config.CONF_IO_USE and PROCESS_IO in config.CONF_GUI_ADDONS:
            self.io = window_widgets.IoWindow(self)
            self.io.create_hooks()
            self.io.move(x + self.get_display_size()[0] + self.get_camera_size()[0] + 3 * row2_xoffset,
                         y + self.controls.size().height() + row2_yoffset)
            self.io.resize(*io_default_dims)
            self.subwindows.append(self.io)

        # Add Plotter
        self.plotter = window_widgets.PlottingWindow(self)
        self.plotter.setMinimumHeight(300)
        if sys.platform == 'linux':
            self.plotter.move(x, y + h-plotter_default_height)
            self.plotter.resize(w, plotter_default_height)
        else:
            self.plotter.move(x,
                              y + 0.9 * h - plotter_default_height)
            self.plotter.resize(w, plotter_default_height + int(0.05 * h))
        self.plotter.create_hooks()
        self.subwindows.append(self.plotter)

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
        if config.CONF_DISPLAY_USE:
            self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
            self.menu_process.restart_display.setAutoRepeat(False)
        # Restart camera modules
        if config.CONF_CAMERA_USE:
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

        self.show()

    def get_display_size(self):
        if self.display is None:
            return 0, 0,
        return self.display.size().width(), self.display.size().height()

    def get_camera_size(self):
        if self.camera is None:
            return 0, 0,
        return self.camera.size().width(), self.camera.size().height()

    def restart_camera(self):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, vxmodules.Camera)

    def restart_display(self):
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, vxmodules.Display)

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
            vxipc.send(PROCESS_CONTROLLER, Signal.shutdown)
            a0.setAccepted(False)
