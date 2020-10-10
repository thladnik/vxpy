"""
MappApp ./gui/CameraRoutines.py - Custom addons which handle UI and visualization with camera process.
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
import routines.camera.CameraRoutines

################################
# Live Camera Widget

class LiveCamera(QtWidgets.QWidget):

    def __init__(self, parent, **kwargs):
        ### Set module always to active
        self.moduleIsActive = True
        QtWidgets.QWidget.__init__(self, parent, **kwargs)

        self.setWindowTitle('Live camera')

        self.setLayout(QtWidgets.QGridLayout())

        self.fps_counter = QtWidgets.QLineEdit('FPS')
        self.fps_counter.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.layout().addWidget(self.fps_counter, 0, 0)
        hspacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout().addItem(hspacer, 0, 1)

        self.tab_camera_views = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_camera_views, 1, 0, 1, 2)

        self.view_wdgts = dict()
        for device_id, res_x in zip(
                Config.Camera[Def.CameraCfg.device_id],
                Config.Camera[Def.CameraCfg.res_x]):

            self.view_wdgts[device_id] = LiveCamera.GraphicsWidget(parent=self)
            self.tab_camera_views.addTab(self.view_wdgts[device_id], device_id.upper())


    def updateFrame(self):

        ### Update current frame
        for device_id, wdgt in self.view_wdgts.items():
            _, frame = IPC.Routines.Camera.read('FrameRoutine/{}_frame'.format(device_id))

            if frame is None:
                continue

            wdgt.imageItem.setImage(np.rot90(frame.squeeze(), -1))

        ### Print fps
        _, frametimes = IPC.Routines.Camera.read('FrameRoutine/time', last=50)
        if frametimes[0] is None:
            return

        fps = 1./np.mean(np.diff(frametimes))
        self.fps_counter.setText('FPS {:.2f}'.format(fps))

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

            self.textItem = pg.TextItem('', color=(255,0,0))
            self.imagePlot.addItem(self.textItem)


################################
# Eye Position Detector Widget
from routines.camera import CameraRoutines

class SliderWidget(QtWidgets.QWidget):

    def __init__(self, slider_name, min_val, max_val, default_val, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self.setLayout(QtWidgets.QGridLayout())

        self.layout().addWidget(QtWidgets.QLabel(slider_name), 0, 0)
        self.lineedit = QtWidgets.QLineEdit()
        self.lineedit.setEnabled(False)
        self.layout().addWidget(self.lineedit, 0, 1)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        #self.slider.setTickInterval(int(max_val - min_val / 10))
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.valueChanged.connect(lambda: self.lineedit.setText(str(self.slider.value())))

        self.slider.setValue(default_val)
        self.layout().addWidget(self.slider, 1, 0, 1, 2)

    def emitValueChanged(self):
        self.slider.valueChanged.emit(self.slider.value())


class EyePositionDetector(QtWidgets.QWidget):

    detector_routine = CameraRoutines.EyePosDetectRoutine
    camera_device_id = detector_routine.camera_device_id

    def __init__(self, parent, **kwargs):
        ### Check if camera is being used (since detector relies on camera input)
        if not(Config.Camera[Def.CameraCfg.use]):
            self.moduleIsActive = False
            return
        self.moduleIsActive = True

        QtWidgets.QWidget.__init__(self, parent, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        ### Panel
        self.panel_wdgt = QtWidgets.QWidget(parent=self)
        self.panel_wdgt.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding)
        self.panel_wdgt.setMinimumWidth(200)
        self.panel_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.panel_wdgt)

        ## Mode
        self.panel_wdgt.layout().addWidget(QtWidgets.QLabel('Detection mode'))
        self.panel_wdgt.mode = QtWidgets.QComboBox()
        self.panel_wdgt.mode.currentTextChanged.connect(lambda:
                                                    IPC.rpc(Def.Process.Camera,
                                                            routines.camera.CameraRoutines.EyePosDetectRoutine.set_detection_mode,
                                                            self.panel_wdgt.mode.currentText()))
        self.panel_wdgt.layout().addWidget(self.panel_wdgt.mode)
        self.panel_wdgt.mode.addItems([routines.camera.CameraRoutines.EyePosDetectRoutine.feret_diameter.__name__,
                                       routines.camera.CameraRoutines.EyePosDetectRoutine.longest_distance.__name__])

        ## Threshold
        self.panel_wdgt.thresh = SliderWidget('Threshold', 1, 255, 60)
        self.panel_wdgt.thresh.slider.valueChanged.connect(lambda:
                                                    IPC.rpc(Def.Process.Camera,
                                                            routines.camera.CameraRoutines.EyePosDetectRoutine.set_threshold,
                                                            self.panel_wdgt.thresh.slider.value()))
        self.panel_wdgt.layout().addWidget(self.panel_wdgt.thresh)
        self.panel_wdgt.thresh.emitValueChanged()

        ## Max value
        self.panel_wdgt.maxImValue = SliderWidget('Max. value', 1, 255, 255)
        self.panel_wdgt.maxImValue.slider.valueChanged.connect(lambda:
                                                    IPC.rpc(Def.Process.Camera,
                                                            routines.camera.CameraRoutines.EyePosDetectRoutine.set_max_im_value,
                                                            self.panel_wdgt.maxImValue.slider.value()))
        self.panel_wdgt.layout().addWidget(self.panel_wdgt.maxImValue)
        self.panel_wdgt.maxImValue.emitValueChanged()

        ## Min particle size
        self.panel_wdgt.minSize = SliderWidget('Min. particle size', 1, 1000, 20)
        self.panel_wdgt.minSize.slider.valueChanged.connect(lambda:
                                                IPC.rpc(Def.Process.Camera,
                                                        routines.camera.CameraRoutines.EyePosDetectRoutine.set_min_particle_size,
                                                        self.panel_wdgt.minSize.slider.value()))
        self.panel_wdgt.layout().addWidget(self.panel_wdgt.minSize)
        self.panel_wdgt.minSize.emitValueChanged()

        self.panel_wdgt.layout().addItem(QtWidgets.QSpacerItem(1, 1,
                                                                 QtWidgets.QSizePolicy.Maximum,
                                                                 QtWidgets.QSizePolicy.MinimumExpanding))

        ### Image plot
        self.graphicsWidget = EyePositionDetector.GraphicsWidget(parent=self)
        self.graphicsWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        self.layout().addWidget(self.graphicsWidget)

    def updateFrame(self):
        idx, frame = IPC.Routines.Camera.read(f'{self.detector_routine.__name__}/frame')

        if not(frame is None):
            self.graphicsWidget.imageItem.setImage(np.rot90(frame, -1))


    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            self.rois = dict()

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
            #self.imagePlot.vb.setMouseEnabled(x=False, y=False)
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
            idx, extractedRects = IPC.Routines.Camera.read('EyePosDetectRoutine/extractedRects')
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
            self.parent.rois[self.id] = self.rect
            ### Send update to detector routine
            IPC.rpc(Def.Process.Camera, routines.camera.CameraRoutines.EyePosDetectRoutine.set_roi, self.id, self.rect)


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
        frame = IPC.Routines.Camera.read('FrameBuffer/frame')
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
