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
        #self._wgt_checkerboardCalibration.displayCheckerboard()

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
        self._menu_act_testStimuli = QtWidgets.QAction('Stimulation protocols')
        self._menu_act_testStimuli.triggered.connect(self._openStimProtocols)
        self._menu_windows.addAction(self._menu_act_testStimuli)

        ## Setup display settings widget
        self._wgt_dispSettings = DisplaySettings(self)
        self._wgt_dispSettings.setMinimumSize(300, 300)
        self._openDisplaySettings()
        self._wgt_dispSettings.move(geo.x(), geo.y() + geo.height())
        geo_disp = self._wgt_dispSettings.window().geometry()

        ## Setup checkerboard calibration
        #self._wgt_checkerboardCalibration = Calibration(self)
        #self._wgt_checkerboardCalibration.setMinimumSize(300, 100)
        #self._openCheckerboardCalibration()
        #self._wgt_checkerboardCalibration.move(geo.x(), geo_disp.y() + geo_disp.height())
        #geo_checker = self._wgt_checkerboardCalibration.window().geometry()

        ## Setup test stimuli
        self._wgt_StimProtocols = StimulationProtocols(self)
        self._wgt_StimProtocols.setMinimumSize(300, 100)
        self._openStimProtocols()
        self._wgt_StimProtocols.move(geo.x(), geo_disp.y() + geo_disp.height())
        geo_teststim = self._wgt_StimProtocols.window().geometry()

    def _openDisplaySettings(self):
        self._wgt_dispSettings.showNormal()
        self._wgt_dispSettings.show()

    def _openCheckerboardCalibration(self):
        self._wgt_checkerboardCalibration.showNormal()
        self._wgt_checkerboardCalibration.show()

    def _openStimProtocols(self):
        self._wgt_StimProtocols.showNormal()
        self._wgt_StimProtocols.show()

    def closeEvent(self, QCloseEvent):
        # Terminate controller instance
        self.ctrl.terminate()
        # Close widgets
        self._wgt_dispSettings.close()
        #self._wgt_checkerboardCalibration.close()
        self._wgt_StimProtocols.close()
        # Close MainWindow
        QCloseEvent.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec_())