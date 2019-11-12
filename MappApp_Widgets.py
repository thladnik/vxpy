from PyQt5 import QtWidgets, QtCore
from PyQt5.Qt import Qt

import MappApp_Communication as macom
import MappApp_Definition as madef
import MappApp_Helper as mahlp
import MappApp_Stimulus as stim

class DisplaySettings(QtWidgets.QWidget):

    def __init__(self, main):
        super().__init__(parent=main, flags=Qt.Window)

        self._setupUi()

    def _setupUi(self):

        ## Fetch default display settings from controller
        init_settings = self.parent().ctrl.config.displaySettings()

        ## Setup widget
        self.setWindowTitle('Display settings')
        self.setLayout(QtWidgets.QVBoxLayout())

        ## Setup position
        self._grp_position = QtWidgets.QGroupBox('Position')
        self._grp_position.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_position)
        # X Position
        self._dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_x_pos.setDecimals(3)
        self._dspn_x_pos.setValue(init_settings[madef.DisplaySettings.float_pos_glob_x_pos])
        self._dspn_x_pos.setMinimum(-1.0)
        self._dspn_x_pos.setMaximum(1.0)
        self._dspn_x_pos.setSingleStep(.001)
        self._grp_position.layout().addWidget(QtWidgets.QLabel('X-position'), 0, 0)
        self._grp_position.layout().addWidget(self._dspn_x_pos, 0, 1)
        # Y position
        self._dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self._dspn_y_pos.setDecimals(3)
        self._dspn_y_pos.setMinimum(-1.0)
        self._dspn_y_pos.setMaximum(1.0)
        self._dspn_y_pos.setSingleStep(.001)
        self._dspn_y_pos.setValue(init_settings[madef.DisplaySettings.float_pos_glob_y_pos])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('Y-position'), 1, 0)
        self._grp_position.layout().addWidget(self._dspn_y_pos, 1, 1)
        # Distance from center
        self._dspn_vp_center_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_vp_center_offset.setDecimals(3)
        self._dspn_vp_center_offset.setMinimum(-1.0)
        self._dspn_vp_center_offset.setMaximum(1.0)
        self._dspn_vp_center_offset.setSingleStep(.001)
        self._dspn_vp_center_offset.setValue(init_settings[madef.DisplaySettings.float_pos_glob_center_offset])
        self._grp_position.layout().addWidget(QtWidgets.QLabel('VP center offset'), 2, 0)
        self._grp_position.layout().addWidget(self._dspn_vp_center_offset, 2, 1)

        ## Setup view
        self._grp_view = QtWidgets.QGroupBox('View')
        self._grp_view.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_view)
        # Elevation
        self._dspn_elev_angle = QtWidgets.QDoubleSpinBox()
        self._dspn_elev_angle.setDecimals(1)
        self._dspn_elev_angle.setMinimum(-90.0)
        self._dspn_elev_angle.setMaximum(90.0)
        self._dspn_elev_angle.setSingleStep(0.1)
        self._dspn_elev_angle.setValue(init_settings[madef.DisplaySettings.float_view_elev_angle])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 0, 0)
        self._grp_view.layout().addWidget(self._dspn_elev_angle, 0, 1)
        # Offset of view from axis towards origin of sphere
        self._dspn_view_axis_offset = QtWidgets.QDoubleSpinBox()
        self._dspn_view_axis_offset.setDecimals(3)
        self._dspn_view_axis_offset.setMinimum(-1.0)
        self._dspn_view_axis_offset.setMaximum(1.0)
        self._dspn_view_axis_offset.setSingleStep(.001)
        self._dspn_view_axis_offset.setValue(init_settings[madef.DisplaySettings.float_view_axis_offset])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Origin offset'), 1, 0)
        self._grp_view.layout().addWidget(self._dspn_view_axis_offset, 1, 1)
        # Distance from origin of sphere
        self._dspn_view_origin_distance = QtWidgets.QDoubleSpinBox()
        self._dspn_view_origin_distance.setDecimals(1)
        self._dspn_view_origin_distance.setMinimum(1.5)
        self._dspn_view_origin_distance.setMaximum(10.)
        self._dspn_view_origin_distance.setSingleStep(.1)
        self._dspn_view_origin_distance.setValue(init_settings[madef.DisplaySettings.float_view_origin_distance])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('Origin distance'), 2, 0)
        self._grp_view.layout().addWidget(self._dspn_view_origin_distance, 2, 1)
        # Field of view
        self._dspn_fov = QtWidgets.QDoubleSpinBox()
        self._dspn_fov.setDecimals(1)
        self._dspn_fov.setMinimum(1.0)
        self._dspn_fov.setMaximum(180.0)
        self._dspn_fov.setSingleStep(0.5)
        self._dspn_fov.setValue(init_settings[madef.DisplaySettings.float_view_fov])
        self._grp_view.layout().addWidget(QtWidgets.QLabel('FOV'), 3, 0)
        self._grp_view.layout().addWidget(self._dspn_fov, 3, 1)

        ## Setup display
        self._grp_disp = QtWidgets.QGroupBox('Display')
        self._grp_disp.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_disp)
        # Screen ID
        self._spn_screen_id = QtWidgets.QSpinBox()
        self._spn_screen_id.setValue(init_settings[madef.DisplaySettings.int_disp_screen_id])
        self._grp_disp.layout().addWidget(QtWidgets.QLabel('Screen'), 0, 0)
        self._grp_disp.layout().addWidget(self._spn_screen_id, 0, 1)
        # Use fullscreen
        self._check_fullscreen = QtWidgets.QCheckBox('Fullscreen')
        self._check_fullscreen.setTristate(False)
        self._check_fullscreen.setCheckState(
            mahlp.Conversion.boolToQtCheckstate(init_settings[madef.DisplaySettings.bool_disp_fullscreen]))
        self._grp_disp.layout().addWidget(self._check_fullscreen, 0, 2)

        ## Connect change events to a timer
        # Define update timer
        self.timer_param_update = QtCore.QTimer()
        self.timer_param_update.setSingleShot(True)
        self.timer_param_update.timeout.connect(self.settingsChanged)
        # Timer delay
        td = 250
        # Connect to timer
        self._dspn_x_pos.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_y_pos.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_elev_angle.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_view_axis_offset.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_vp_center_offset.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_view_origin_distance.valueChanged.connect(lambda: self.timer_param_update.start(td))
        self._check_fullscreen.stateChanged.connect(lambda: self.timer_param_update.start(td))
        self._dspn_fov.valueChanged.connect(lambda: self.timer_param_update.start(td))

    def settingsChanged(self):
        self.parent().ctrl.updateDisplaySettings(**{
            madef.DisplaySettings.float_pos_glob_x_pos           : self._dspn_x_pos.value(),
            madef.DisplaySettings.float_pos_glob_y_pos           : self._dspn_y_pos.value(),
            madef.DisplaySettings.float_view_elev_angle          : self._dspn_elev_angle.value(),
            madef.DisplaySettings.float_view_axis_offset         : self._dspn_view_axis_offset.value(),
            madef.DisplaySettings.float_pos_glob_center_offset   : self._dspn_vp_center_offset.value(),
            madef.DisplaySettings.float_view_origin_distance     : self._dspn_view_origin_distance.value(),
            madef.DisplaySettings.float_view_fov                 : self._dspn_fov.value(),
            madef.DisplaySettings.int_disp_screen_id             : self._spn_screen_id.value(),
            madef.DisplaySettings.bool_disp_fullscreen           : mahlp.Conversion.QtCheckstateToBool(
                self._check_fullscreen.checkState())
        })

