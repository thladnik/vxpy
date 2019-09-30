import configparser
from PyQt5 import QtCore, QtWidgets
import sys
from multiprocessing import Process, Pipe
import time


from MappApp_Widgets import *
from MappApp_Control import Controller
import MappApp_Definition as madef


class Main(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create controller instance
        self.ctrl = Controller()

        # Setup user interface
        print('Setting up UI...')
        self.setupUi()

        # Wrap controller methods
        self._wrapController()

        # By default: show checkerboard
        self.checkerboardDisp.displayCheckerboard()


    def _wrapController(self):
        """
        Add optional wrappers for controller methods
        :return:
        """
        pass


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
        #self._btn_displayMovGrating.clicked.connect(self.displayMovGrating)
        self._centralwidget.layout().addWidget(self._btn_displayMovGrating, 2, 0)

        # Define update timer
        self.timer_param_update = QtCore.QTimer()
        self.timer_param_update.setSingleShot(True)
        self.timer_param_update.timeout.connect(self.displaySettingsChanged)

        # Connect events
        self.dispSettings._dspn_x_pos.valueChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._dspn_y_pos.valueChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._dspn_elev_angle.valueChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._dspn_view_axis_offset.valueChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._dspn_vp_center_offset.valueChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._check_fullscreen.stateChanged.connect(self.onDisplaySettingChange)
        self.dispSettings._dspn_fov.valueChanged.connect(self.onDisplaySettingChange)

        # Show window
        self.show()

    def _convCheckstateToBool(self, checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False

    def _convBoolToCheckstate(self, bool):
        return QtCore.Qt.Checked if bool else QtCore.Qt.Unchecked

    def onDisplaySettingChange(self):
        self.timer_param_update.start(100)

    def displaySettingsChanged(self):

        self.ctrl.updateDisplaySettings(**{
            madef.DisplaySettings.float_glob_x_pos           : self.dispSettings._dspn_x_pos.value(),
            madef.DisplaySettings.float_glob_y_pos           : self.dispSettings._dspn_y_pos.value(),
            madef.DisplaySettings.float_elev_angle           : self.dispSettings._dspn_elev_angle.value(),
            madef.DisplaySettings.float_view_axis_offset     : self.dispSettings._dspn_view_axis_offset.value(),
            madef.DisplaySettings.float_vp_center_offset     : self.dispSettings._dspn_vp_center_offset.value(),
            madef.DisplaySettings.float_vp_fov               : self.dispSettings._dspn_fov.value(),
            madef.DisplaySettings.int_disp_screen_id         : self.dispSettings._spn_screen_id.value(),
            madef.DisplaySettings.bool_disp_fullscreen       : self._convCheckstateToBool(
                self.dispSettings._check_fullscreen.checkState() == QtCore.Qt.Checked)
        })


    def closeEvent(self, event):
        self.ctrl.terminate()
        # Close
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())