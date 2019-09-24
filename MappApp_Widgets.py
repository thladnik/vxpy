from PyQt5 import QtWidgets, QtCore

import MappApp_Com as macom
import MappApp_Stimulus as stim

class DisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, main):
        super().__init__('Display settings')
        self.main = main

        self.setupUi()

    def setupUi(self):

        self.setLayout(QtWidgets.QGridLayout())

        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setValue(0.)
        self._dspn_x_pos.setMinimum(-1.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(0.001)
        self.layout().addWidget(QtWidgets.QLabel('X position'), 0, 0)
        self.layout().addWidget(self._dspn_x_pos, 0, 1)

        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setValue(0.)
        self._dspn_y_pos.setMinimum(-1.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(0.001)
        self.layout().addWidget(QtWidgets.QLabel('Y position'), 1, 0)
        self.layout().addWidget(self._dspn_y_pos, 1, 1)

        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setValue(0.)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setSingleStep(0.1)
        self.layout().addWidget(QtWidgets.QLabel('Elevation angle'), 2, 0)
        self.layout().addWidget(self._dspn_elev_angle, 2, 1)

        self._dspn_glob_disp_size = QtWidgets.QDoubleSpinBox()
        self._dspn_glob_disp_size.setDecimals(3)
        self._dspn_glob_disp_size.setValue(1.)
        self._dspn_glob_disp_size.setMinimum(0.01)
        self._dspn_glob_disp_size.setMaximum(2.0)
        self._dspn_glob_disp_size.setSingleStep(0.005)
        self.layout().addWidget(QtWidgets.QLabel('Global display size'), 3, 0)
        self.layout().addWidget(self._dspn_glob_disp_size, 3, 1)

        self._dspn_vp_center_dist = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_dist.setDecimals(3)
        self._dspn_vp_center_dist.setValue(0.0)
        self._dspn_vp_center_dist.setMinimum(-1.0)
        self._dspn_vp_center_dist.setMaximum(1.0)
        self._dspn_vp_center_dist.setSingleStep(0.001)
        self.layout().addWidget(QtWidgets.QLabel('Center distance'), 4, 0)
        self.layout().addWidget(self._dspn_vp_center_dist, 4, 1)

        self._spn_screen_id = QtWidgets.QSpinBox()
        self._spn_screen_id.setValue(0)
        self.layout().addWidget(QtWidgets.QLabel('Screen'), 20, 0)
        self.layout().addWidget(self._spn_screen_id, 20, 1)

        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setCheckState(QtCore.Qt.Unchecked)
        self.layout().addWidget(self._check_fullscreen, 21, 1)

class CheckerboardCalibration(QtWidgets.QGroupBox):

    def __init__(self, main):
        super().__init__('Checkerboard calibration')
        self.main = main

#self.displayClient = macom.Display.Client()

        self.setupUi()


    def setupUi(self):

        self.setLayout(QtWidgets.QGridLayout())

        self._spn_rows = QtWidgets.QSpinBox()
        self._spn_rows.setValue(16)
        self.layout().addWidget(QtWidgets.QLabel('Rows'), 0, 0)
        self.layout().addWidget(self._spn_rows, 0, 1)

        self._spn_cols = QtWidgets.QSpinBox()
        self._spn_cols.setValue(16)
        self.layout().addWidget(QtWidgets.QLabel('Columns'), 1, 0)
        self.layout().addWidget(self._spn_cols, 1, 1)

        self._btn_disp_checkerboard = QtWidgets.QPushButton('Display checkerboard')
        self._btn_disp_checkerboard.clicked.connect(self.displayCheckerboard)
        self.layout().addWidget(self._btn_disp_checkerboard, 2, 0, 1, 2)

    def displayCheckerboard(self):
        print('Sending')
        self.main.displayClient.send([macom.Display.Code.SetNewStimulus, stim.DisplayCheckerboard,
                               [], dict(rows=self._spn_rows.value(), cols=self._spn_cols.value())])