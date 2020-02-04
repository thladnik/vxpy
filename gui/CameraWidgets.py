import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from helper import Geometry
import IPC

class EyePositionDetector(QtWidgets.QWidget):

    class PlotWidget(pg.PlotWidget):
        def __init__(self, parent):
            pg.PlotWidget.__init__(self, parent=parent)

            ### Set synchronized variables
            self.eyeMarkerLines: dict = IPC.Buffer.CameraBO._buffers[self.parent().__class__.__name__].eyeMarkerLines
            self.eyeMarkerRects: dict = IPC.Buffer.CameraBO._buffers[self.parent().__class__.__name__].eyeMarkerRects
            self.segmentationMode = IPC.Buffer.CameraBO._buffers[self.parent().__class__.__name__].segmentationMode
            self.areaThreshold = IPC.Buffer.CameraBO._buffers[self.parent().__class__.__name__].areaThreshold

            ### Set up basics
            self.lines = dict()
            self.ellipses = dict()
            self.newMarker = None
            self.currentId = 0

            ### Set up plot image item
            self.imageItem = pg.ImageItem()
            self.getPlotItem().hideAxis('left')
            self.getPlotItem().hideAxis('bottom')
            self.setAspectLocked(True)
            self.getPlotItem().vb.setMouseEnabled(x=False, y=False)
            self.addItem(self.imageItem)

            ### Bind mouse click event for drawing of lines
            self.scene().sigMouseClicked.connect(self.mouseClicked)

            ### Bind context menu call function
            self.getPlotItem().vb.raiseContextMenu = self.raiseContextMenu

        def raiseContextMenu(self, ev):

            ### Set context menu
            self.menu = QtWidgets.QMenu()

            ## Set new line
            self._menu_act_new = QtWidgets.QAction('New marker line')
            self._menu_act_new.triggered.connect(self.addMarkerLine)
            self.menu.addAction(self._menu_act_new)
            self.menu.popup(QtCore.QPoint(ev.screenPos().x(), ev.screenPos().y()))

            self._menu_segmode = self.menu.addMenu('Segmentation mode')
            # Default
            self._menu_segmode_act_setDefault = self._menu_segmode.addAction('Default')
            self._menu_segmode_act_setDefault.setCheckable(True)
            self._menu_segmode_act_setDefault.triggered.connect(lambda: self.setSegmode('default'))
            # Watershed
            self._menu_segmode_act_setWatershed = self._menu_segmode.addAction('Watershed')
            self._menu_segmode_act_setWatershed.setCheckable(True)
            self._menu_segmode_act_setWatershed.triggered.connect(lambda: self.setSegmode('watershed'))
            # Blob detector
            self._menu_segmode_act_setBlobdetect = self._menu_segmode.addAction('Blob detector')
            self._menu_segmode_act_setBlobdetect.setCheckable(True)
            self._menu_segmode_act_setBlobdetect.triggered.connect(lambda: self.setSegmode('blob_detect'))

        def setSegmode(self, mode):
            self.segmentationMode.value = mode

            self._menu_segmode_act_setDefault.setChecked(False)
            self._menu_segmode_act_setWatershed.setChecked(False)

            if mode == 'default':
                self._menu_segmode_act_setDefault.setChecked(True)
            elif mode == 'watershed':
                self._menu_segmode_act_setWatershed.setChecked(True)

        def addMarkerLine(self):
            if self.newMarker is not None:
                return
            self.newMarker = list()

        def mouseClicked(self, ev):
            pos = self.getPlotItem().vb.mapSceneToView(ev.pos())

            if self.newMarker is not None and len(self.newMarker) == 0:
                ## Start new line
                self.newMarker = [[pos.x(), pos.y()]]

            elif self.newMarker is not None and len(self.newMarker) == 1:
                ## Set second point of line
                self.newMarker.append([pos.x(), pos.y()])

                self.eyeMarkerLines[self.currentId] = self.newMarker

                ## Draw line
                lineSegROI = EyePositionDetector.Line(self, self.currentId, self.newMarker,
                                                      pen=pg.mkPen(color='FF0000', width=5))
                self.lines[self.currentId] = lineSegROI
                self.getPlotItem().vb.addItem(self.lines[self.currentId])

                ## Add rectangle
                self.newMarker.append([pos.x(), pos.y()])

                rectROI = EyePositionDetector.Rect(self, self.currentId, self.newMarker)
                self.ellipses[self.currentId] = rectROI
                self.getPlotItem().vb.addItem(self.ellipses[self.currentId])

                self.currentId += 1
                self.newMarker = None

    class Line(pg.LineSegmentROI):
        def __init__(self, parent, id, *args, **kwargs):
            self.parent = parent
            self.id = id
            pg.LineSegmentROI.__init__(self, *args, **kwargs, movable=False, removable=True)

            self.sigRegionChangeFinished.connect(self.updateLineCoords)

        def updateLineCoords(self):
            newPos = self.listPoints()
            self.parent.eyeMarkerLines[self.id] = [[newPos[0].x(), newPos[0].y()], [newPos[1].x(), newPos[1].y()]]

    class Rect(pg.RectROI):

        def __init__(self, parent, id, coords):
            self.parent = parent
            self.id = id
            pg.RectROI.__init__(self, pos=coords[0], size=[50, 150], movable=False, centered=True)

            self.cornerPlot = None

            self.parent.lines[self.id].sigRegionChangeFinished.connect(self.updateRect)
            self.sigRegionChangeFinished.connect(self.updateRect)
            self.updateRect()

        def updateRect(self):
            lineCoords = self.parent.eyeMarkerLines[self.id]
            lineStart = np.array(lineCoords[0])
            lineEnd = np.array(lineCoords[1])
            line = Geometry.vecNormalize(lineEnd - lineStart)
            lineAngleRad = np.arccos(np.dot(Geometry.vecNormalize(np.array([-1.0, 0.0])), line))

            if line[1] > 0:
               lineAngleRad = 2*np.pi - lineAngleRad

            self.setPos(lineStart, finish=False)
            self.setAngle(360 * lineAngleRad / (2 * np.pi), finish=False)

            self.translate(-0.5 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])
                           + 0.5 * self.size().y() * np.array([np.sin(lineAngleRad),-np.cos(lineAngleRad)]),
                           finish=False)

            self.test = [lineStart, np.array(self.size()), 360 * lineAngleRad / (2 * np.pi)]

            self.points = list()
            self.points.append(lineStart + 0.5 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])\
                           - 0.5 * self.size().y() * np.array([np.sin(lineAngleRad), -np.cos(lineAngleRad)]))
            self.points.append(lineStart + 0.5 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])\
                           + 0.5 * self.size().y() * np.array([np.sin(lineAngleRad), -np.cos(lineAngleRad)]))
            self.points.append(lineStart - 0.5 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])\
                           + 0.5 * self.size().y() * np.array([np.sin(lineAngleRad), -np.cos(lineAngleRad)]))
            self.points.append(lineStart - 0.5 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])\
                           - 0.5 * self.size().y() * np.array([np.sin(lineAngleRad), -np.cos(lineAngleRad)]))

            if self.cornerPlot is None:
                self.cornerPlot = pg.ScatterPlotItem()
                self.parent.addItem(self.cornerPlot)
                self.cornerPlot.setPen(pg.mkPen(width=5, color='b'))

            self.cornerPlot.setData(x=[p[0] for p in self.points], y=[p[1] for p in self.points])

            self.parent.eyeMarkerRects[self.id] = self.test#[self.points, lineAngleRad]

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QGridLayout())

        self.plotWidget = EyePositionDetector.PlotWidget(self)
        self.layout().addWidget(self.plotWidget, 0, 0)

        self._spn_treshold = QtWidgets.QSpinBox()
        self._spn_treshold.setValue(self.plotWidget.areaThreshold.value)
        self._spn_treshold.setMinimum(0)
        self._spn_treshold.setMaximum(999999)
        self._spn_treshold.valueChanged.connect(lambda: setattr(self.plotWidget.areaThreshold, 'value',
                                                                self._spn_treshold.value()))
        self.layout().addWidget(self._spn_treshold)

        self.imageItem = self.plotWidget.imageItem