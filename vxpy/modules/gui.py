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
from __future__ import annotations
import ctypes
import importlib
import os.path
from typing import Dict, List

import qdarktheme
from PySide6 import QtCore, QtGui, QtWidgets
import sys

import vxpy
from vxpy import config
from vxpy.definitions import *
import vxpy.core.ipc as vxipc
import vxpy.core.ui as vxui
import vxpy.core.logger as vxlogger
import vxpy.core.process as vxprocess
import vxpy.modules as vxmodules

log = vxlogger.getLogger(__name__)


class Gui(vxprocess.AbstractProcess):
    name = PROCESS_GUI

    instance: Gui = None
    app: QtWidgets.QApplication = None
    window: Window = None

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)
        self.instance = self

        # Create application
        Gui.app = QtWidgets.QApplication.instance()
        if Gui.app is None:
            Gui.app = QtWidgets.QApplication(sys.argv)

        # Set theme
        qdarktheme.setup_theme('dark')

        # Create main window
        self.window = Window()
        self.window.show()

        # Run event loop
        self.run(interval=1 / config.GUI_REFRESH)

    def main(self):
        self.app.processEvents()

    def prompt_shutdown_confirmation(self):
        reply = QtWidgets.QMessageBox.question(self.window,
                                               'Confirm shutdown',
                                               'Program is still busy. Shut down anyways?',
                                               QtWidgets.QMessageBox.StandardButton.Cancel |
                                               QtWidgets.QMessageBox.StandardButton.Yes,
                                               QtWidgets.QMessageBox.StandardButton.Cancel)

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            vxipc.rpc(vxmodules.Controller.name, vxmodules.Controller._force_shutdown)

    def _start_shutdown(self):
        self.window.close()

        self.set_state(STATE.STOPPED)


