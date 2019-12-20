from PyQt5 import QtCore, QtGui, QtWidgets
import sys

import Definition as madef
import Camera
import Process
import gui.DisplaySettings
import gui.Protocols
import gui.Camera

class GUI(QtWidgets.QMainWindow, Process.BaseProcess):

    name = 'gui'

    _cameraBO : Camera.CameraBufferObject
    _app      : QtWidgets.QApplication

    def __init__(self, **kwargs):
        Process.BaseProcess.__init__(self, **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

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
        self._wdgt_dispSettings = gui.DisplaySettings.DisplaySettings(self)
        self._wdgt_dispSettings.move(50, 400)
        self._openDisplaySettings()

        ## Stimulus Protocols
        self._wdgt_stimProtocols = gui.Protocols.Protocols(self)
        self._wdgt_stimProtocols.move(450, 400)
        self._openStimProtocols()

        # Video Streamer
        self._wdgt_videoStreamer = gui.Camera.Camera(self, flags=QtCore.Qt.Window)
        self._wdgt_videoStreamer.move(850, 50)
        self._openVideoStreamer()

        self.show()

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
        self._sendToCtrl(Process.BaseProcess.Signals.Shutdown)

def runGUI(**kwargs):
    app = QtWidgets.QApplication(sys.argv)
    GUI(_app=app, **kwargs)

