"""
MappApp ./gui/CameraStream.py - GUI widget for plotting buffers in the camera buffer object.
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
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
from time import perf_counter

import Config
import Definition
import IPC

class Camera(QtWidgets.QWidget):

    def __init__(self, _main, *args, **kwargs):
        self.main = _main
        QtWidgets.QWidget.__init__(self, *args, parent=_main, **kwargs)

        self.fps = 30

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QGridLayout())

        ### Construct buffers
        IPC.BufferObject.constructBuffers()

        self._plotItem = dict()
        # Use default PlotWidget
        self._wdgt_plot = pg.PlotWidget(parent=self)
        self._wdgt_plot.getPlotItem().hideAxis('left')
        self._wdgt_plot.getPlotItem().hideAxis('bottom')
        self._wdgt_plot.setAspectLocked(True)
        self._plotItem = pg.ImageItem()
        self._wdgt_plot.addItem(self._plotItem)
        self._wdgt_plot.getPlotItem().vb.setMouseEnabled(x=False, y=False)
        self.setMinimumSize(Config.Camera[Definition.Camera.res_x], Config.Camera[Definition.Camera.res_y])
        self.layout().addWidget(self._wdgt_plot, 0, 0)

        ### Set frame update timer
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000//self.fps)
        self.timer.timeout.connect(self.updateImage)
        self.timer.start()

    def updateImage(self):
        # Rotate frame because cv2 and pg coords don't match
        self._plotItem.setImage(np.rot90(IPC.BufferObject.readBuffer('FrameBuffer'), -1))

        self.t = perf_counter()