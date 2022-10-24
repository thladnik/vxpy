"""
vxPy ./core/gui.py
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
import importlib

from PySide6 import QtCore, QtWidgets
from typing import Callable, List, Union

from vxpy import config
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
from vxpy.addons import core_widgets
from vxpy.core import ipc
from vxpy.definitions import *
import vxpy.modules as vxmodules
from vxpy.definitions import PROCESS_GUI

log = vxlogger.getLogger(__name__)


class Widget:
    """Base widget"""

    def __init__(self, main):
        self.main: vxmodules.Gui = main


class ExposedWidget:
    """Widget base class for widgets which expose bound methods to be called from external sources"""

    def __init__(self):
        # List of exposed methods to register for rpc callbacks
        self.exposed: List[Callable] = []

    def create_hooks(self):
        """Register exposed functions as callbacks with the local process"""
        for fun in self.exposed:
            fun_str = fun.__qualname__
            vxipc.Process.register_rpc_callback(self, fun_str, fun)


class RoutineParameter:

    def __init__(self, addon_cls: AddonWidget, update_fun: Callable):
        self.addon_class = addon_cls
        self.routine_update_fun = update_fun

    def update(self, *args, **kwargs):
        vxipc.rpc(self.addon_class.name, self.routine_update_fun, *args, **kwargs)


class AddonWidget(QtWidgets.QWidget, ExposedWidget, Widget):
    """Addon widget which should be subclassed by custom widgets in plugins, etc"""

    name = None
    display_name = None

    def __init__(self, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=main)
        self.module_active = True

    @staticmethod
    def connect_to_timer(fun: Callable):
        AddonWindow.timer.timeout.connect(fun)

    @classmethod
    def call_routine(cls, fun, *args, **kwargs):
        vxipc.rpc(cls.name, fun, *args, **kwargs)


class CameraAddonWidget(AddonWidget):

    name = PROCESS_CAMERA

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)


class DisplayAddonWidget(AddonWidget):

    name = PROCESS_DISPLAY

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)


class IoAddonWidget(AddonWidget):

    name = PROCESS_IO

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)


class WorkerAddonWidget(AddonWidget):

    name = PROCESS_WORKER

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)


class IntegratedWidget(QtWidgets.QGroupBox, ExposedWidget, Widget):
    """Integrated widgets which are part of the  main window"""

    def __init__(self, group_name: str, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QGroupBox.__init__(self, group_name, parent=main)


class WindowWidget(QtWidgets.QWidget, ExposedWidget, Widget):
    """Widget that should be displayed as a separate window"""

    def __init__(self, title: str, main):
        Widget.__init__(self, main=main)
        ExposedWidget.__init__(self)
        QtWidgets.QWidget.__init__(self, parent=main, f=QtCore.Qt.WindowType.Window)

        # Set title
        self.setWindowTitle(title)

        # Make known to window manager
        self.createWinId()

        # Open/show
        self.show()

    def toggle_visibility(self):
        """Switch visibility based on current visibility"""

        if self.isVisible():
            self.hide()
        else:
            self.show()

        if self.isMinimized():
            self.showNormal()

    def event(self, event):
        """Catch all events and execute custom responses"""

        # If window is activated (e.g. brought to front),
        # this also raises all other windows
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            # Raise main window
            vxipc.Process.window.raise_()
            # Raise all subwindows
            vxipc.Process.window.raise_subwindows()
            # Raise this window last
            self.raise_()

        return QtWidgets.QWidget.event(self, event)


class WindowTabWidget(WindowWidget, ExposedWidget):
    """Windowed widget which implements a central tab widget that is used to display addon widgets"""

    def __init__(self, *args, **kwargs):
        WindowWidget.__init__(self, *args, **kwargs)

        # Add tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.tab_widget)

    def create_addon_tabs(self, process_name: str) -> None:
        """Read UI addons for local given process and add them to central tab widget.

        :param process_name: name of process for which to add the addons to the tab widget
        """
        # Select ui addons for this local
        used_addons = config.CONF_GUI_ADDONS[process_name]

        # Add all addons as individual tabs to tab widget
        for path in used_addons:
            log.info(f'Load UI addon {path}')

            # Load routine
            parts = path.split('.')
            module = importlib.import_module('.'.join(parts[:-1]))
            addon_cls = getattr(module, parts[-1])

            if addon_cls is None:
                log.error(f'UI addon {path} not found.')
                continue

            wdgt = addon_cls(self.main)

            if addon_cls.display_name is None:
                display_name = parts[-1]
            else:
                display_name = addon_cls.display_name

            self.tab_widget.addTab(wdgt, f'{process_name}:{display_name}')


class AddonWindow(WindowTabWidget):
    timer = QtCore.QTimer()
    timer_interval = 50  # ms

    def __init__(self, *args):
        WindowTabWidget.__init__(self, 'Addon widgets', *args)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.stream_fps = 20
        self.timer.setInterval(self.timer_interval)
        self.timer.start()


def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(PROCESS_GUI, core_widgets.PlottingWindow.add_buffer_attribute, attr_name, *args, **kwargs)
