"""
MappApp .process/GUI.py - Graphical user interface for easier UX.
Copyright (C) 2020 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from time import strftime

import Definition
import Buffers
import Controller
import Logging
import gui.DisplaySettings
import gui.Protocols
import gui.Camera

class Main(QtWidgets.QMainWindow, Controller.BaseProcess):
    name = Definition.Process.GUI

    _cameraBO    : Buffers.CameraBufferObject
    _app         : QtWidgets.QApplication
    _logFilename : str = None

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, _app=QtWidgets.QApplication(sys.argv), **kwargs)
        QtWidgets.QMainWindow.__init__(self, flags=QtCore.Qt.Window)

        ### Set icon
        self.setWindowIcon(QtGui.QIcon('MappApp.ico'))

        ### Fetch log file
        self.registerPropertyWithController('_logFilename')
        while self._logFilename is None:
            self._handleCommunication()
        self.logccount = 0

        self._setupUI()

        ### Run event loop
        self.run()


    def run(self):
        ### Set timer for handling of communication
        self._tmr_handlePipe = QtCore.QTimer()
        self._tmr_handlePipe.timeout.connect(self._handleCommunication)
        self._tmr_handlePipe.start(10)

        ### Set timer for updating of log
        self._tmr_logger = QtCore.QTimer()
        self._tmr_logger.timeout.connect(self.printLog)
        self._tmr_logger.start(50)

        ### Run QApplication event loop
        self._app.exec_()

    def _setupUI(self):

        self.setWindowTitle('MappApp')
        self.move(50, 50)
        self.setFixedSize(1600, 700)

        ## Setup central widget
        self._centralwidget = QtWidgets.QWidget(parent=self, flags=QtCore.Qt.Widget)
        self._centralwidget.setLayout(QtWidgets.QGridLayout())
        self.setCentralWidget(self._centralwidget)

        self._txe_log = QtWidgets.QTextEdit()
        self._txe_log.setReadOnly(True)
        self._txe_log.setFontFamily('Courier')
        self._txe_log.setFontPointSize(10)
        self._centralwidget.layout().addWidget(QtWidgets.QLabel('Log'), 0, 0)
        self._centralwidget.layout().addWidget(self._txe_log, 1, 0)

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
        # Menu processes
        self._menu_process = QtWidgets.QMenu('Processes')
        self.menuBar().addMenu(self._menu_process)
        self.menuBar().addMenu(self._menu_windows)
        self._menu_process_redisp = QtWidgets.QAction('Restart display')
        self._menu_process_redisp.setShortcut('Ctrl+d')
        self._menu_process_redisp.triggered.connect(
            lambda: self.rpc(Definition.Process.Controller, Controller.Controller.initializeDisplay))
        self._menu_process.addAction(self._menu_process_redisp)

        ## Display Settings
        self._wdgt_dispSettings = gui.DisplaySettings.DisplaySettings(self)
        self._wdgt_dispSettings.move(1660, 50)
        self._openDisplaySettings()

        ## Stimulus Protocols
        self._wdgt_stimProtocols = gui.Protocols.Protocols(self)
        self._wdgt_stimProtocols.move(1660, 560)
        self._openStimProtocols()

        # Video Streamer
        self._wdgt_camera = gui.Camera.Camera(self, flags=QtCore.Qt.Window)
        self._wdgt_camera.move(50, 800)
        self._openVideoStreamer()

        self.show()

    def printLog(self):
        with open(os.path.join(Definition.Path.Log, self._logFilename), 'r') as fobj:
            lines = fobj.read().split('<<\n')
            for line in lines[self.logccount:]:
                if len(line) == 0:
                    continue
                record = line.split(' <<>> ')
                if record[2].find('INFO') > -1 or record[2].find('WARN') > -1:
                    #self._txe_log.append(line)
                    self._txe_log.append('{} :: {:10} :: {:8} :: {} '
                                         .format(record[0],
                                                 record[1].replace(' ', ''),
                                                 record[2].replace(' ', ''),
                                                 record[3]))
                self.logccount += 1

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
        self._wdgt_camera.showNormal()
        self._wdgt_camera.show()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Inform controller of close event
        self._wdgt_dispSettings.close()
        self._wdgt_stimProtocols.close()
        self._wdgt_camera.close()
        self.send(Definition.Process.Controller, Controller.BaseProcess.Signals.Shutdown)
        self.send(Definition.Process.Controller, Controller.BaseProcess.Signals.ConfirmShutdown)


