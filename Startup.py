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

from PyQt5 import QtWidgets

import Definition
from helper import Basic

from devices.cameras.virtual import VirtualCamera

class StartupConfiguration(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self.configuration = None
        self._configfile = None
        self._currentConfigChanged = False

        self._setupUI()

    def _setupUI(self):

        ## Setup window
        self.resize(600, 300)

        ## Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QGridLayout())

        ## Set file selection
        self.centralWidget().layout().addWidget(QtWidgets.QLabel('Select configuration file: '))
        self._cb_selectConfigfile = QtWidgets.QComboBox()
        self._cb_selectConfigfile.currentTextChanged.connect(self._openConfigfile)
        self.centralWidget().layout().addWidget(self._cb_selectConfigfile, 0, 1)
        self._pb_addConfigfile = QtWidgets.QPushButton('Add new configs file...')
        self._pb_addConfigfile.clicked.connect(self._addConfigfile)
        self.centralWidget().layout().addWidget(self._pb_addConfigfile, 0, 2)

        ## Set configs widget
        self._wdgt_config = QtWidgets.QWidget(self)
        self._wdgt_config.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self._wdgt_config, 1, 0, 1, 2)
        # Camera configuration
        self._gb_camera = CameraConfiguration(self)
        self._wdgt_config.layout().addWidget(self._gb_camera, 0, 0)

        self._pb_saveConfig = QtWidgets.QPushButton('Save changes')
        self._pb_saveConfig.clicked.connect(self._saveToFile)
        self.centralWidget().layout().addWidget(self._pb_saveConfig, 1, 2)

        self._pb_startApp = QtWidgets.QPushButton('Save and start')
        self._pb_startApp.clicked.connect(self._startApplication)
        self.centralWidget().layout().addWidget(self._pb_startApp, 2, 2)

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

    def _saveToFile(self):
        if self.configuration is None or self._configfile is None:
            return
        print('Saving changes to file')
        # Camera configuration
        self.configuration.updateConfiguration(Definition.Camera, **self._gb_camera.get())

        # Display configuration
        self.configuration.updateConfiguration(Definition.Display)

        # Gui configuration
        self.configuration.updateConfiguration(Definition.Gui)

        self.configuration.saveToFile()
        self._currentConfigChanged = False


    def _openConfigfile(self):

        name = self._cb_selectConfigfile.currentText()
        if name == '':
            return

        self._configfile = '%s.ini' % name
        self.configuration = Basic.Config(self._configfile)

        # Set camera configuration
        self._gb_camera._loadCameraList()
        self._gb_camera.set(**self.configuration.configuration(Definition.Camera))

        # Set ...

    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes:
                self._saveToFile()

        event.accept()


    def _startApplication(self):
        self._saveToFile()
        global _configfile
        _configfile = self._configfile
        self.close()


import lib.pyapi.tisgrabber as IC
class CameraConfiguration(QtWidgets.QGroupBox):

    def __init__(self, _main):
        self._main = _main
        QtWidgets.QGroupBox.__init__(self, 'Camera configuration')

        self._setupUI()

    def _setupUI(self):

        self._manufacturer = None
        self._camera = None

        self.setFixedSize(400, 150)

        self.setLayout(QtWidgets.QGridLayout())

        self._cb_selectModel = QtWidgets.QComboBox()
        self._cb_selectModel.activated.connect(self._cameraSelected)
        self.layout().addWidget(QtWidgets.QLabel('Camera'), 0, 0)
        self.layout().addWidget(self._cb_selectModel, 0, 1)

        self._cb_selectFormat = QtWidgets.QComboBox()
        self.layout().addWidget(QtWidgets.QLabel('Format'), 1, 0)
        self._cb_selectFormat.activated.connect(self._formatSelected)
        self.layout().addWidget(self._cb_selectFormat, 1, 1)

    def _loadCameraList(self):
        self._cb_selectModel.clear()

        # Virtual camera
        for c in VirtualCamera.getModels():
            self._cb_selectModel.addItem('virtual>>{}'.format(c))

        # The Imaging Source
        camera = IC.TIS_CAM()
        for c in camera.GetDevices():
            self._cb_selectModel.addItem('TIS>>{}'.format(c.decode()))

        # Select current
        config = self._main.configuration.configuration(Definition.Camera)
        self._cb_selectModel.setCurrentText(
            '%s>>%s' % (config[Definition.Camera.manufacturer], config[Definition.Camera.model]))

        self._loadFormatList()

    def _cameraSelected(self, idx):
        manufacturer, model = self._cb_selectModel.currentText().split('>>')

        self._manufacturer = manufacturer
        self._camera : Union[IC.TIS_CAM, VirtualCamera]

        if manufacturer == 'virtual':
            self._camera = VirtualCamera()

        elif manufacturer == 'TIS':
            self._camera = IC.TIS_CAM()
            self._camera.open(model)

        print('Changed camera to %s' % self._cb_selectModel.currentText())

        self._main._currentConfigChanged = True
        self._loadFormatList()

    def _loadFormatList(self):
        self._cb_selectFormat.clear()
        if self._manufacturer is None:
            return
        if self._manufacturer == 'virtual':
            for f in self._camera.getFormats():
                self._cb_selectFormat.addItem(f)
        elif self._manufacturer == 'TIS':
            for f in self._camera.GetVideoFormats():
                self._cb_selectFormat.addItem(f.decode())

        self._cb_selectFormat.setCurrentText(self._main.configuration.configuration(
            Definition.Camera, Definition.Camera.format)
        )

    def _formatSelected(self, idx):
        self._main._currentConfigChanged = True
        print('Changed format to %s' % self._cb_selectFormat.currentText())

    def set(self, **settings):
        self._loadCameraList()

        if Definition.Camera.model in settings:
            self._cb_selectModel.setCurrentText(settings[Definition.Camera.model])

        if Definition.Camera.format in settings:
            self._cb_selectModel.setCurrentText(settings[Definition.Camera.format])

    def get(self):
        format = self._cb_selectFormat.currentText()
        format1 = format.split(' ')[-1].split('x')

        camera = self._cb_selectModel.currentText().split('>>')
        manufacturer = camera[0]
        model = camera[1]

        return {
            Definition.Camera.manufacturer : manufacturer,
            Definition.Camera.model        : model,
            Definition.Camera.format       : format,
            Definition.Camera.res_y : int(format1[1][:-1]),
            Definition.Camera.res_x : int(format1[0][1:])
        }


if __name__ == '__main__':

    _configfile = None
    app = QtWidgets.QApplication([])
    window = StartupConfiguration()
    app.exec_()

    if _configfile is not None:

        import Controller
        _useGUI = True
        Controller.Controller(_configfile, _useGUI)