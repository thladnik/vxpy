import configparser
from PyQt5 import QtCore, QtWidgets
import sys
from multiprocessing import Process, Pipe

import MappApp_Output as out
import MappApp_Com as com
import MappApp_Stimulus as stim
from MappApp_Widgets import *


class Main(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up presenter screen
        self.pipeout, self.pipein = Pipe()
        self.presenter = Process(target=out.runPresenter, args=(self.pipein, self.pipeout), kwargs=dict())
        self.presenter.start()

        # Wait for presenter to report readyness
        print('Waiting for presenter to respond...')
        if self.pipein.poll(timeout=5.):
            obj = self.pipein.recv()
            if obj[0] == com.Display.ToMain.Ready:
                print('Presenter is ready.')
            else:
                self.pipein.send([com.Display.ToDisplay.Close])
                print('Invalid response from presenter. EXIT')
                self.close()
                return

        # Setup user interface
        self.setupUi()

        # Load configurations
        self.loadConfiguration()

        # Last: Send display settings to OpenGL
        self.displaySettingsUpdated()


    def setupUi(self):
        self.setGeometry(300, 300, 500, 250)
        self.setWindowTitle('MappApp')

        self.liveUpdate = True

        # Central widget
        self._centralwidget = QtWidgets.QWidget()
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        self.dispSettings = DisplaySettings(self)
        self._centralwidget.layout().addWidget(self.dispSettings, 0, 0)

        # Display checkerboard
        self.checkerboardDisp = CheckerboardCalibration(self)
        self._centralwidget.layout().addWidget(self.checkerboardDisp, 1, 0)

        # Display moving grating
        self._btn_displayMovGrating = QtWidgets.QPushButton('Display moving grating')
        self._btn_displayMovGrating.clicked.connect(self.displayMovGrating)
        self._centralwidget.layout().addWidget(self._btn_displayMovGrating, 2, 0)

        if self.liveUpdate:
            # Define update timer
            self.timer_param_update = QtCore.QTimer()
            self.timer_param_update.setSingleShot(True)
            self.timer_param_update.timeout.connect(self.displaySettingsUpdated)

            # Connect events
            self.dispSettings._dspn_x_pos.valueChanged.connect(self.onDisplayParamChange)
            self.dispSettings._dspn_y_pos.valueChanged.connect(self.onDisplayParamChange)
            self.dispSettings._dspn_elev_angle.valueChanged.connect(self.onDisplayParamChange)
            self.dispSettings._dspn_glob_disp_size.valueChanged.connect(self.onDisplayParamChange)
            self.dispSettings._dspn_vp_center_dist.valueChanged.connect(self.onDisplayParamChange)
            self.dispSettings._check_fullscreen.stateChanged.connect(self.onDisplayParamChange)

        self.show()

    def onDisplayParamChange(self):
        self.timer_param_update.start(100)

    def displaySettingsUpdated(self, return_settings=False):

        settings = {
            com.Display.Settings.glob_x_pos           : self.dispSettings._dspn_x_pos.value(),
            com.Display.Settings.glob_y_pos           : self.dispSettings._dspn_y_pos.value(),
            com.Display.Settings.elev_angle           : self.dispSettings._dspn_elev_angle.value(),
            com.Display.Settings.glob_disp_size       : self.dispSettings._dspn_glob_disp_size.value(),
            com.Display.Settings.vp_center_dist       : self.dispSettings._dspn_vp_center_dist.value(),
            com.Display.Settings.disp_screen_id       : self.dispSettings._spn_screen_id.value(),
            com.Display.Settings.disp_fullscreen      : True if (self.dispSettings._check_fullscreen.checkState() == QtCore.Qt.Checked)
                                   else False
        }

        if return_settings:
            return settings

        # Send new display parameters to presenter
        obj = [com.Display.ToDisplay.NewSettings, settings]
        self.pipein.send(obj)


    def displayMovGrating(self):
        self.pipein.send([com.Display.ToDisplay.SetNewStimulus, stim.DisplayGrating])

    def saveConfiguration(self):
        config = configparser.ConfigParser()
        config['DisplaySettings'] = self.displaySettingsUpdated(return_settings=True)

        with open('settings.cfg', 'w') as cfgfile:
            config.write(cfgfile)
        print('Config saved.')

    def loadConfiguration(self):
        config = configparser.ConfigParser()
        config.read('settings.cfg',)

        if len(config.sections()) == 0:
            print('No config file found')
            return

        # Set display settings
        print('Loading display settings from config')
        disp_settings = config['DisplaySettings']
        self.dispSettings._dspn_x_pos.setValue(float(disp_settings[com.Display.Settings.glob_x_pos]))
        self.dispSettings._dspn_y_pos.setValue(float(disp_settings[com.Display.Settings.glob_y_pos]))
        self.dispSettings._dspn_elev_angle.setValue(float(disp_settings[com.Display.Settings.glob_x_pos]))
        self.dispSettings._dspn_glob_disp_size.setValue(float(disp_settings[com.Display.Settings.glob_disp_size]))
        self.dispSettings._dspn_vp_center_dist.setValue(float(disp_settings[com.Display.Settings.vp_center_dist]))
        self.dispSettings._spn_screen_id.setValue(int(disp_settings[com.Display.Settings.disp_screen_id]))
        self.dispSettings._check_fullscreen.setCheckState(True
                                                          if disp_settings[com.Display.Settings.disp_fullscreen] == 'True'
                                                          else False)

    def closeEvent(self, event):
        print('Shutting down...')
        self.pipein.send([com.Display.ToDisplay.Close])

        print('> Saving config...')
        self.saveConfiguration()

        # Close
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())