class Calibration(QtWidgets.QWidget):

    def __init__(self, main):
        super().__init__(parent=main, flags=Qt.Window)

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
        self._grp_sstripes = QtWidgets.QGroupBox('Static stripes')
        self._grp_sstripes.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._grp_sstripes)
        # Vertical or horizontal
        self._cb_orientation = QtWidgets.QComboBox()
        self._cb_orientation.addItem('vertical')
        self._cb_orientation.addItem('horizontal')
        self._grp_sstripes.layout().addWidget(QtWidgets.QLabel('Orientation'), 0, 0)
        self._cb_orientation.currentTextChanged.connect(self.updateSStripes)
        self._grp_sstripes.layout().addWidget(self._cb_orientation, 0, 1)
        # Number of stripes
        self._spn_sstripes_num = QtWidgets.QSpinBox()
        self._spn_sstripes_num.setValue(20)
        self._spn_sstripes_num.valueChanged.connect(self.updateSStripes)
        self._grp_sstripes.layout().addWidget(QtWidgets.QLabel('Number'), 1, 0)
        self._grp_sstripes.layout().addWidget(self._spn_sstripes_num, 1, 1)
        # Set static stripes
        self._btn_disp_sstripes = QtWidgets.QPushButton('Display static stripes')
        self._btn_disp_sstripes.clicked.connect(self.displayStaticStripes)
        self._grp_sstripes.layout().addWidget(self._btn_disp_sstripes, 2, 0, 1, 2)



    def displayCheckerboard(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                                 [macom.Display.Code.SetNewStimulus, stim.Checkerboard,
                                                  [], dict(rows=self._spn_checker_rows.value(), cols=self._spn_checker_cols.value())])

    def updateCheckerboard(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                                 [macom.Display.Code.UpdateStimulusParams, stim.Checkerboard,
                                                  dict(rows=self._spn_checker_rows.value(), cols=self._spn_checker_cols.value())])

    def displayStaticStripes(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                                 [macom.Display.Code.SetNewStimulus, stim.StaticStripes,
                                                  [], dict(
                                                     num=self._spn_sstripes_num.value(), orientation=self._cb_orientation.currentText()
                                                 )])

    def updateSStripes(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                                 [macom.Display.Code.UpdateStimulusParams, stim.StaticStripes,
                                                  dict(
                                                      num=self._spn_sstripes_num.value(),
                                                      orientation=self._cb_orientation.currentText()
                                                  )])


class TestStimuli(QtWidgets.QWidget):

    def __init__(self, main):
        super().__init__(parent=main, flags=Qt.Window)

        self.setupUi()

    def setupUi(self):

        ## Setup widget
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setWindowTitle('Test stimuli')

        # Display moving grating
        self._btn_displayMovGrating = QtWidgets.QPushButton('Moving grating')
        self._btn_displayMovGrating.clicked.connect(self.displayMovingGrating)
        self.layout().addWidget(self._btn_displayMovGrating)

        # Display moving sinusoid
        self._btn_displayMovSinusoid = QtWidgets.QPushButton('Moving sinusoid')
        self._btn_displayMovSinusoid.clicked.connect(self.displayMovingSinusoid)
        self.layout().addWidget(self._btn_displayMovSinusoid)

        # Display moving sinusoid
        self._btn_display360Movie = QtWidgets.QPushButton('360 movie')
        self._btn_display360Movie.clicked.connect(self.display360Movie)
        self.layout().addWidget(self._btn_display360Movie)


    def displayMovingGrating(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                        [macom.Display.Code.SetNewStimulus, stim.Checkerboard,
                                        [], dict()])

    def displayMovingSinusoid(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                        [macom.Display.Code.SetNewStimulus, stim.Checkerboard,
                                        [], dict()])


    def display360Movie(self):
        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                        [macom.Display.Code.SetNewStimulus, stim.Checkerboard,
                                        ['media/Rotation.mp4'], dict()])

