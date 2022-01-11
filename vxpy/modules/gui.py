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
from PySide6 import QtCore, QtGui, QtWidgets
import sys

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.definitions import *
from vxpy import modules
from vxpy.core import process, ipc, logging
from vxpy.gui.window_controls import LoggingWidget, ProcessMonitorWidget, RecordingWidget
from vxpy.gui.window_widgets import CameraWindow, DisplayWindow, IoWindow, PlottingWindow

log = logging.getLogger(__name__)


class Gui(process.AbstractProcess):
    name = PROCESS_GUI

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

        ipc.Process.set_state(definitions.State.STOPPED)


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
            self.setWindowIcon(QtGui.QIcon('vxpy_icon.ico'))
        elif sys.platform == 'linux':
            self.setWindowIcon(QtGui.QIcon('vxpy_icon.png'))

        self.subwindows = []

        # Set up main window
        self.setWindowTitle('vxPy - vision experiments in Python')

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
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
        self.process_monitor = ProcessMonitorWidget(self)
        self.process_monitor.create_hooks()
        self.controls.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = RecordingWidget(self)
        self.recordings.create_hooks()
        self.controls.layout().addWidget(self.recordings)

        # Logger
        self.log_display = LoggingWidget(self)
        self.controls.layout().addWidget(self.log_display)

        # Set geometry
        self.move(x, y)
        self.resize(w, controls_default_height)

        # Optional sub windows

        row2_yoffset = -20
        row2_xoffset = 10

        # Display
        self.display = None
        if config.Display[definitions.DisplayCfg.use] \
                and PROCESS_DISPLAY in config.Gui[definitions.GuiCfg.addons] \
                and bool(config.Gui[definitions.GuiCfg.addons][PROCESS_DISPLAY]):
            self.display = DisplayWindow(self)
            self.display.create_hooks()
            self.display.move(x + row2_xoffset,
                              y + self.controls.size().height() + row2_yoffset)
            self.display.resize(*display_default_dims)
            self.subwindows.append(self.display)

        # Camera
        self.camera = None
        if config.Camera[definitions.CameraCfg.use] \
                and PROCESS_CAMERA in config.Gui[definitions.GuiCfg.addons] \
                and bool(config.Gui[definitions.GuiCfg.addons][PROCESS_CAMERA]):
            self.camera = CameraWindow(self)
            self.camera.create_hooks()
            self.camera.move(x + self.get_display_size()[0] + 2 * row2_xoffset,
                             y + self.controls.size().height() + row2_yoffset)
            self.camera.resize(*camera_default_dims)
            self.subwindows.append(self.camera)

        # Io
        self.io = None
        if config.Io[definitions.IoCfg.use] \
                and PROCESS_IO in config.Gui[definitions.GuiCfg.addons] \
                and bool(config.Gui[definitions.GuiCfg.addons][PROCESS_IO]):
            self.io = IoWindow(self)
            self.io.create_hooks()
            self.io.move(x + self.get_display_size()[0] + self.get_camera_size()[0] + 3 * row2_xoffset,
                         y + self.controls.size().height() + row2_yoffset)
            self.io.resize(*io_default_dims)
            self.subwindows.append(self.io)

        # Add Plotter
        self.plotter = PlottingWindow(self)
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
        self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
        self.menu_process.restart_display.setAutoRepeat(False)
        # Restart camera modules
        if config.Camera[definitions.CameraCfg.use]:
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
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.initialize_process, modules.Camera)

    def restart_display(self):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.initialize_process, modules.Display)

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
            ipc.send(PROCESS_CONTROLLER, definitions.Signal.shutdown)
            a0.setAccepted(False)
