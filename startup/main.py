from configparser import ConfigParser
import os

from PyQt5 import QtWidgets

import Def
from helper import Basic
from startup import settings
from startup.utils import ModuleWidget
from startup.camera_setup import CameraWidget
from startup.display_setup import DisplayWidget

settings.current_config = Basic.ConfigParser()

import Logging
import Config
Logging.write = lambda *args, **kwargs: None
from PyQt5 import QtWidgets

from startup import settings


class ModuleCheckbox(QtWidgets.QCheckBox):

    def __init__(self, module_name, *_args):
        QtWidgets.QCheckBox.__init__(self, module_name.upper(), *_args)
        self.module_name = module_name

        self.toggled.connect(self.react_to_toggle)

    def react_to_toggle(self, bool):
        print('Set module \"{}\" usage to {}'.format(self.text(), bool))
        settings.current_config.setParsed(self.module_name,Def.Cfg.use,bool)


class StartupConfiguration(QtWidgets.QMainWindow):

    _availModules = {Def.CameraCfg.name: CameraWidget,
                     Def.DisplayCfg.name: DisplayWidget,
                     Def.GuiCfg.name: ModuleWidget,
                     Def.IoCfg.name: ModuleWidget,
                     Def.RecCfg.name: ModuleWidget}

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self._configfile = None
        self._currentConfigChanged = False

        self.setup_ui()


    def setup_ui(self):
        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        hSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

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
        self.gb_select.cb_select.currentTextChanged.connect(self.open_configfile)
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
        ### Module selection
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

        # Spacer
        self.gb_edit.gb_select_mod.layout().addItem(vSpacer)

        self.btn_save_config = QtWidgets.QPushButton('Save changes')
        self.btn_save_config.clicked.connect(settings.current_config.saveToFile)
        self.gb_edit.layout().addWidget(self.btn_save_config, 1, 1)

        self.btn_start_app = QtWidgets.QPushButton('Save and start')
        self.btn_start_app.clicked.connect(self.save_and_start_application)
        self.gb_edit.layout().addWidget(self.btn_start_app, 1, 2)

        # Update and show
        self.update_configfile_list()
        self.show()

    def update_configfile_list(self):
        self.gb_select.cb_select.clear()
        for fname in os.listdir(Def.Path.Config):
            self.gb_select.cb_select.addItem(fname[:-4])

    def _add_configfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(Def.Path.Config):
                with open(os.path.join(Def.Path.Config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self.update_configfile_list()
            self.gb_select.cb_select.setCurrentText(name)


    def open_configfile(self):

        name = self.gb_select.cb_select.currentText()

        if name == '':
            return

        print('Open config {}'.format(name))

        self._configfile = '{}.ini'.format(name)
        settings.current_config.read(self._configfile)

        ### Set display config for visual compat.
        Config.Display = settings.current_config.getParsedSection(Def.DisplayCfg.name)

        ### Update module selection
        for module_name, checkbox in self.module_checkboxes.items():
            use = settings.current_config.getParsed(module_name,Def.Cfg.use)
            checkbox.setChecked(use)
            self.module_widgets[module_name].setEnabled(use)

        ### Update module settings
        for module_name, wdgt in self.module_widgets.items():
            if hasattr(wdgt, 'load_settings_from_config'):
                print('Load settings for module \"{}\" from config file'.format(module_name))
                wdgt.load_settings_from_config()
            else:
                print('Could not load settings for module \"{}\" from config file'.format(module_name))


    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                settings.current_config.saveToFile()

        # Close widgets
        for wdgt_name, wdgt in self.module_widgets.items():
            wdgt.closed_main_window()

        # Close MainWindow
        event.accept()

    def save_and_start_application(self):
        settings.current_config.saveToFile()
        self.start_application()

    def start_application(self):
        print('Start application')
        settings.configfile = self._configfile
        self.close()
