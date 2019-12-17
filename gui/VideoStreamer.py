import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from time import perf_counter

class VideoStreamer(QtWidgets.QWidget):

    def __init__(self, main, *args, **kwargs):
        self.main = main
        QtWidgets.QWidget.__init__(self, *args, parent=None, **kwargs)

        self.fps = 60.

        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Video Streamer')

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
        frame = self.main._cameraBO.readBuffer('frame')
        edges = self.main._cameraBO.readBuffer('edge_detector')

        self._plotItem.setImage(np.vstack((np.rot90(frame, -1), np.rot90(edges, -1))))

        #print(perf_counter()-self.t)
        self.t = perf_counter()