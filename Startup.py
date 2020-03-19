"""
MappApp ./Startup.py - Startup script is used for creation and
modification of program configuration files.
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
from typing import Union

from PyQt5 import QtCore, QtWidgets

import Definition
from helper import Basic

from devices.Camera import GetCamera

class StartupConfiguration(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self.configuration = Basic.Config()
        self._configfile = None
        self._currentConfigChanged = False

        self._setupUI()

    def _setupUI(self):

        ## Setup window
        self.setFixedSize(1000, 800)

        ## Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        ## Set file selection
        self.centralWidget().layout().addWidget(QtWidgets.QLabel('Select configuration file: '), 0, 0)
        self._cb_selectConfigfile = QtWidgets.QComboBox()
        self._cb_selectConfigfile.currentTextChanged.connect(self._openConfigfile)
        self.centralWidget().layout().addWidget(self._cb_selectConfigfile, 0, 1)
        self._pb_addConfigfile = QtWidgets.QPushButton('Add new configs file...')
        self._pb_addConfigfile.clicked.connect(self._addConfigfile)
        self.centralWidget().layout().addWidget(self._pb_addConfigfile, 0, 2)

        ## Set configs widget
        self._tabwdgt_config = QtWidgets.QTabWidget(self)
        self._tabwdgt_config.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self._tabwdgt_config, 1, 0, 1, 5)
        # Camera configuration
        self._wdgt_camera = CameraWidget(self)
        self._tabwdgt_config.addTab(self._wdgt_camera, 'Camera')
        # Next
        self._tabwdgt_config.addTab(QtWidgets.QWidget(self._tabwdgt_config), 'Hello2')

        self._pb_saveConfig = QtWidgets.QPushButton('Save changes')
        self._pb_saveConfig.clicked.connect(self.configuration.saveToFile)
        self.centralWidget().layout().addWidget(self._pb_saveConfig, 2, 3)

        self._pb_startApp = QtWidgets.QPushButton('Save and start')
        self._pb_startApp.clicked.connect(self._startApplication)
        self.centralWidget().layout().addWidget(self._pb_startApp, 2, 4)

        # Update and show
        self._updateConfigfileList()
        self.show()

    def _updateConfigfileList(self):
        self._cb_selectConfigfile.clear()
        for fname in os.listdir(Definition.Path.Config):
            self._cb_selectConfigfile.addItem(fname[:-4])

    def _addConfigfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(Definition.Path.Config):
                with open(os.path.join(Definition.Path.Config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self._updateConfigfileList()
            self._cb_selectConfigfile.setCurrentText(name)


    def _openConfigfile(self):

        name = self._cb_selectConfigfile.currentText()
        if name == '':
            return

        self._configfile = '%s.ini' % name
        self.configuration = Basic.Config(self._configfile)


    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                self.configuration.saveToFile()

        event.accept()


    def _startApplication(self):
        self.configuration.saveToFile()
        global _configfile
        _configfile = self._configfile
        self.close()

from devices import Camera
class CameraWidget(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Enabled')

        self.setCheckable(True)
        self.setLayout(QtWidgets.QHBoxLayout())

        self._vbox_cameras = QtWidgets.QWidget()
        self._vbox_cameras.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self._vbox_cameras)

        self._listw_cameras = QtWidgets.QListWidget()
        self._vbox_cameras.layout().addWidget(QtWidgets.QLabel('Camera types'))
        self._vbox_cameras.layout().addWidget(self._listw_cameras)
        for name in Camera.__dict__:
            if name.startswith('CAM_'):
                self._listw_cameras.addItem(name)


if __name__ == '__main__':

    _configfile = None
    app = QtWidgets.QApplication([])
    window = StartupConfiguration()
    app.exec_()

    if _configfile is None:
        exit()

    import Controller
    Controller.Controller()