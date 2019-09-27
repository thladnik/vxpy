import configparser
from PyQt5 import QtCore, QtWidgets
import sys
from multiprocessing import Process, Pipe
import time

import MappApp_Output as maout
import MappApp_Com as macom
import MappApp_Stimulus as stim
from MappApp_Widgets import *
import MappApp_Definition as madef


class Main(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ### Set up IPC
        ipc = macom.IPC()
        ## Main listener
        ipc.registerConnection('main', 'display')
        #ipc.registerConnection('main', 'io')
        # Save to file
        ipc.saveToFile()

        # Set up presenter screen
        print('Starting display...')
        self.display = Process(name='Display', target=maout.runDisplay)
        self.display.start()

        print('Starting IO...')
        self.io = Process(name='IO', target=maout.runIO)
        #self.io.start()

        # Set up listener
        self.listener = ipc.getMetaListener('main')
        self.listener.acceptClients()

        # Setup user interface
        print('Setting up UI...')
        self.setupUi()

        # Map relations
        self.mapRelations()

        # Load configurations
        print('Load config...')
        self.loadConfiguration()

        # By default: show checkerboard
        self.checkerboardDisp.displayCheckerboard()

        # Last: Send display settings to OpenGL
        print('Updating display params...')
        self.displaySettingsUpdated()

    def setupUi(self):
        self.setGeometry(300, 300, 500, 250)
        self.setWindowTitle('MappApp')

        # Central widget
        self._centralwidget = QtWidgets.QWidget(self)
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

        # Define update timer
        self.timer_param_update = QtCore.QTimer()
        self.timer_param_update.setSingleShot(True)
        self.timer_param_update.timeout.connect(self.displaySettingsUpdated)

        # Connect events
        self.dispSettings._dspn_x_pos.valueChanged.connect(self.onDisplayParamChange)
        self.dispSettings._dspn_y_pos.valueChanged.connect(self.onDisplayParamChange)
        self.dispSettings._dspn_elev_angle.valueChanged.connect(self.onDisplayParamChange)
        self.dispSettings._dspn_vp_center_dist.valueChanged.connect(self.onDisplayParamChange)
        self.dispSettings._check_fullscreen.stateChanged.connect(self.onDisplayParamChange)
        self.dispSettings._dspn_fov.valueChanged.connect(self.onDisplayParamChange)

        # Show window
        self.show()

    def _convCheckstateToBool(self, checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False

    def _convBoolToCheckstate(self, bool):
        return QtCore.Qt.Checked if bool else QtCore.Qt.Unchecked

    def mapRelations(self):
        return
        self.mapDisplaySettings = [
            (madef.DisplaySettings.float_glob_x_pos,      self.dispSettings._dspn_x_pos.value,
             self.dispSettings._dspn_x_pos.setValue),
            (madef.DisplaySettings.float_glob_y_pos,      self.dispSettings._dspn_y_pos.value,
             self.dispSettings._dspn_y_pos.setValue),
            (madef.DisplaySettings.float_elev_angle,      self.dispSettings._dspn_elev_angle.value,
             self.dispSettings._dspn_elev_angle.setValue),
            (madef.DisplaySettings.float_vp_center_dist,  self.dispSettings._dspn_vp_center_dist.value,
             self.dispSettings._dspn_vp_center_dist.setValue),
            (madef.DisplaySettings.float_vp_fov,          self.dispSettings._dspn_fov.value,
             self.dispSettings._dspn_fov.setValue),
            (madef.DisplaySettings.int_disp_screen_id,    self.dispSettings._spn_screen_id.value,
             self.dispSettings._spn_screen_id.setValue),
            (madef.DisplaySettings.bool_disp_fullscreen,
            lambda: self._convCheckstateToBool(self.dispSettings._check_fullscreen.checkState()),
            lambda: self.dispSettings._check_fullscreen.setCheckState(self._convBoolToCheckstate()))
        ]

    def onDisplayParamChange(self):
        self.timer_param_update.start(100)

    def displaySettingsUpdated(self, return_settings=False):

        settings = {
            madef.DisplaySettings.float_glob_x_pos           : self.dispSettings._dspn_x_pos.value(),
            madef.DisplaySettings.float_glob_y_pos           : self.dispSettings._dspn_y_pos.value(),
            madef.DisplaySettings.float_elev_angle           : self.dispSettings._dspn_elev_angle.value(),
            madef.DisplaySettings.float_vp_center_dist       : self.dispSettings._dspn_vp_center_dist.value(),
            madef.DisplaySettings.float_vp_fov               : self.dispSettings._dspn_fov.value(),
            madef.DisplaySettings.int_disp_screen_id         : self.dispSettings._spn_screen_id.value(),
            madef.DisplaySettings.bool_disp_fullscreen       :
                True
                if (self.dispSettings._check_fullscreen.checkState() == QtCore.Qt.Checked)
                else False
        }
        #settings = {option[0] : self.mapDisplaySettings[option[1]] for option in self.mapDisplaySettings}

        if return_settings:
            return settings

        # Send new display parameters to display
        obj = [macom.Display.Code.NewDisplaySettings, settings]
        self.listener.connections['display'].send(obj)


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
        self.dispSettings._dspn_x_pos.setValue(float(disp_settings[madef.DisplaySettings.float_glob_x_pos]))
        self.dispSettings._dspn_y_pos.setValue(float(disp_settings[madef.DisplaySettings.float_glob_y_pos]))
        self.dispSettings._dspn_elev_angle.setValue(float(disp_settings[madef.DisplaySettings.float_elev_angle]))
        self.dispSettings._dspn_vp_center_dist.setValue(float(disp_settings[madef.DisplaySettings.float_vp_center_dist]))
        self.dispSettings._spn_screen_id.setValue(int(disp_settings[madef.DisplaySettings.int_disp_screen_id]))
        self.dispSettings._check_fullscreen.setCheckState(QtCore.Qt.Checked
                                                          if disp_settings[madef.DisplaySettings.bool_disp_fullscreen] == 'True'
                                                          else QtCore.Qt.Unchecked)

    def closeEvent(self, event):
        print('Shutting down...')
        self.listener.connections['display'].send([macom.Display.Code.Close])

        print('> Saving config...')
        self.saveConfiguration()

        # Close
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())