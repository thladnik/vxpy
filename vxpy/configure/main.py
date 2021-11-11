"""
MappApp ./setup/main.py
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
from configparser import ConfigParser
import os
from PySide6 import QtCore, QtWidgets

from vxpy import Config
from vxpy import Def
from vxpy.Def import *
from vxpy import Logging
from vxpy.configure import acc
from vxpy.configure.utils import ModuleWidget
from vxpy.configure.camera.__init__ import CameraWidget
from vxpy.configure.display import Main as Display
from vxpy.utils import misc

Logging.write = lambda *args,**kwargs: None


class ModuleCheckbox(QtWidgets.QCheckBox):

    def __init__(self, module_name, *_args):
        QtWidgets.QCheckBox.__init__(self, module_name.upper(), *_args)
        self.module_name = module_name

        self.toggled.connect(self.react_to_toggle)

    def react_to_toggle(self, bool):
        print('Set module \"{}\" usage to {}'.format(self.text(), bool))
        acc.cur_conf.setParsed(self.module_name, Def.Cfg.use, bool)


class StartupConfiguration(QtWidgets.QMainWindow):

    _availModules = {Def.CameraCfg.name: CameraWidget,
                     Def.DisplayCfg.name: Display,
                     Def.GuiCfg.name: ModuleWidget,
                     Def.IoCfg.name: ModuleWidget,
                     Def.RecCfg.name: ModuleWidget}

    # sig_reload_config = QtCore.pyqtSignal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

    def setup_ui(self):

        self._configfile = None
        self._currentConfigChanged = False

        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)

        # Setup window
        self.resize(1200, 1000)

        # Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        # Config file selection
        self.gb_select = QtWidgets.QGroupBox('Select config file...')
        self.gb_select.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.gb_select)

        # Selection
        self.gb_select.layout().addWidget(QtWidgets.QLabel('Select configuration file: '))
        self.gb_select.cb_select = QtWidgets.QComboBox()
        self.gb_select.cb_select.currentTextChanged.connect(self.open_config)
        self.gb_select.layout().addWidget(self.gb_select.cb_select)
        # New
        self.gb_select.btn_new = QtWidgets.QPushButton('Add new...')
        self.gb_select.btn_new.clicked.connect(self._add_configfile)
        self.gb_select.layout().addWidget(self.gb_select.btn_new)
        # Use
        self.gb_select.btn_use = QtWidgets.QPushButton('Use')
        self.gb_select.btn_use.clicked.connect(self.start_application)
        self.gb_select.layout().addWidget(self.gb_select.btn_use)

        # Change configurations for current file
        self.gb_edit = QtWidgets.QGroupBox('Change config')
        self.gb_edit.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self.gb_edit)

        #
        # Module selection
        self.gb_edit.gb_select_mod = QtWidgets.QGroupBox('Select modules')
        self.gb_edit.gb_select_mod.setMaximumWidth(200)
        self.gb_edit.gb_select_mod.setLayout(QtWidgets.QVBoxLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.gb_select_mod, 0, 0)

        # Set configs widget
        self.gb_edit.tab_modules = QtWidgets.QTabWidget(self)
        self.gb_edit.tab_modules.setLayout(QtWidgets.QGridLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.tab_modules, 0, 1, 1, 2)

        # Add all available modules
        self.module_checkboxes = dict()
        self.module_widgets = dict()
        for name, widget in self._availModules.items():

            cb = ModuleCheckbox(name)
            cb.setChecked(False)
            self.module_checkboxes[name] = cb
            self.gb_edit.gb_select_mod.layout().addWidget(self.module_checkboxes[name])

            if widget.__name__ == 'ModuleWidget':
                wdgt = widget(name, self)
            else:
                wdgt = widget(self)


            self.module_widgets[name] = wdgt
            self.gb_edit.tab_modules.addTab(self.module_widgets[name], name.upper())

        # (Debug option) Select module tab
        # self.gb_edit.tab_modules.setCurrentWidget(self.module_widgets['display'])

        # Spacer
        self.gb_edit.gb_select_mod.layout().addItem(vSpacer)

        self.btn_save_config = QtWidgets.QPushButton('Save changes')
        self.btn_save_config.clicked.connect(self.save_config)
        self.gb_edit.layout().addWidget(self.btn_save_config, 1, 1)

        self.btn_start_app = QtWidgets.QPushButton('Save and start')
        self.btn_start_app.clicked.connect(self.save_and_start_application)
        self.gb_edit.layout().addWidget(self.btn_start_app, 1, 2)

        # Update and show
        self.update_configfile_list()
        self.show()

    def update_configfile_list(self):
        self.gb_select.cb_select.clear()
        for fname in os.listdir(PATH_CONFIG):
            self.gb_select.cb_select.addItem(fname)

    def _add_configfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(PATH_CONFIG):
                with open(os.path.join(PATH_CONFIG,fname),'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self.update_configfile_list()
            self.gb_select.cb_select.setCurrentText(name)

    def open_config(self):

        name = self.gb_select.cb_select.currentText()

        if name == '':
            return

        print('Open config {}'.format(name))

        self._configfile = name
        acc.cur_conf = misc.ConfigParser()
        acc.cur_conf.read(self._configfile)

        # Set display config for visual compat.
        Config.Display = acc.cur_conf.getParsedSection(Def.DisplayCfg.name)

        # Update module selection
        for module_name, checkbox in self.module_checkboxes.items():
            use = acc.cur_conf.getParsed(module_name, Def.Cfg.use)
            checkbox.setChecked(use)
            self.module_widgets[module_name].setEnabled(use)

        # Update module settings
        for module_name, wdgt in self.module_widgets.items():
            if hasattr(wdgt, 'load_settings_from_config'):
                print('Load settings for module \"{}\" from config file'.format(module_name))
                self.sig_reload_config.emit()
            else:
                print('Could not load settings for module \"{}\" from config file'.format(module_name))

    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                acc.cur_conf.saveToFile()

        # Close widgets
        for wdgt_name, wdgt in self.module_widgets.items():
            wdgt.closed_main_window()

        # Close MainWindow
        event.accept()

    def save_config(self):
        acc.cur_conf.saveToFile()

    def save_and_start_application(self):
        acc.cur_conf.saveToFile()
        self.start_application()

    def start_application(self):
        print('Start application')
        acc.configfile = self._configfile
        self.close()
