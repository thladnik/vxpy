"""
MappApp ./core/uiutils.py
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
import importlib
from PySide6 import QtCore, QtWidgets

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy import Logging
from vxpy.core import ipc

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vxpy.modules.gui import Gui


class AddonWidget(QtWidgets.QWidget):

    def __init__(self,main):
        QtWidgets.QWidget.__init__(self)
        self.main = main
        self.module_active = True


class ExposedWidget:

    def __init__(self):
        # List of exposed methods to register for rpc callbacks
        self.exposed: list = []

    def create_hooks(self):
        for fun in self.exposed:
            fun_str = fun.__qualname__
            ipc.Process.register_rpc_callback(self, fun_str, fun)


class IntegratedWidget(QtWidgets.QGroupBox, ExposedWidget):

    def __init__(self, group_name, main):
        QtWidgets.QGroupBox.__init__(self, group_name, parent=main)
        self.main: Gui = main

        self.exposed = list()


class WindowWidget(QtWidgets.QWidget, ExposedWidget):

    def __init__(self, group_name, main):
        QtWidgets.QWidget.__init__(self, main, f=QtCore.Qt.WindowType.Window)
        self.setWindowTitle(group_name)
        self.main: Gui = main

        # List of exposed methods to register for rpc callbacks
        self.exposed = list()

        self.show()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            # Raise main window
            ipc.Process.window.raise_()
            ipc.Process.window.raise_subwindows()
            self.raise_()

        return QtWidgets.QWidget.event(self, event)


class WindowTabWidget(WindowWidget, ExposedWidget):
    def __init__(self, *args, **kwargs):
        WindowWidget.__init__(self, *args, **kwargs)

        # Add tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.tab_widget)

    def create_addon_tabs(self, process_name):

        used_addons = config.Gui[definitions.GuiCfg.addons][process_name]

        for path in used_addons:
            Logging.info(f'Load UI addon "{path}"')

            # TODO: search different paths for package structure redo
            # Load routine
            parts = path.split('.')
            module = importlib.import_module('.'.join(parts[:-1]))
            addon_cls = getattr(module, parts[-1])

            if addon_cls is None:
                Logging.error(f'UI addon "{path}" not found.')
                continue

            wdgt = addon_cls(self.main)

            self.tab_widget.addTab(wdgt, parts[-1])
