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
        self._wgt_checkerboardCalibration.displayCheckerboard()


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
        self.setFixedSize(800, 30)
        self.show()
        geo = self.window().geometry()

        ## Setup central widget
        self._centralwidget = QtWidgets.QWidget(parent=self, flags=Qt.Widget)
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        ## Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        # Menu windows
        self._menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self._menu_windows)
        self._menu_act_dispSettings = QtWidgets.QAction('Display settings')
        self._menu_act_dispSettings.triggered.connect(self._openDisplaySettings)
        self._menu_windows.addAction(self._menu_act_dispSettings)
        self._menu_act_checkerCalib = QtWidgets.QAction('Checkerboard calibration')
        self._menu_act_checkerCalib.triggered.connect(self._openCheckerboardCalibration)
        self._menu_windows.addAction(self._menu_act_checkerCalib)
        self._menu_act_testStimuli = QtWidgets.QAction('Test stimuli')
        self._menu_act_testStimuli.triggered.connect(self._openTestStimuli)
        self._menu_windows.addAction(self._menu_act_testStimuli)


        ## Setup display settings widget
        self._wgt_dispSettings = DisplaySettings(self)
        self._wgt_dispSettings.setMinimumSize(300, 300)
        self._openDisplaySettings()
        self._wgt_dispSettings.move(geo.x(), geo.y() + geo.height())
        geo_disp = self._wgt_dispSettings.window().geometry()

        ## Setup checkerboard calibration
        self._wgt_checkerboardCalibration = CheckerboardCalibration(self)
        self._wgt_checkerboardCalibration.setMinimumSize(300, 100)
        self._openCheckerboardCalibration()
        self._wgt_checkerboardCalibration.move(geo.x(), geo_disp.y() + geo_disp.height())
        geo_checker = self._wgt_checkerboardCalibration.window().geometry()

        ## Setup test stimuli
        self._wgt_testStimuli = TestStimuli(self)
        self._wgt_testStimuli.setMinimumSize(300, 100)
        self._openTestStimuli()
        self._wgt_testStimuli.move(geo.x(), geo_checker.y() + geo_checker.height())
        geo_teststim = self._wgt_testStimuli.window().geometry()

        # Define update timer
        self.timer_param_update = QtCore.QTimer()
        self.timer_param_update.setSingleShot(True)
        self.timer_param_update.timeout.connect(self.displaySettingsChanged)

        # Connect events
        self._wgt_dispSettings._dspn_x_pos.valueChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._dspn_y_pos.valueChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._dspn_elev_angle.valueChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._dspn_view_axis_offset.valueChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._dspn_vp_center_offset.valueChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._check_fullscreen.stateChanged.connect(self.onDisplaySettingChange)
        self._wgt_dispSettings._dspn_fov.valueChanged.connect(self.onDisplaySettingChange)

    def _openDisplaySettings(self):
        self._wgt_dispSettings.showNormal()
        self._wgt_dispSettings.show()

    def _openCheckerboardCalibration(self):
        self._wgt_checkerboardCalibration.showNormal()
        self._wgt_checkerboardCalibration.show()

    def _openTestStimuli(self):
        self._wgt_testStimuli.showNormal()
        self._wgt_testStimuli.show()

    def onDisplaySettingChange(self):
        self.timer_param_update.start(100)

    def displaySettingsChanged(self):

        self.ctrl.updateDisplaySettings(**{

            madef.DisplaySettings.float_glob_x_pos           : self._wgt_dispSettings._dspn_x_pos.value(),
            madef.DisplaySettings.float_glob_y_pos           : self._wgt_dispSettings._dspn_y_pos.value(),
            madef.DisplaySettings.float_elev_angle           : self._wgt_dispSettings._dspn_elev_angle.value(),
            madef.DisplaySettings.float_view_axis_offset     : self._wgt_dispSettings._dspn_view_axis_offset.value(),
            madef.DisplaySettings.float_vp_center_offset     : self._wgt_dispSettings._dspn_vp_center_offset.value(),
            madef.DisplaySettings.float_vp_fov               : self._wgt_dispSettings._dspn_fov.value(),
            madef.DisplaySettings.int_disp_screen_id         : self._wgt_dispSettings._spn_screen_id.value(),
            madef.DisplaySettings.bool_disp_fullscreen       : mahlp.Conversion.QtCheckstateToBool(
                self._wgt_dispSettings._check_fullscreen.checkState())
        })


    def closeEvent(self, QCloseEvent):
        # Terminate controller instance
        self.ctrl.terminate()
        # Close widgets
        self._wgt_dispSettings.close()
        self._wgt_checkerboardCalibration.close()
        self._wgt_testStimuli.close()
        # Close MainWindow
        QCloseEvent.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())