import configparser
from PyQt5 import QtCore, QtWidgets
import sys
from multiprocessing import Process, Pipe
import time

import MappApp_OpenGL as gl
import MappApp_Com as com
import MappApp_Stimulus as stim


class Main(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        # Set up presenter screen
        self.pipeout, self.pipein = Pipe()
        self.presenter = Process(target=gl.runPresenter,
                                 args=(self.pipein, self.pipeout),
                                 kwargs=dict())
        self.presenter.start()

        # Wait for presenter to report readyness
        print('Waiting for presenter to respond')
        obj = self.pipein.recv()
        if not(obj[0] == com.OGL.ToMain.Ready):
            print('Invalid response from presenter')
            return

        self.setupUi()

        # Send display settings to OpenGL
        self.displaySettingsUpdated()

    def setupUi(self):
        self.setGeometry(300, 300, 500, 250)
        self.setWindowTitle('MappApp')

        self.liveUpdate = True

        # Central widget
        self._widget = QtWidgets.QWidget()
        self._widget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._widget)

        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setValue(0.)
        self._dspn_x_pos.setMinimum(0.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(0.001)
        self._widget.layout().addWidget(QtWidgets.QLabel('X position'), 0, 0)
        self._widget.layout().addWidget(self._dspn_x_pos, 0, 1)

        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setValue(0.)
        self._dspn_y_pos.setMinimum(0.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(0.001)
        self._widget.layout().addWidget(QtWidgets.QLabel('Y position'), 1, 0)
        self._widget.layout().addWidget(self._dspn_y_pos, 1, 1)

        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setValue(0.)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._widget.layout().addWidget(QtWidgets.QLabel('Elevation angle'), 2, 0)
        self._widget.layout().addWidget(self._dspn_elev_angle, 2, 1)

        self._dspn_disp_size_glob = QtWidgets.QDoubleSpinBox()
        self._dspn_disp_size_glob.setDecimals(3)
        self._dspn_disp_size_glob.setValue(1.)
        self._dspn_disp_size_glob.setMinimum(0.01)
        self._dspn_disp_size_glob.setMaximum(2.0)
        self._dspn_disp_size_glob.setSingleStep(0.005)
        self._widget.layout().addWidget(QtWidgets.QLabel('Global display size'), 3, 0)
        self._widget.layout().addWidget(self._dspn_disp_size_glob, 3, 1)

        self._dspn_vp_center_dist = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_dist.setDecimals(3)
        self._dspn_vp_center_dist.setValue(0.0)
        self._dspn_vp_center_dist.setMinimum(-1.0)
        self._dspn_vp_center_dist.setMaximum(1.0)
        self._dspn_vp_center_dist.setSingleStep(0.001)
        self._widget.layout().addWidget(QtWidgets.QLabel('Center distance'), 4, 0)
        self._widget.layout().addWidget(self._dspn_vp_center_dist, 4, 1)

        self._btn_submit = QtWidgets.QPushButton('Submit')
        self._btn_submit.clicked.connect(self.displaySettingsUpdated)
        self._widget.layout().addWidget(self._btn_submit, 10, 1)

        self._btn_startStim = QtWidgets.QPushButton('Start stimulus')
        self._btn_startStim.clicked.connect(self.startStimulus)
        self._widget.layout().addWidget(self._btn_startStim, 11, 1)

        self._spn_disp_screen = QtWidgets.QSpinBox()
        self._spn_disp_screen.setValue(0)
        self._widget.layout().addWidget(QtWidgets.QLabel('Screen'), 20, 0)
        self._widget.layout().addWidget(self._spn_disp_screen, 20, 1)

        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setCheckState(QtCore.Qt.Unchecked)
        self._widget.layout().addWidget(self._check_fullscreen, 21, 1)


        if self.liveUpdate:
            # Define update timer
            self.timer_param_update = QtCore.QTimer()
            self.timer_param_update.setSingleShot(True)
            self.timer_param_update.timeout.connect(self.displaySettingsUpdated)

            # Connect events
            self._dspn_x_pos.valueChanged.connect(self.onDisplayParamChange)
            self._dspn_y_pos.valueChanged.connect(self.onDisplayParamChange)
            self._dspn_elev_angle.valueChanged.connect(self.onDisplayParamChange)
            self._dspn_disp_size_glob.valueChanged.connect(self.onDisplayParamChange)
            self._dspn_vp_center_dist.valueChanged.connect(self.onDisplayParamChange)
            self._spn_disp_screen.valueChanged.connect(self.onDisplayParamChange)
            self._check_fullscreen.stateChanged.connect(self.onDisplayParamChange)

        self.show()

    def onDisplayParamChange(self):
        self.timer_param_update.start(100)

    def displaySettingsUpdated(self, return_settings=False):

        settings = dict(
            x_pos=self._dspn_x_pos.value(),
            y_pos = self._dspn_y_pos.value(),
            elev_angle = self._dspn_elev_angle.value(),
            disp_size_glob = self._dspn_disp_size_glob.value(),
            disp_vp_center_dist = self._dspn_vp_center_dist.value(),
            disp_screen = self._spn_disp_screen.value(),
            disp_fullscreen = True if (self._check_fullscreen.checkState() == QtCore.Qt.Checked) else False
        )

        if return_settings:
            return settings

        # Send new display parameters to presenter
        obj = [com.OGL.ToOpenGL.DisplaySettings, settings]
        self.pipein.send(obj)

    def startStimulus(self):
        self.pipein.send([com.OGL.ToOpenGL.SetNewStimulus, stim.DisplayCheckerboard])

    def saveConfigurations(self):
        config = configparser.ConfigParser()
        config['Display'] = self.displaySettingsUpdated(return_settings=True)

        with open('settings.cfg', 'w') as cfgfile:
            config.write(cfgfile)


    def closeEvent(self, event):
        print('Shutting down...')
        self.pipein.send([com.OGL.ToOpenGL.Close])

        print('> Saving configurations...')
        self.saveConfigurations()

        # Close
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())