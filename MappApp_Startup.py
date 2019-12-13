from configparser import ConfigParser
import os

import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import MappApp_Defaults as madflt
import MappApp_Definition as madef


class StartupConfiguration(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self._parser = None
        self._configfile = None

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
        self._pb_addConfigfile = QtWidgets.QPushButton('Add new config file...')
        self._pb_addConfigfile.clicked.connect(self._addConfigfile)
        self.centralWidget().layout().addWidget(self._pb_addConfigfile, 0, 2)

        ## Set config widget
        self._wdgt_config = QtWidgets.QWidget(self)
        self._wdgt_config.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self._wdgt_config, 1, 0, 1, 2)
        # Camera configuration
        self._gb_camera = CameraConfiguration()
        self._wdgt_config.layout().addWidget(self._gb_camera, 0, 0)

        self._pb_startApp = QtWidgets.QPushButton('Start')
        self._pb_startApp.clicked.connect(self._startApplication)
        self.centralWidget().layout().addWidget(self._pb_startApp, 2, 2)

        # Update and show
        self._updateConfigfileList()
        self.show()

    def _updateConfigfileList(self):
        self._cb_selectConfigfile.clear()
        for fname in os.listdir(madef.Path.config):
            self._cb_selectConfigfile.addItem(fname[:-4])

    def _addConfigfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new config file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(madef.Path.config):
                with open(os.path.join(madef.Path.config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self._updateConfigfileList()
            self._cb_selectConfigfile.setCurrentText(name)

    def _saveToFile(self):
        if self._parser is not None and self._configfile is not None:
            with open(os.path.join(madef.Path.config, self._configfile), 'w') as fobj:
                # Camera configuration
                self._parser['camera'] = self._gb_camera.get()

                # Display configuration
                displayConfig = madflt.DisplayConfiguration
                if self._parser.has_section('display'):
                    displayConfig = self._parser['display']
                self._parser['display'] = displayConfig

                self._parser.write(fobj)

    def _openConfigfile(self):

        if self._parser is not None and self._configfile is not None:
            self._saveToFile()

        name = self._cb_selectConfigfile.currentText()
        if name == '':
            return

        self._configfile = '%s.ini' % name
        self._parser = ConfigParser()
        self._parser.read(os.path.join(madef.Path.config, self._configfile))

        # Set camera
        _cameraConfig = dict()
        if self._parser.has_section('camera'):
            _cameraConfig = {prop : val for (prop, val) in self._parser['camera'].items()}
        self._gb_camera.set(**_cameraConfig)

        # Set ...

    def closeEvent(self, event):
        self._saveToFile()
        event.accept()

    def _startApplication(self):
        global _configfile
        _configfile = self._configfile
        self.close()


import devices.cameras.tisgrabber as IC
class CameraConfiguration(QtWidgets.QGroupBox):

    def __init__(self):
        QtWidgets.QGroupBox.__init__(self, 'Camera configuration')

        self._setupUI()

    def _setupUI(self):

        self._type = None
        self._camera = None

        self.setFixedSize(400, 150)

        self.setLayout(QtWidgets.QGridLayout())

        self._cb_selectModel = QtWidgets.QComboBox()
        self._cb_selectModel.currentTextChanged.connect(self._cameraSelected)
        self.layout().addWidget(QtWidgets.QLabel('Camera'), 0, 0)
        self.layout().addWidget(self._cb_selectModel, 0, 1)
        self._cb_selectFormat = QtWidgets.QComboBox()
        self.layout().addWidget(QtWidgets.QLabel('Format'), 1, 0)
        self.layout().addWidget(self._cb_selectFormat, 1, 1)

    def _loadCameraList(self):
        self._cb_selectModel.clear()

        # The Imaging Source
        camera = IC.TIS_CAM()
        for c in camera.GetDevices():
            self._cb_selectModel.addItem('TIS>>%s' % c.decode())

    def _loadFormatList(self):
        self._cb_selectFormat.clear()
        if self._type is not None and self._type == 'TIS':
            for f in self._camera.GetVideoFormats():
                self._cb_selectFormat.addItem(f.decode())

    def _cameraSelected(self):
        selection = self._cb_selectModel.currentText().split('>>')

        self._type = None
        self._camera = None
        if selection[0] == 'TIS':
            self._type = selection[0]
            self._camera = IC.TIS_CAM()
            self._camera.open(selection[1])

        if self._camera is None:
            print('ERROR: problem selecting camera')
            return

        self._loadFormatList()

    def set(self, model=None, format=None, **kwargs):
        self._loadCameraList()

        if model is not None:
            self._cb_selectModel.setCurrentText(model)

        if format is not None:
            self._cb_selectFormat.setCurrentText(format)


    def get(self):
        format = self._cb_selectFormat.currentText()
        format1 = format.split(' ')[-1].split('x')

        camera = self._cb_selectModel.currentText().split('>>')
        manufacturer = camera[0]
        model = camera[1]

        return dict(
            manufacturer=manufacturer,
            model=model,
            format=format,
            resolution_x=int(format1[1][:-1]),
            resolution_y=int(format1[0][1:])
        )


if __name__ == '__main__':

    _configfile = None
    app = QtWidgets.QApplication([])
    window = StartupConfiguration()
    app.exec_()

    if _configfile is not None:

        import IPython
        #IPython.embed()
        from MappApp_Controller import runController
        _useGUI = True
        runController(_configfile, _useGUI)