import configparser
from PyQt5 import QtCore, QtWidgets
import sys
from multiprocessing import Process, Pipe
from multiprocessing.connection import Client, Listener

import MappApp_Output as maout
import MappApp_Com as macom
import MappApp_Stimulus as stim
from MappApp_Widgets import *
import MappApp_Definition as madef


class Main(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up presenter screen
        print('Starting presenter...')
        self.presenter = Process(name='Presenter', target=maout.runPresenter)
        self.presenter.start()

        self.displayClient = macom.Display.Client()
        self.presenterClient = macom.Presenter.Client()

        # Wait for presenter to report readyness
        if False:
            print('Waiting for presenter to respond...')
            if self.pipein.poll(timeout=5.):
                obj = self.pipein.recv()
                if obj[0] == macom.ToMain.Ready:
                    print('Presenter is ready.')
                else:
                    self.pipein.send([macom.ToDisplay.Close])
                    print('Invalid response from presenter. EXIT')
                    self.close()
                    return

        # Setup user interface
        print('Setting up UI...')
        self.setupUi()

        # Load configurations
        print('Load config...')
        self.loadConfiguration()

        # Last: Send display settings to OpenGL
        print('Updating display params...')
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
            madef.DisplaySettings.glob_x_pos           : self.dispSettings._dspn_x_pos.value(),
            madef.DisplaySettings.glob_y_pos           : self.dispSettings._dspn_y_pos.value(),
            madef.DisplaySettings.elev_angle           : self.dispSettings._dspn_elev_angle.value(),
            madef.DisplaySettings.glob_disp_size       : self.dispSettings._dspn_glob_disp_size.value(),
            madef.DisplaySettings.vp_center_dist       : self.dispSettings._dspn_vp_center_dist.value(),
            madef.DisplaySettings.disp_screen_id       : self.dispSettings._spn_screen_id.value(),
            madef.DisplaySettings.disp_fullscreen      : True if (self.dispSettings._check_fullscreen.checkState() == QtCore.Qt.Checked)
                                   else False
        }

        if return_settings:
            return settings

        # Send new display parameters to presenter
        obj = [macom.Display.Code.NewSettings, settings]
        self.displayClient.send(obj)


    def displayMovGrating(self):
        self.displayClient.send([macom.Display.Code.SetNewStimulus, stim.DisplayGrating])

    def saveConfiguration(self):
        config = configparser.ConfigParser()
        config['DisplaySettings'] = self.displaySettingsUpdated(return_settings=True)

        with open('settings.cfg', 'w') as cfgfile:
            config.write(cfgfile)
        print('Config saved.')

    def loadConfiguration(self):
        config = configparser.ConfigParser()
        config.read('settings.cfg')

        if len(config.sections()) == 0:
            print('No config file found')
            return

        # Set display settings
        print('Loading display settings from config')
        disp_settings = config['DisplaySettings']
        self.dispSettings._dspn_x_pos.setValue(float(disp_settings[madef.DisplaySettings.glob_x_pos]))
        self.dispSettings._dspn_y_pos.setValue(float(disp_settings[madef.DisplaySettings.glob_y_pos]))
        self.dispSettings._dspn_elev_angle.setValue(float(disp_settings[madef.DisplaySettings.glob_x_pos]))
        self.dispSettings._dspn_glob_disp_size.setValue(float(disp_settings[madef.DisplaySettings.glob_disp_size]))
        self.dispSettings._dspn_vp_center_dist.setValue(float(disp_settings[madef.DisplaySettings.vp_center_dist]))
        self.dispSettings._spn_screen_id.setValue(int(disp_settings[madef.DisplaySettings.disp_screen_id]))
        self.dispSettings._check_fullscreen.setCheckState(True
                                                          if disp_settings[madef.DisplaySettings.disp_fullscreen] == 'True'
                                                          else False)

    def closeEvent(self, event):
        print('Shutting down...')
        self.presenterClient.conn.send([macom.Presenter.Code.Close])
        #self.displayClient.conn.send([macom.Display.Code.Close])

        print('> Saving config...')
        self.saveConfiguration()

        # Close
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())