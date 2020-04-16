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
import Def
import IPC

class Camera(QtWidgets.QWidget):

    def __init__(self, _main, *args, **kwargs):
        self.main = _main
        QtWidgets.QWidget.__init__(self, *args, parent=_main, **kwargs)

        self.streamFps = 120

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Camera')
        self.setLayout(QtWidgets.QVBoxLayout())

        ## Use default PlotWidget
        self._wdgt_plot = pg.PlotWidget(parent=self)
        self._wdgt_plot.getPlotItem().hideAxis('left')
        self._wdgt_plot.getPlotItem().hideAxis('bottom')
        self._wdgt_plot.setAspectLocked(True)
        self._plotItem = pg.ImageItem()
        self._wdgt_plot.addItem(self._plotItem)
        self._wdgt_plot.getPlotItem().vb.setMouseEnabled(x=False, y=False)
        self.setMinimumSize(Config.Camera[Def.CameraCfg.res_x], Config.Camera[Def.CameraCfg.res_y])
        self.layout().addWidget(self._wdgt_plot)

        ### Set camera property dials
        self._gb_properties = QtWidgets.QGroupBox('Camera properties')
        self._gb_properties.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self._gb_properties)
        ## Exposure
        self._gb_properties.layout().addWidget(QtWidgets.QLabel('Exposure [ms]'), 0, 0)
        self._dspn_exposure = QtWidgets.QDoubleSpinBox(self._gb_properties)
        self._dspn_exposure.setSingleStep(0.01)
        self._dspn_exposure.valueChanged.connect(lambda: self.updateConfig(Def.CameraCfg.exposure))
        self._gb_properties.layout().addWidget(self._dspn_exposure, 0, 1)
        ## Gain
        self._gb_properties.layout().addWidget(QtWidgets.QLabel('Gain [a.u.]'), 1, 0)
        self._dspn_gain = QtWidgets.QDoubleSpinBox(self._gb_properties)
        self._dspn_gain.setSingleStep(0.01)
        self._dspn_gain.valueChanged.connect(lambda: self.updateConfig(Def.CameraCfg.gain))
        self._gb_properties.layout().addWidget(self._dspn_gain, 1, 1)

        ### Set property update timer
        self.propTimer = QtCore.QTimer()
        self.propTimer.setInterval(20)
        self.propTimer.timeout.connect(self.updateProperties)
        self.propTimer.start()

        ### Set frame update timer
        self.imTimer = QtCore.QTimer()
        self.imTimer.setInterval(1000 // self.streamFps)
        self.imTimer.timeout.connect(self.updateImage)
        self.imTimer.start()

    def updateProperties(self):
        self._dspn_exposure.setValue(Config.Camera[Def.CameraCfg.exposure])
        self._dspn_gain.setValue(Config.Camera[Def.CameraCfg.gain])

    def updateConfig(self, propName):
        if propName == Def.CameraCfg.exposure:
            Config.Camera[propName] = self._dspn_exposure.value()
        elif propName == Def.CameraCfg.gain:
            Config.Camera[propName] = self._dspn_gain.value()

    def updateImage(self):
        # Plot image
        self._plotItem.setImage(np.rot90(IPC.BufferObject.Camera._buffers['FrameBuffer'].readFrame(), -1))

        self.t = perf_counter()