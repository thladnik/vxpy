"""
MappApp ./core/gui.py
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
from PyQt5 import QtWidgets

from mappapp import Config
from mappapp import Def
from mappapp import Logging

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mappapp.process.gui import Gui


class AddonWidget(QtWidgets.QWidget):

    def __init__(self,main):
        QtWidgets.QWidget.__init__(self)
        self.main = main
        self.module_active = True


class IntegratedWidget(QtWidgets.QGroupBox):

    def __init__(self,group_name,main):
        QtWidgets.QGroupBox.__init__(self,group_name)
        self.main: Gui = main

        # List of exposed methods to register for rpc callbacks
        self.exposed = list()

    def add_widgets(self,process_name):

        # Add camera addons
        selected_addons = Config.Gui[Def.GuiCfg.addons]
        used_here = selected_addons[process_name]

        for module_name,widgets in used_here.items():
            for widget_name in widgets:
                if not (bool(widget_name)):
                    continue

                # TODO: expand this to draw from all files in ./gui/
                path = '.'.join([Def.Path.Gui,process_name.lower(),module_name])
                module = importlib.import_module(path)

                wdgt = getattr(module,widget_name)(self.main)
                if not (wdgt.module_active):
                    Logging.write(Logging.WARNING,f'Addon {widget_name} could not be activated')
                    continue
                self.tab_widget.addTab(wdgt,widget_name)

    def create_hooks(self):
        for fun in self.exposed:
            fun_str = fun.__qualname__
            self.main.register_rpc_callback(self,fun_str,fun)