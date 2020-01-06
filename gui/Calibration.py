from PyQt5 import QtCore, QtWidgets

class Calibration(QtWidgets.QWidget):

    def __init__(self, main):
        self.main = main
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)

        self.setupUi()

    def setupUi(self):

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        self.setWindowTitle('Calibration')

        ## Checkerboard
        self._grp_checker = QtWidgets.QGroupBox('Checkerboard')
        self._grp_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_checker)
        # Rows
        self._spn_checker_rows = QtWidgets.QSpinBox()
        self._spn_checker_rows.setValue(16)
        self._spn_checker_rows.valueChanged.connect(self.updateCheckerboard)
        self._grp_checker.layout().addWidget(QtWidgets.QLabel('Rows'), 0, 0)
        self._grp_checker.layout().addWidget(self._spn_checker_rows, 0, 1)
        # Cols
        self._spn_checker_cols = QtWidgets.QSpinBox()
        self._spn_checker_cols.setValue(16)
        self._spn_checker_cols.valueChanged.connect(self.updateCheckerboard)
        self._grp_checker.layout().addWidget(QtWidgets.QLabel('Columns'), 1, 0)
        self._grp_checker.layout().addWidget(self._spn_checker_cols, 1, 1)
        # Set checkerboard
        self._btn_disp_checkerboard = QtWidgets.QPushButton('Display checkerboard')
        self._btn_disp_checkerboard.clicked.connect(self.displayCheckerboard)
        self._grp_checker.layout().addWidget(self._btn_disp_checkerboard, 2, 0, 1, 2)

        ## Static stripes
        self._grp_grating = QtWidgets.QGroupBox('Grating')
        self._grp_grating.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_grating)
        # Rectangular or sinusoidal
        self._cb_grating_shape = QtWidgets.QComboBox()
        self._cb_grating_shape.addItem('rectangular')
        self._cb_grating_shape.addItem('sinusoidal')
        self._cb_grating_shape.currentTextChanged.connect(self.updateGrating)
        self._grp_grating.layout().addWidget(QtWidgets.QLabel('Shape'), 0, 0)
        self._grp_grating.layout().addWidget(self._cb_grating_shape, 0, 1)
        # Vertical or horizontal
        self._cb_grating_orient = QtWidgets.QComboBox()
        self._cb_grating_orient.addItem('vertical')
        self._cb_grating_orient.addItem('horizontal')
        self._cb_grating_orient.currentTextChanged.connect(self.updateGrating)
        self._grp_grating.layout().addWidget(QtWidgets.QLabel('Orientation'), 1, 0)
        self._grp_grating.layout().addWidget(self._cb_grating_orient, 1, 1)
        # Velocity
        self._dspn_grating_v = QtWidgets.QDoubleSpinBox()
        self._dspn_grating_v.setMinimum(-99.9)
        self._dspn_grating_v.setMaximum(99.9)
        self._dspn_grating_v.setValue(0.0)
        self._dspn_grating_v.valueChanged.connect(self.updateGrating)
        self._grp_grating.layout().addWidget(QtWidgets.QLabel('Velocity'), 2, 0)
        self._grp_grating.layout().addWidget(self._dspn_grating_v, 2, 1)
        # Number of stripes
        self._spn_grating_num = QtWidgets.QSpinBox()
        self._spn_grating_num.setValue(20)
        self._spn_grating_num.valueChanged.connect(self.updateGrating)
        self._grp_grating.layout().addWidget(QtWidgets.QLabel('Number'), 3, 0)
        self._grp_grating.layout().addWidget(self._spn_grating_num, 3, 1)
        # Set static stripes
        self._btn_disp_grating = QtWidgets.QPushButton('Display grating')
        self._btn_disp_grating.clicked.connect(self.displayGrating)
        self._grp_grating.layout().addWidget(self._btn_disp_grating, 4, 0, 1, 2)
