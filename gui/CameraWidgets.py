"""
MappApp ./gui/CameraWidgets.py - Custom widgets which handle UI and visualization with camera process.
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
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from helper import Geometry
import IPC

class EyePositionDetector(pg.GraphicsLayoutWidget):
    def __init__(self, parent):
        pg.GraphicsLayoutWidget.__init__(self, parent=parent)

        ### Set synchronized variables
        self.eyeMarkerRects: dict = IPC.Buffer.CameraBO._buffers[self.__class__.__name__].eyeMarkerRects
        self.extractedRects: dict = IPC.Buffer.CameraBO._buffers[self.__class__.__name__].extractedRects
        self.segmentationMode = IPC.Buffer.CameraBO._buffers[self.__class__.__name__].segmentationMode
        self.areaThreshold = IPC.Buffer.CameraBO._buffers[self.__class__.__name__].areaThreshold

        ### Set up basics
        self.lineSegROIs = dict()
        self.rectROIs = dict()
        self.rectSubplots = dict()
        self.newMarker = None
        self.currentId = 0

        self.imagePlot = self.addPlot(0, 0, 1, 10)

        ### Set up plot image item
        self.imageItem = pg.ImageItem()
        self.imagePlot.hideAxis('left')
        self.imagePlot.hideAxis('bottom')
        self.imagePlot.setAspectLocked(True)
        self.imagePlot.vb.setMouseEnabled(x=False, y=False)
        self.imagePlot.addItem(self.imageItem)

        self.imageItem.sigImageChanged.connect(self.updateRectSubplots)
        ### Bind mouse click event for drawing of lines
        self.imagePlot.scene().sigMouseClicked.connect(self.mouseClicked)

        ### Bind context menu call function
        self.imagePlot.vb.raiseContextMenu = self.raiseContextMenu

    def resizeEvent(self, ev):
        pg.GraphicsLayoutWidget.resizeEvent(self, ev)
        self.setEyeRectPlotMaxHeight()

    def setEyeRectPlotMaxHeight(self):
        if not(hasattr(self, 'ci')):
            return
        self.ci.layout.setRowMaximumHeight(1, self.height()//6)

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
        pos = self.imagePlot.vb.mapSceneToView(ev.scenePos())

        if self.newMarker is not None and len(self.newMarker) == 0:
            ## Start new line
            self.newMarker = [[pos.x(), pos.y()]]

        elif self.newMarker is not None and len(self.newMarker) == 1:
            ## Set second point of line
            self.newMarker.append([pos.x(), pos.y()])

            ## Draw line
            lineSegROI = EyePositionDetector.Line(self, self.currentId, self.newMarker,
                                                  pen=pg.mkPen(color='FF0000', width=2))
            self.lineSegROIs[self.currentId] = lineSegROI
            self.imagePlot.vb.addItem(self.lineSegROIs[self.currentId])

            ## Add rectangle
            self.newMarker.append([pos.x(), pos.y()])

            rectROI = EyePositionDetector.Rect(self, self.currentId, self.newMarker)
            self.rectROIs[self.currentId] = rectROI
            self.imagePlot.vb.addItem(self.rectROIs[self.currentId])

            ## Add subplot
            self.rectSubplots[self.currentId] = dict()
            sp = self.addPlot(1, self.currentId)
            ii = pg.ImageItem()
            sp.hideAxis('left')
            sp.hideAxis('bottom')
            sp.setAspectLocked(True)
            sp.vb.setMouseEnabled(x=False, y=False)
            sp.addItem(ii)

            self.rectSubplots[self.currentId]['imageitem'] = ii
            self.rectSubplots[self.currentId]['plotitem'] = sp

            self.currentId += 1
            self.newMarker = None

    def updateRectSubplots(self):
        for id, plot in self.rectSubplots.items():
            if not(id in self.extractedRects):
                continue

            plot['imageitem'].setImage(np.rot90(self.extractedRects[id], -1))


    class Line(pg.LineSegmentROI):
        def __init__(self, parent, id, *args, **kwargs):
            self.parent = parent
            self.id = id
            pg.LineSegmentROI.__init__(self, *args, **kwargs, movable=False, removable=True)


    class Rect(pg.RectROI):

        def __init__(self, parent, id, coords):
            self.parent = parent
            self.id = id
            pg.RectROI.__init__(self, pos=coords[0], size=[50, 150], movable=False, centered=True)

            self.parent.lineSegROIs[self.id].sigRegionChangeFinished.connect(self.updateRect)
            self.sigRegionChangeFinished.connect(self.updateRect)
            self.updateRect()

        def updateRect(self):
            linePoints = self.parent.lineSegROIs[self.id].listPoints()
            lineCoords = [[linePoints[0].x(), linePoints[0].y()], [linePoints[1].x(), linePoints[1].y()]]
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

            self.rect = [lineStart, np.array(self.size()), 360 * lineAngleRad / (2 * np.pi)]

            self.parent.eyeMarkerRects[self.id] = self.rect
