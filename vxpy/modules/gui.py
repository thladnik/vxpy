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
import ctypes
import os.path
from PySide6 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet
import sys

import vxpy
import vxpy.core.ui
from vxpy import config
from vxpy.definitions import *
import vxpy.core.ipc as vxipc
import vxpy.core.ui as vxgui
import vxpy.core.logger as vxlogger
import vxpy.core.process as vxprocess
import vxpy.modules as vxmodules

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
        self.window.show()

        # Run event loop
        self.run(interval=1 / 30)

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

        vxipc.LocalProcess.set_state(STATE.STOPPED)


class Window(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.WindowType.Window)

        # Fix icon issues on windows systems
        if sys.platform == 'win32':
            # Explicitly set app-id as suggested by https://stackoverflow.com/a/1552105
            appid = u'vxpy.application.0.0.1'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

        # Set offsets
        row2_yoffset = 0
        row2_xoffset = 0
        side_window_borders = 5
        x_spacing = 5

        # Set icon
        iconpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.svg')
        self.setWindowIcon(QtGui.QIcon(iconpath))

        self.subwindows = []

        # Set up main window
        self.setWindowTitle('vxPy - vision experiments in Python')

        # Setup central widget
        self.setCentralWidget(QtWidgets.QWidget(parent=self, f=QtCore.Qt.WindowType.Widget))
        self.centralWidget().setLayout(QtWidgets.QHBoxLayout())

        # Control widgets
        self.control_wdgt = QtWidgets.QWidget()
        self.control_wdgt.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.control_wdgt)

        # Main monitoring widget
        self.monitoring_wdgt = QtWidgets.QWidget()
        self.monitoring_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().addWidget(self.monitoring_wdgt)

        # Process monitor
        self.process_monitor = vxpy.core.ui.ProcessMonitorWidget(self)
        self.process_monitor.create_hooks()
        self.monitoring_wdgt.layout().addWidget(self.process_monitor)

        # Recordings
        self.recordings = vxpy.core.ui.RecordingWidget(self)
        self.recordings.create_hooks()
        self.control_wdgt.layout().addWidget(self.recordings)

        # Protocols}
        self.protocols = vxpy.core.ui.ProtocolWidget(self)
        self.protocols.create_hooks()
        self.control_wdgt.layout().addWidget(self.protocols)

        # Logger
        self.log_display = vxpy.core.ui.LoggingWidget(self)
        self.monitoring_wdgt.layout().addWidget(self.log_display)

        # Set geometry
        self.setMinimumHeight(500)
        screen = vxipc.LocalProcess.app.screens()[config.CONF_GUI_SCREEN]

        self.screenGeo = screen.geometry()
        width, height = self.screenGeo.width(), self.screenGeo.height()
        xpos, ypos = self.screenGeo.x(), self.screenGeo.y()
        self.move(xpos, ypos)
        self.resize(width-side_window_borders, height // 2 if height <= 1080 else 540)

        # Optional sub windows
        titlebar_height = 40
        bottom_height_offset = 80
        # if sys.platform == 'win32':
        #     titlebar_height = 40
        #     bottom_height_offset = 120
        # else:
        #     titlebar_height = 0
        #     bottom_height_offset = 120
        main_window_height = self.size().height() + titlebar_height
        addon_window_default_dims = (600, 600)

        # Addon widget window if any addons are selected in config
        self.addon_widget_window = None
        if any([config.CONF_DISPLAY_USE, config.CONF_CAMERA_USE, config.CONF_IO_USE]) and bool(config.CONF_GUI_ADDONS):

            # Create windowed tab
            self.addon_widget_window = vxgui.AddonWindow(self)

            for process_name, addons in config.CONF_GUI_ADDONS.items():
                self.addon_widget_window.create_addon_tabs(process_name)

            # Create hooks
            self.addon_widget_window.create_hooks()

            # Place and resize addon widget
            self.addon_widget_window.move(xpos + row2_xoffset,
                                          ypos + main_window_height + row2_yoffset)
            if height - self.size().height() - addon_window_default_dims[1] > bottom_height_offset:
                addon_height = addon_window_default_dims[1]
            else:
                addon_height = height - self.size().height() - bottom_height_offset
            self.addon_widget_window.resize(addon_window_default_dims[0], addon_height)

            # Add subwindow
            self.subwindows.append(self.addon_widget_window)

        # Add Plotter
        self.plotter = vxpy.core.ui.PlottingWindow(self)
        self.plotter.setMinimumHeight(300)

        # Place and resize
        addon_win_width = self.addon_widget_window.size().width() if self.addon_widget_window is not None else 0
        self.plotter.move(xpos + row2_xoffset + addon_win_width + x_spacing,
                          ypos + self.size().height() + titlebar_height + row2_yoffset)

        if height - self.size().height() - addon_window_default_dims[1] > bottom_height_offset:
            plotter_height = addon_window_default_dims[1]
        else:
            plotter_height = height - self.size().height() - bottom_height_offset

        self.plotter.resize(width - addon_win_width - x_spacing,
                            plotter_height)

        self.plotter.create_hooks()
        self.subwindows.append(self.plotter)

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

        # Add modules
        # self.module_menus: Dict[str, QtWidgets.QMenu] = {}
        # module_opts = [(config.CONF_CAMERA_USE, PROCESS_CAMERA, vxmodules.Camera),
        #                (config.CONF_DISPLAY_USE, PROCESS_DISPLAY, vxmodules.Display),
        #                (config.CONF_GUI_USE, PROCESS_GUI, vxmodules.Gui),
        #                (config.CONF_IO_USE, PROCESS_IO, vxmodules.Io),
        #                (config.CONF_WORKER_USE, PROCESS_WORKER, vxmodules.Worker)]
        #
        # for use, name, module in module_opts:
        #     if not use:
        #         continue
        #
        #     # Create menu
        #     menu = QtWidgets.QMenu(name)
        #     self.menuBar().addMenu(menu)
        #
        #     # Add restart action
        #     action = menu.addAction('Restart')
        #     action.triggered.connect(self.restart_process(module))
        #     action.setAutoRepeat(False)
        #
        #     self.module_menus[name] = menu

        # Processes actions
        self.menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self.menu_process)

        # Restart display module
        if config.CONF_DISPLAY_USE:
            self.menu_process.restart_display = QtGui.QAction('Restart display')
            self.menu_process.restart_display.triggered.connect(self.restart_display)
            self.menu_process.addAction(self.menu_process.restart_display)
            self.menu_process.restart_display.setShortcut('Ctrl+Alt+Shift+d')
            self.menu_process.restart_display.setAutoRepeat(False)

        # Restart camera module
        if config.CONF_CAMERA_USE:
            self.menu_process.restart_camera = QtGui.QAction('Restart camera')
            self.menu_process.restart_camera.triggered.connect(self.restart_camera)
            self.menu_process.addAction(self.menu_process.restart_camera)
            self.menu_process.restart_camera.setShortcut('Ctrl+Alt+Shift+c')
            self.menu_process.restart_camera.setAutoRepeat(False)

        # Restart camera module
        if config.CONF_IO_USE:
            self.menu_process.restart_io = QtGui.QAction('Restart IO')
            self.menu_process.restart_io.triggered.connect(self.restart_io)
            self.menu_process.addAction(self.menu_process.restart_io)
            self.menu_process.restart_io.setShortcut('Ctrl+Alt+Shift+i')
            self.menu_process.restart_io.setAutoRepeat(False)

        # Set theme
        extra = {'density_scale': '-2', }
        apply_stylesheet(vxipc.LocalProcess.app, theme='dark_amber.xml', invert_secondary=False, extra=extra)
        # apply_stylesheet(vxipc.Process.app, theme='dark_teal.xml', extra=extra)

    # @staticmethod
    # def restart_process(module):
    #     def _restart():
    #         vxipc.rpc(PROCESS_CONTROLLER, vxmodules.Controller.initialize_process, module)
    #     return _restart

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
