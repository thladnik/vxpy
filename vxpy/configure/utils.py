"""
MappApp ./setup/utils.py
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
from PySide6 import QtWidgets


class ModuleWidget(QtWidgets.QWidget):

    def __init__(self, module_name, *_args, **_kwargs):
        QtWidgets.QWidget.__init__(self, *_args, **_kwargs)

        self.module_name = module_name

    def get_setting(self, option_name):
        global current_config
        return current_config.getParsed(self.module_name, option_name)

    def update_setting(self, option, value):
        global current_config
        current_config.setParsed(self.module_name, option, value)

    def closed_main_window(self):
        """Method called by default in MainWindow on closeEvent"""
        pass

    def load_settings_from_config(self):
        """Method called by default in MainWindow when selecting new configuration"""
        pass
