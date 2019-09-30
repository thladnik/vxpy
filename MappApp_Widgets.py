from PyQt5 import QtWidgets, QtCore

import MappApp_Communication as macom
import MappApp_Definition as madef
import MappApp_Stimulus as stim

class DisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, main):
        super().__init__('Display settings')
        self.main = main

        self.setupUi()

    def setupUi(self):

        init_settings = self.main.ctrl.config.displaySettings()

        self.setLayout(QtWidgets.QGridLayout())

        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setValue(init_settings[madef.DisplaySettings.float_glob_x_pos])
        self._dspn_x_pos.setMinimum(-1.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(.001)
        self.layout().addWidget(QtWidgets.QLabel('X-position'), 0, 0)
        self.layout().addWidget(self._dspn_x_pos, 0, 1)

        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setMinimum(-1.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(.001)
        self._dspn_y_pos.setValue(init_settings[madef.DisplaySettings.float_glob_y_pos])
        self.layout().addWidget(QtWidgets.QLabel('Y-position'), 1, 0)
        self.layout().addWidget(self._dspn_y_pos, 1, 1)

        self._dspn_vp_center_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_offset.setDecimals(3)
        self._dspn_vp_center_offset.setMinimum(-1.0)
        self._dspn_vp_center_offset.setMaximum(1.0)
        self._dspn_vp_center_offset.setSingleStep(.001)
        self._dspn_vp_center_offset.setValue(init_settings[madef.DisplaySettings.float_vp_center_offset])
        self.layout().addWidget(QtWidgets.QLabel('VP center offset'), 2, 0)
        self.layout().addWidget(self._dspn_vp_center_offset, 2, 1)

        self._dspn_view_axis_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_view_axis_offset.setDecimals(3)
        self._dspn_view_axis_offset.setMinimum(-1.0)
        self._dspn_view_axis_offset.setMaximum(1.0)
        self._dspn_view_axis_offset.setSingleStep(.001)
        self._dspn_view_axis_offset.setValue(init_settings[madef.DisplaySettings.float_view_axis_offset])
        self.layout().addWidget(QtWidgets.QLabel('Origin dir. offset'), 3, 0)
        self.layout().addWidget(self._dspn_view_axis_offset, 3, 1)

        self._dspn_fov = QtWidgets.QDoubleSpinBox()
        self._dspn_fov.setDecimals(1)
        self._dspn_fov.setMinimum(1.0)
        self._dspn_fov.setMaximum(180.0)
        self._dspn_fov.setSingleStep(0.5)
        self._dspn_fov.setValue(init_settings[madef.DisplaySettings.float_vp_fov])
        self.layout().addWidget(QtWidgets.QLabel('FOV'), 4, 0)
        self.layout().addWidget(self._dspn_fov, 4, 1)

        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._dspn_elev_angle.setValue(init_settings[madef.DisplaySettings.float_elev_angle])
        self.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 5, 0)
        self.layout().addWidget(self._dspn_elev_angle, 5, 1)

        self._spn_screen_id = QtWidgets.QSpinBox()
        self._spn_screen_id.setValue(init_settings[madef.DisplaySettings.int_disp_screen_id])
        self.layout().addWidget(QtWidgets.QLabel('Screen'), 20, 0)
        self.layout().addWidget(self._spn_screen_id, 20, 1)

        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setTristate(False)
        self._check_fullscreen.setCheckState(
            self.main._convBoolToCheckstate(init_settings[madef.DisplaySettings.bool_disp_fullscreen]))
        self.layout().addWidget(self._check_fullscreen, 21, 1)

class CheckerboardCalibration(QtWidgets.QGroupBox):

    def __init__(self, main):
        super().__init__('Checkerboard calibration')
        self.main = main

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
        self.main.ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                        [macom.Display.Code.SetNewStimulus, stim.DisplayCheckerboard,
                                        [], dict(rows=self._spn_rows.value(), cols=self._spn_cols.value())])