class Window(QtWidgets.QMainWindow):

    instance: Window = None

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.WindowType.Window)
        self.instance = self

        # Fix icon issues on Windows systems
        if sys.platform == 'win32':
            # Explicitly set app-id as suggested by https://stackoverflow.com/a/1552105
            appid = f'vxpy.application.{vxpy.get_version()}'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

        if Gui.app.platformName() not in ['x11', 'xcb']:
            log.warning(f'Using {Gui.app.platformName()} windowing platform. This is untested.')

        screen = Gui.app.screens()[config.GUI_SCREEN]
        sgeo = screen.geometry()
        sx, sy, sw, sh = sgeo.getRect()
        self.sx, self.sy, self.sw, self.sh = sgeo.getRect()

        # Set main window
        self.setWindowTitle(f'vxPy - vision experiments in Python (v{vxpy.get_version()})')
        self.setWindowIcon(QtGui.QIcon(os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.svg')))
        # Make known to window manager
        self.createWinId()
        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QHBoxLayout())

        # Set up reference container for all sub windows
        self.subwindows: List[vxui.WindowWidget] = []

        # Add all widgets

        # Control widgets
        self.control_wdgt = QtWidgets.QWidget()
        self.control_wdgt.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.control_wdgt)

        # Main monitoring widget
        self.monitoring_wdgt = QtWidgets.QWidget()
        self.monitoring_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().addWidget(self.monitoring_wdgt)

        # Process monitor
        self.process_monitor = vxui.ProcessMonitorWidget(self)
        self.process_monitor.create_hooks()
        self.monitoring_wdgt.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = vxui.RecordingWidget(self)
        self.recordings.create_hooks()
        self.control_wdgt.layout().addWidget(self.recordings)

        # Protocols}
        self.protocols = vxui.ProtocolWidget(self)
        self.protocols.create_hooks()
        self.control_wdgt.layout().addWidget(self.protocols)

        # Logger
        self.log_display = vxui.LoggingWidget(self)
        self.monitoring_wdgt.layout().addWidget(self.log_display)

        # Add Plotter window
        self.plotter_window = vxpy.core.ui.PlottingWindow(self)
        self.plotter_window.setMinimumHeight(300)
        self.plotter_window.create_hooks()
        self.subwindows.append(self.plotter_window)

        # Add addon widget window if any are selected in config
        self.addon_widgets: Dict[str, vxui.AddonWidget] = {}
        self.addon_window = None
        if any([config.DISPLAY_USE, config.CAMERA_USE, config.IO_USE]) and len(config.GUI_ADDONS) > 0:

            # Create addon window
            self.addon_window = vxui.AddonWindow(self)

            # Create addon widget for each addon
            for addon_path, addon_ops in config.GUI_ADDONS.items():
                log.info(f'Load UI addon {addon_path}')

                # Load routine
                parts = addon_path.split('.')
                module = importlib.import_module('.'.join(parts[:-1]))
                addon_cls = getattr(module, parts[-1])

                if addon_cls is None:
                    log.error(f'UI addon {addon_path} not found.')
                    continue

                # Create widget
                wdgt: vxui.AddonWidget = addon_cls(self.addon_window, self, **addon_ops)

                # Create hooks
                wdgt.create_hooks()

                # Add to subwindows, since widget might get detached later
                self.subwindows.append(wdgt)

                # Add widget to dict
                self.addon_widgets[wdgt.__class__.__qualname__] = wdgt

                # Attach to addon widget window
                if 'detached' in addon_ops and addon_ops['detached']:
                    wdgt.detach()
                else:
                    wdgt.attach()

            # Create hooks
            self.addon_window.create_hooks()

            # Add subwindow
            self.subwindows.append(self.addon_window)

        # Resize main window
        mwh = 1000
        if sh < 1500:
            mwh = 500
        self.resize(sw, mwh)
        if sys.platform == 'win32':
            # TODO: test this on Ubuntu
            self.move(self.sx, self.sy)
        Gui.app.processEvents()

        # Resize and place addon window
        aww = 1500
        if sw < 2600:
            aww = 1000
        awh = 1000
        if sh < 1500:
            awh = 700
        self.addon_window.resize(aww, awh)
        self.addon_window.move(sx, sy + self.pos().y() + self.size().height() + 120)

        # Resize and place plotter window
        pww = 1800
        if sw < 2600:
            pww = 1500
        pwh = 1000
        if sh < 1500:
            pwh = 700
        self.plotter_window.resize(pww, pwh)
        self.plotter_window.move(self.addon_window.pos().x() + self.addon_window.size().width() + 20,
                                 sy + self.pos().y() + self.size().height() + 120)

        # Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())

        # Windows actions
        self.menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self.menu_windows)

        self.window_toggles = []
        for subwin in self.subwindows:
            self.window_toggles.append(QtGui.QAction(f'Toggle {subwin.windowTitle()}'))
            self.window_toggles[-1].triggered.connect(subwin.toggle_visibility)
            self.menu_windows.addAction(self.window_toggles[-1])

        # Processes actions
        self.menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self.menu_process)

        # Restart display module
        if config.DISPLAY_USE:
            self.menu_process.restart_display = QtGui.QAction('Restart display')
            self.menu_process.restart_display.triggered.connect(self.restart_display)
            self.menu_process.addAction(self.menu_process.restart_display)
            self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
            self.menu_process.restart_display.setAutoRepeat(False)

        # Restart camera module
        if config.CAMERA_USE:
            self.menu_process.restart_camera = QtGui.QAction('Restart camera')
            self.menu_process.restart_camera.triggered.connect(self.restart_camera)
            self.menu_process.addAction(self.menu_process.restart_camera)
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

        # Restart camera module
        if config.IO_USE:
            self.menu_process.restart_io = QtGui.QAction('Restart IO')
            self.menu_process.restart_io.triggered.connect(self.restart_io)
            self.menu_process.addAction(self.menu_process.restart_io)
            self.menu_process.restart_io.setShortcut('Ctrl+Alt+Shift+i')
            self.menu_process.restart_io.setAutoRepeat(False)

    @staticmethod
    def restart_camera():
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, vxmodules.Camera)

    @staticmethod
    def restart_display():
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, vxmodules.Display)

    @staticmethod
    def restart_io():
        vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, vxmodules.Io)

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

            # Inform controller of close event
            vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.commence_shutdown)
            a0.setAccepted(False)
