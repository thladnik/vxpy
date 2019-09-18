from PyQt5 import QtWidgets, QtCore

class DisplaySettings(QtWidgets.QWidget):

    def __init__(self, main, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main = main

        self.setupUi()

    def setupUi(self):

        self.setLayout(QtWidgets.QGridLayout())

        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setValue(0.)
        self._dspn_x_pos.setMinimum(0.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(0.001)
        self.layout().addWidget(QtWidgets.QLabel('X position'), 0, 0)
        self.layout().addWidget(self._dspn_x_pos, 0, 1)

        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setValue(0.)
        self._dspn_y_pos.setMinimum(0.0)
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

        self._dspn_disp_size_glob = QtWidgets.QDoubleSpinBox()
        self._dspn_disp_size_glob.setDecimals(3)
        self._dspn_disp_size_glob.setValue(1.)
        self._dspn_disp_size_glob.setMinimum(0.01)
        self._dspn_disp_size_glob.setMaximum(2.0)
        self._dspn_disp_size_glob.setSingleStep(0.005)
        self.layout().addWidget(QtWidgets.QLabel('Global display size'), 3, 0)
        self.layout().addWidget(self._dspn_disp_size_glob, 3, 1)

        self._dspn_vp_center_dist = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_dist.setDecimals(3)
        self._dspn_vp_center_dist.setValue(0.0)
        self._dspn_vp_center_dist.setMinimum(-1.0)
        self._dspn_vp_center_dist.setMaximum(1.0)
        self._dspn_vp_center_dist.setSingleStep(0.001)
        self.layout().addWidget(QtWidgets.QLabel('Center distance'), 4, 0)
        self.layout().addWidget(self._dspn_vp_center_dist, 4, 1)

        self._spn_disp_screen = QtWidgets.QSpinBox()
        self._spn_disp_screen.setValue(0)
        self.layout().addWidget(QtWidgets.QLabel('Screen'), 20, 0)
        self.layout().addWidget(self._spn_disp_screen, 20, 1)

        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setCheckState(QtCore.Qt.Unchecked)
        self.layout().addWidget(self._check_fullscreen, 21, 1)