"""
MappApp ./gui/Camera.py - GUI widget for plotting buffers in the camera buffer object.
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

import numpy as np
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from time import perf_counter

import Config
from Definition import CameraConfig
import gui.CameraWidgets
import IPC

class Camera(QtWidgets.QWidget):

    def __init__(self, _main, *args, **kwargs):
        self.main = _main
        QtWidgets.QWidget.__init__(self, *args, parent=_main, **kwargs)

        self.fps = 60.

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QGridLayout())

        if IPC.Buffer.CameraBO is None:
            print('Camera Frame Buffer Object not set in <%s>' % self.main._name)
            return

        IPC.Buffer.CameraBO.constructBuffers()

        bufferNum = len(IPC.Buffer.CameraBO._buffers)

        i = 2 if bufferNum > 1 else 1
        self.setMinimumSize(i * Config.Camera[CameraConfig.resolution_x],
                            int(np.ceil(bufferNum/2)) * Config.Camera[CameraConfig.resolution_y])

        self._wdgt_plots = dict()
        self._plotItems = dict()
        for i, bufferName in enumerate(IPC.Buffer.CameraBO._buffers):
            if hasattr(gui.CameraWidgets, bufferName):
                # Use custom PlotWidget
                self._wdgt_plots[bufferName] = getattr(gui.CameraWidgets, bufferName)(self)
                self._plotItems[bufferName] = self._wdgt_plots[bufferName].imageItem
            else:
                # Use default PlotWidget
                self._wdgt_plots[bufferName] = pg.PlotWidget(parent=self)
                self._wdgt_plots[bufferName].getPlotItem().hideAxis('left')
                self._wdgt_plots[bufferName].getPlotItem().hideAxis('bottom')
                self._wdgt_plots[bufferName].setAspectLocked(True)
                self._plotItems[bufferName] = pg.ImageItem()
                self._wdgt_plots[bufferName].addItem(self._plotItems[bufferName])
                self._wdgt_plots[bufferName].getPlotItem().vb.setMouseEnabled(x=False, y=False)

            self.layout().addWidget(self._wdgt_plots[bufferName], i // 2, i % 2)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000//self.fps)
        self.timer.timeout.connect(self.updateImage)
        self.timer.start()

    def updateImage(self):
        # Rotate frame because cv2 and pg coords don't match
        for bufferName in IPC.Buffer.CameraBO._buffers:
            self._plotItems[bufferName].setImage(np.rot90(IPC.Buffer.CameraBO.readBuffer(bufferName), -1))

        self.t = perf_counter()