from PyQt5 import QtCore, QtWidgets
import sys


from MappApp_Widgets import *
from MappApp_Control import Controller
import MappApp_Definition as madef
import MappApp_Helper as mahlp

import IPython

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
        self.checkerboardCalibration.displayCheckerboard()


    def _wrapController(self):
        """
        Add optional wrappers for controller methods
        :return:
        """
        pass


    def setupUi(self):

        ## Setup MainWindow
        self.setWindowTitle('MappApp')
        self.move(0, 0)
        self.setFixedSize(800, 100)
        self.show()

        geo = self.window().geometry()

        ## Setup central widget
        self._centralwidget = QtWidgets.QWidget(parent=self, flags=Qt.Widget)
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        ## Setup display settings widget
        self.dispSettings = DisplaySettings(self)
        self.dispSettings.setMinimumSize(300, 300)
        self._openDisplaySettings()
        self.dispSettings.move(geo.x(), geo.y()+geo.height())

        geo_disp = self.dispSettings.window().geometry()

        ## Setup checkerboard calibration
        self.checkerboardCalibration = CheckerboardCalibration(self)
        self.checkerboardCalibration.setMinimumSize(300, 100)
        self._openCheckerboardCalibration()
        self.checkerboardCalibration.move(geo.x(), geo_disp.y()+geo_disp.height())

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


    def _openDisplaySettings(self):
        self.dispSettings.show()

    def _openCheckerboardCalibration(self):
        self.checkerboardCalibration.show()

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
            madef.DisplaySettings.bool_disp_fullscreen       : mahlp.Conversion.QtCheckstateToBool(
                self.dispSettings._check_fullscreen.checkState())
        })


    def closeEvent(self, QCloseEvent):
        # Terminate controller instance
        self.ctrl.terminate()
        # Close widgets
        self.dispSettings.close()
        self.checkerboardCalibration.close()
        # Close MainWindow
        QCloseEvent.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())