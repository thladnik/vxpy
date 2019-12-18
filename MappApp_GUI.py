import logging
from PyQt5 import QtCore, QtGui, QtWidgets
import sys

import MappApp_Definition as madef
from process.Base import BaseProcess
from gui.Calibration import *
from gui.DisplaySettings import *
from gui.StimulationProtocols import *
from gui.VideoStreamer import *

class GUI(QtWidgets.QMainWindow, BaseProcess):

    _name = madef.Process.GUI.name

    def __init__(self, _app, _ctrlQueue, _inPipe, _logQueue, _cameraBO=None):
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)
        BaseProcess.__init__(self, _ctrlQueue=_ctrlQueue, _inPipe=_inPipe, _logQueue=_logQueue)
        self._app = _app
        self._cameraBO = _cameraBO

        print('Set up GUI')
        self._setupUI()

        self.run()

    def main(self):
        # Set timer for handling the pipe
        self._tmr_handlePipe = QtCore.QTimer()
        self._tmr_handlePipe.timeout.connect(self._handlePipe)
        self._tmr_handlePipe.start(10)

        # Run QApplication event loop
        self._app.exec_()

    def _setupUI(self):

        self.setWindowTitle('MappApp')
        self.move(50, 50)
        self.setFixedSize(800, 300)

        ## Setup central widget
        self._centralwidget = QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget)
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        ## Setup menubar
        self.setMenuBar(QtWidgets.QMenuBar())
        # Menu windows
        self._menu_windows = QtWidgets.QMenu('Windows')
        self.menuBar().addMenu(self._menu_windows)
        self._menu_act_dispSettings = QtWidgets.QAction('Display settings')
        #self._menu_act_dispSettings.triggered.connect(self._openDisplaySettings)
        self._menu_windows.addAction(self._menu_act_dispSettings)
        self._menu_act_checkerCalib = QtWidgets.QAction('Checkerboard calibration')
        #self._menu_act_checkerCalib.triggered.connect(self._openCheckerboardCalibration)
        self._menu_windows.addAction(self._menu_act_checkerCalib)
        self._menu_act_testStimuli = QtWidgets.QAction('Stimulation protocols')
        #self._menu_act_testStimuli.triggered.connect(self._openStimProtocols)
        self._menu_windows.addAction(self._menu_act_testStimuli)

        ## Display Settings
        self._wdgt_dispSettings = DisplaySettings(self)
        self._wdgt_dispSettings.move(50, 400)
        self._openDisplaySettings()

        ## Stimulus Protocols
        self._wdgt_stimProtocols = StimulationProtocols(self)
        self._wdgt_stimProtocols.move(450, 400)
        self._openStimProtocols()

        # Video Streamer
        self._wdgt_videoStreamer = VideoStreamer(self, flags=QtCore.Qt.Window)
        self._wdgt_videoStreamer.move(850, 50)
        self._openVideoStreamer()

        self.show()

    def _edgeDetectorParamsUpdated(self):
        self._rpcToProcess(
            madef.Process.FrameGrabber, madef.Process.FrameGrabber.updateBufferEvalParams,
            'edge_detector',
            thresh1=self._spn_EdgeDetector_thresh1.value(),
            thresh2=self._spn_EdgeDetector_thresh2.value())

    def _openDisplaySettings(self):
        self._wdgt_dispSettings.showNormal()
        self._wdgt_dispSettings.show()

    def _openCheckerboardCalibration(self):
        self._wgt_checkerboardCalibration.showNormal()
        self._wgt_checkerboardCalibration.show()

    def _openStimProtocols(self):
        self._wdgt_stimProtocols.showNormal()
        self._wdgt_stimProtocols.show()

    def _openVideoStreamer(self):
        self._wdgt_videoStreamer.showNormal()
        self._wdgt_videoStreamer.show()

    def _registerCallback(self, signature, fun):
        setattr(self, signature, fun)


    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Inform controller of close event
        self._wdgt_dispSettings.close()
        self._wdgt_stimProtocols.close()
        self._wdgt_videoStreamer.close()
        self._sendToCtrl([madef.Process.Signal.rpc, madef.Process.Signal.shutdown])

def runGUI(*args, **kwargs):
    app = QtWidgets.QApplication(sys.argv)
    GUI(app, *args, **kwargs)

