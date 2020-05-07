"""
MappApp ./gui/Camera.py - Custom addons which handle UI and visualization with camera process.
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
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

import Config
import Def
from helper import Geometry
import IPC
import routines.Camera

################################
# Live Camera Widget

class LiveCamera(QtWidgets.QWidget):
    def __init__(self, parent, **kwargs):
        ### Set module always to active
        self.moduleIsActive = True
        QtWidgets.QWidget.__init__(self, parent, **kwargs)
        self.setWindowTitle('Live camera')
        baseSize = (Config.Camera[Def.CameraCfg.res_x], 1.5 * Config.Camera[Def.CameraCfg.res_y])
        self.setMinimumSize(*baseSize)
        self.resize(*baseSize)
        self.setLayout(QtWidgets.QGridLayout())

        self.graphicsWidget = LiveCamera.GraphicsWidget(parent=self)
        self.layout().addWidget(self.graphicsWidget, 0, 0)

    def updateFrame(self):
        idx, frame = IPC.Routines.Camera.readAttribute('FrameRoutine/frame')
        if not(frame is None):
            self.graphicsWidget.imageItem.setImage(np.rot90(frame, -1))

    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            ### Add plot
            self.imagePlot = self.addPlot(0, 0, 1, 10)

            ### Set up plot image item
            self.imageItem = pg.ImageItem()
            self.imagePlot.hideAxis('left')
            self.imagePlot.hideAxis('bottom')
            self.imagePlot.setAspectLocked(True)
            self.imagePlot.vb.setMouseEnabled(x=False, y=False)
            self.imagePlot.addItem(self.imageItem)


################################
# Eye Position Detector Widget

class EyePositionDetector(QtWidgets.QWidget):
    def __init__(self, parent, **kwargs):
        ### Check if camera is being used (since detector relies on camera input)
        if not(Config.Camera[Def.CameraCfg.use]):
            self.moduleIsActive = False
            return
        self.moduleIsActive = True

        QtWidgets.QWidget.__init__(self, parent, flags=QtCore.Qt.Window, **kwargs)
        self.setWindowTitle('Eye position detector')
        baseSize = (Config.Camera[Def.CameraCfg.res_x], 1.5 * Config.Camera[Def.CameraCfg.res_y])
        self.setMinimumSize(*baseSize)
        self.resize(*baseSize)
        self.setLayout(QtWidgets.QGridLayout())

        self.graphicsWidget = EyePositionDetector.GraphicsWidget(parent=self)
        self.layout().addWidget(self.graphicsWidget, 0, 0)

    def updateFrame(self):
        idx, frame = IPC.Routines.Camera.readAttribute('FrameRoutine/frame')

        if not(frame is None):
            self.graphicsWidget.imageItem.setImage(np.rot90(frame, -1))


    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            self.ROIs = dict()

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

        def addMarkerLine(self):
            if self.newMarker is not None:
                return
            self.newMarker = list()

        def mouseClicked(self, ev):
            pos = self.imagePlot.vb.mapSceneToView(ev.scenePos())

            ### First click: start new line
            if self.newMarker is not None and len(self.newMarker) == 0:
                self.newMarker = [[pos.x(), pos.y()]]

            ### Second click: end line and create rectangular ROI + subplot
            elif self.newMarker is not None and len(self.newMarker) == 1:
                ## Set second point of line
                self.newMarker.append([pos.x(), pos.y()])

                ## Draw line
                lineSegROI = EyePositionDetector.Line(self, self.currentId, self.newMarker,
                                                      pen=pg.mkPen(color='FF0000', width=2))
                self.lineSegROIs[self.currentId] = lineSegROI
                self.imagePlot.vb.addItem(self.lineSegROIs[self.currentId])


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
            idx, extractedRects = IPC.Routines.Camera.readAttribute('EyePosDetectRoutine/extractedRects')
            if extractedRects is None:
                return

            ### Plot rectangualar ROIs
            for id in range(len(extractedRects)):
                self.rectSubplots[id]['imageitem'].setImage(np.rot90(extractedRects[id], -1))


    class Line(pg.LineSegmentROI):
        def __init__(self, parent, id, *args, **kwargs):
            self.parent = parent
            self.id = id
            pg.LineSegmentROI.__init__(self, *args, **kwargs, movable=False, removable=True)


    class Rect(pg.RectROI):

        def __init__(self, parent, id, coords):
            self.parent = parent
            self.id = id
            ## Add rectangle
            lLen = np.linalg.norm(np.array(coords[0]) - np.array(coords[1]))
            pg.RectROI.__init__(self, pos=coords[0], size=lLen * np.array([0.8, 1.3]), movable=False, centered=True)

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

            ### Set updates ROI parameters
            self.parent.ROIs[self.id] = self.rect
            ### Send update to detector routine
            IPC.rpc(Def.Process.Camera, routines.Camera.EyePosDetectRoutine.setROI, self.id, self.rect)


################################
# Tail Deflection Detector Widget
# TODO: finish tail detector

class TailDeflectionDetector(QtWidgets.QWidget):
    def __init__(self, parent, **kwargs):
        ### Check if camera is being used (since detector relies on camera input)
        if not(Config.Camera[Def.CameraCfg.use]):
            self.moduleIsActive = False
            return
        self.moduleIsActive = True

        QtWidgets.QWidget.__init__(self, parent, flags=QtCore.Qt.Window, **kwargs)
        self.setWindowTitle('Tail deflection detector')
        baseSize = (Config.Camera[Def.CameraCfg.res_x], 1.5 * Config.Camera[Def.CameraCfg.res_y])
        self.setMinimumSize(*baseSize)
        self.resize(*baseSize)
        self.setLayout(QtWidgets.QGridLayout())

        self.graphicsWidget = TailDeflectionDetector.GraphicsWidget(parent=self)
        self.layout().addWidget(self.graphicsWidget, 0, 0)

    def updateFrame(self):
        frame = IPC.Routines.Camera.readAttribute('FrameBuffer/frame')
        self.graphicsWidget.imageItem.setImage(np.rot90(frame, -1))


    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            ### Set synchronized variables
            self.fishMarkerRects: dict = IPC.Routines.Camera._buffers[self.parent().__class__.__name__].fishMarkerRects
            self.extractedRects: dict = IPC.Routines.Camera._buffers[self.parent().__class__.__name__].extractedRects
            self.tailDeflectionAngles = IPC.Routines.Camera._buffers[self.parent().__class__.__name__].tailDeflectionAngles

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

        def addMarkerLine(self):
            if self.newMarker is not None:
                return
            self.newMarker = list()

        def mouseClicked(self, ev):
            pos = self.imagePlot.vb.mapSceneToView(ev.scenePos())

            ### First click: start new line
            if self.newMarker is not None and len(self.newMarker) == 0:
                self.newMarker = [[pos.x(), pos.y()]]

            ### Second click: end line and create rectangular ROI + subplot
            elif self.newMarker is not None and len(self.newMarker) == 1:
                ## Set second point of line
                self.newMarker.append([pos.x(), pos.y()])

                ## Draw line
                lineSegROI = TailDeflectionDetector.Line(self, self.currentId, self.newMarker,
                                                      pen=pg.mkPen(color='FF0000', width=2))
                self.lineSegROIs[self.currentId] = lineSegROI
                self.imagePlot.vb.addItem(self.lineSegROIs[self.currentId])


                rectROI = TailDeflectionDetector.Rect(self, self.currentId, self.newMarker)
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


    class Rect(pg.ROI):

        def __init__(self, parent, id, coords):
            self.parent = parent
            self.id = id
            ## Add rectangle
            lLen = np.linalg.norm(np.array(coords[0]) - np.array(coords[1]))
            pg.ROI.__init__(self, coords[0], lLen * np.array([1.2, 0.75]), movable=False)
            center = [0.5, 0.5]

            self.addScaleHandle([0.5, 1], [0.5, center[1]])

            self.rect = [[0, 0], np.array([self.size()]), 0]
            self.parent.lineSegROIs[self.id].sigRegionChangeFinished.connect(self.updateRect)
            self.sigRegionChangeFinished.connect(self.updateSize)
            self.sigRegionChangeFinished.connect(self.updateRectParams)
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

            self.setSize((np.linalg.norm(lineStart-lineEnd), self.size().y()))
            self.setPos(lineStart, finish=False)
            self.setAngle(360 * lineAngleRad / (2 * np.pi), finish=False)

            self.translate(-1.0 * self.size().x() * np.array([np.cos(lineAngleRad), np.sin(lineAngleRad)])
                           + 0.5 * self.size().y() * np.array([np.sin(lineAngleRad),-np.cos(lineAngleRad)]),
                           finish=False)

            self.rect = [lineStart + 0.5 * line * self.size().x(), np.array(self.size()), 360 * lineAngleRad / (2 * np.pi)]

            self.updateRectParams()

        def updateSize(self):
            self.rect[1] = np.array(self.size())
            self.updateRectParams()

        def updateRectParams(self):
            self.parent.fishMarkerRects[self.id] = self.rect
