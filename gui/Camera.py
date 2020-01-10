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
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from time import perf_counter

class Camera(QtWidgets.QWidget):

    def __init__(self, _main, *args, **kwargs):
        self.main = _main
        QtWidgets.QWidget.__init__(self, *args, parent=_main, **kwargs)

        self.fps = 60.

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')

        self._aspect = self.main._cameraBO.frameDims[0] / (2 * self.main._cameraBO.frameDims[1])
        self.setMinimumSize(2 * self.main._cameraBO.frameDims[1], self.main._cameraBO.frameDims[0])
        self.setLayout(QtWidgets.QVBoxLayout())

        self._wdgt_plot = pg.PlotWidget(parent=self)
        self._plotItem = pg.ImageItem()
        self._wdgt_plot.getPlotItem().hideAxis('left')
        self._wdgt_plot.getPlotItem().hideAxis('bottom')
        self._wdgt_plot.addItem(self._plotItem)
        self.layout().addWidget(self._wdgt_plot)

        if self.main._cameraBO is None:
            print('Camera Frame Buffer Object not set in <%s>' % self.main._name)
            return

        self.main._cameraBO.constructBuffers()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000//self.fps)
        self.timer.timeout.connect(self.updateImage)
        self.timer.start()


    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.resize(self.width(), int(self._aspect * self.width()))

    def updateImage(self):
        # Rotate frame because cv2 and pg coords don't match
        frame = self.main._cameraBO.readBuffer('frame_buffer')
        edges = self.main._cameraBO.readBuffer('edge_detector')

        self._plotItem.setImage(np.vstack((np.rot90(frame, -1), np.rot90(edges, -1))))

        #print(perf_counter()-self.t)
        self.t = perf_counter()