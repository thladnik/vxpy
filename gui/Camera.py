"""
MappApp ./gui/Core.py - Custom addons which handle UI and visualization with camera process.
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
from PyQt5.QtWidgets import QLabel
import pyqtgraph as pg

import Config
import Def
from utils import geometry
import IPC
import routines.camera.Core

################################
# Live Camera Widget

class FrameStream(QtWidgets.QWidget):

    frame_routine = routines.camera.Core.Frames

    def __init__(self, parent, **kwargs):
        # Check if camera is being used (since detector relies on camera input)
        if not(Config.Camera[Def.CameraCfg.use]):
            self.moduleIsActive = False
            return
        self.moduleIsActive = True
        QtWidgets.QWidget.__init__(self, parent, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())

        # Get frame routine buffer
        self.frame_buffer = IPC.Routines.Camera.get_buffer(self.frame_routine)

        hspacer = QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout().addItem(hspacer, 0, 1)

        self.tab_camera_views = QtWidgets.QTabWidget()
        self.tab_camera_views.setTabPosition(QtWidgets.QTabWidget.West)
        self.layout().addWidget(self.tab_camera_views, 1, 0, 1, 2)

        # Add one view per camera device
        self.view_wdgts = dict()
        for device_id in Config.Camera[Def.CameraCfg.device_id]:
            self.view_wdgts[device_id] = FrameStream.CameraWidget(self, device_id, parent=self)
            self.tab_camera_views.addTab(self.view_wdgts[device_id], device_id.upper())

    def update_frame(self):
        for _, widget in self.view_wdgts.items():
            widget.update_frame()

    class CameraWidget(QtWidgets.QWidget):
        def __init__(self, main, device_id, **kwargs):
            QtWidgets.QWidget.__init__(self, **kwargs)
            self.main = main
            self.device_id = device_id

            # Set layout
            self.setLayout(QtWidgets.QHBoxLayout())

            self.lpanel = QtWidgets.QWidget()
            self.lpanel.setLayout(QtWidgets.QVBoxLayout())
            self.layout().addWidget(self.lpanel)

            # Add Rotate/flip controls
            self._rotation = 0
            self.cb_rotation = QtWidgets.QComboBox()
            self.lpanel.layout().addWidget(QtWidgets.QLabel('Rotation'))
            self.cb_rotation.addItems(['None', '90CCW', '180', '270CCW'])
            self.cb_rotation.currentIndexChanged.connect(lambda i: self.set_rotation(i))
            self.cb_rotation.currentIndexChanged.connect(self.update_frame)
            self.lpanel.layout().addWidget(self.cb_rotation)
            self._flip_ud = False
            self.check_flip_ud = QtWidgets.QCheckBox('Flip vertical')
            self.check_flip_ud.stateChanged.connect(lambda s: self.set_flip_ud(s))
            self.check_flip_ud.stateChanged.connect(self.update_frame)
            self.lpanel.layout().addWidget(self.check_flip_ud)
            self._flip_lr = False
            self.check_flip_lr = QtWidgets.QCheckBox('Flip horizontal')
            self.check_flip_lr.stateChanged.connect(lambda s: self.set_flip_lr(s))
            self.check_flip_lr.stateChanged.connect(self.update_frame)
            self.lpanel.layout().addWidget(self.check_flip_lr)
            spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
            self.lpanel.layout().addItem(spacer)

            # Add graphics widget
            self.graphics_widget = FrameStream.GraphicsWidget(self.main, parent=self)
            self.layout().addWidget(self.graphics_widget)

        def update_frame(self):
            idx, time, frame = self.main.frame_buffer.read(f'{self.device_id}_frame')

            if frame is None:
                return

            frame = np.rot90(frame.squeeze(), self._rotation)
            if self._flip_lr:
                frame = np.fliplr(frame)
            if self._flip_ud:
                frame = np.flipud(frame)

            #self.image_plot.vb.autoRange()

            self.graphics_widget.image_item.setImage(frame)

        def set_rotation(self, dir):
            self._rotation = dir

        def set_flip_ud(self, flip):
            self._flip_ud = flip

        def set_flip_lr(self, flip):
            self._flip_lr = flip

    class GraphicsWidget(pg.GraphicsLayoutWidget):

        def __init__(self, main, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            # Add plot
            self.image_plot = self.addPlot(0, 0, 1, 10)

            # Set up plot image item
            self.image_item = pg.ImageItem()
            self.image_plot.hideAxis('left')
            self.image_plot.hideAxis('bottom')
            self.image_plot.setAspectLocked(True)
            #self.image_plot.vb.setMouseEnabled(x=False, y=False)
            self.image_plot.addItem(self.image_item)


################################
# Eye Position Detector Widget

class EyePositionDetector(QtWidgets.QWidget):

    detection_routine = routines.camera.Core.EyePositionDetection

    def __init__(self, parent, **kwargs):
        # Check if camera is being used (since detector relies on camera input)
        if not(Config.Camera[Def.CameraCfg.use]):
            self.moduleIsActive = False
            return
        self.moduleIsActive = True

        QtWidgets.QWidget.__init__(self, parent, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.detection_buffer = IPC.Routines.Camera.get_buffer(self.detection_routine)

        from utils.gui import IntSliderWidget

        self.lpanel = QtWidgets.QWidget(self)
        self.lpanel.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.lpanel)

        # Set up left control panel
        self.lpanel.layout().addWidget(QLabel('<b>Eye detection</b>'))

        label_width = 125
        # Image threshold
        self.image_threshold = IntSliderWidget('Threshold', 1, 255, 60, label_width=label_width, step_size=1)
        self.image_threshold.connect_to_result(self.update_image_threshold)
        self.image_threshold.emit_current_value()
        self.lpanel.layout().addWidget(self.image_threshold)

        # Particle size
        self.particle_minsize = IntSliderWidget('Min. particle size',1, 1000, 60, label_width=label_width, step_size=1)
        self.particle_minsize.connect_to_result(self.update_particle_minsize)
        self.particle_minsize.emit_current_value()
        self.lpanel.layout().addWidget(self.particle_minsize)

        # Position calculation mode
        self.lpanel.layout().addWidget(QtWidgets.QLabel('Position calculation mode'))
        self.detection_mode = QtWidgets.QComboBox()
        self.detection_mode.currentTextChanged.connect(self.update_detection_mode)
        self.lpanel.layout().addWidget(self.detection_mode)
        self.detection_mode.addItems(
            [routines.camera.Core.EyePositionDetection.from_ellipse.__name__,
             routines.camera.Core.EyePositionDetection.feret_diameter.__name__])

        # Saccade detection
        self.lpanel.layout().addWidget(QLabel('<b>Saccade detection</b>'))
        self.sacc_threshold = IntSliderWidget('Sacc. threshold [deg/s]', 1, 10000, 2000, label_width=label_width, step_size=1)
        self.sacc_threshold.connect_to_result(self.update_sacc_threshold)
        self.sacc_threshold.emit_current_value()
        self.lpanel.layout().addWidget(self.sacc_threshold)

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.lpanel.layout().addItem(spacer)

        # Set up image plot
        self.graphics_widget = EyePositionDetector.GraphicsWidget(parent=self)
        self.graphics_widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Expanding)
        self.layout().addWidget(self.graphics_widget)

    def update_detection_mode(self,mode):
        IPC.rpc(Def.Process.Camera,
                routines.camera.Core.EyePositionDetection.set_detection_mode,
                mode)

    def update_image_threshold(self,threshold):
        IPC.rpc(Def.Process.Camera,
                routines.camera.Core.EyePositionDetection.set_threshold,
                threshold)

    def update_particle_minsize(self,minsize):
        IPC.rpc(Def.Process.Camera,
                routines.camera.Core.EyePositionDetection.set_min_particle_size,
                minsize)

    def update_sacc_threshold(self,sacc_threshold):
        IPC.rpc(Def.Process.Camera,
                routines.camera.Core.EyePositionDetection.set_saccade_threshold,
                sacc_threshold)

    def update_frame(self):
        idx, time, frame = self.detection_buffer.frame.read()
        frame = frame[0]

        if frame is None:
            return

        self.graphics_widget.image_item.setImage(np.rot90(frame, -1))


    class GraphicsWidget(pg.GraphicsLayoutWidget):
        def __init__(self, **kwargs):
            pg.GraphicsLayoutWidget.__init__(self, **kwargs)

            # Set up basics
            self.lines = dict()
            self.roi_params = dict()
            self.roi_rects = dict()
            self.subplots = dict()
            self.new_marker = None
            self.current_id = 0

            # Set context menu
            self.context_menu = QtWidgets.QMenu()

            # Set new line
            self.menu_new = QtWidgets.QAction('New ROI')
            self.menu_new.triggered.connect(self.add_marker)
            self.context_menu.addAction(self.menu_new)

            # Set up plot image item
            self.image_plot = self.addPlot(0, 0, 1, 10)
            self.image_item = pg.ImageItem()
            self.image_plot.hideAxis('left')
            self.image_plot.hideAxis('bottom')
            self.image_plot.setAspectLocked(True)
            self.image_plot.addItem(self.image_item)

            # Make subplots update with whole camera frame
            self.image_item.sigImageChanged.connect(self.update_subplots)
            # Bind mouse click event for drawing of lines
            self.image_plot.scene().sigMouseClicked.connect(self.mouse_clicked)
            # Bind context menu call function
            self.image_plot.vb.raiseContextMenu = self.raise_context_menu

        def resizeEvent(self, ev):
            pg.GraphicsLayoutWidget.resizeEvent(self, ev)
            self.set_eye_rect_plot_max_height()

        def set_eye_rect_plot_max_height(self):
            if not(hasattr(self, 'ci')):
                return
            self.ci.layout.setRowMaximumHeight(1, self.height()//6)

        def raise_context_menu(self, ev):
            self.context_menu.popup(QtCore.QPoint(ev.screenPos().x(), ev.screenPos().y()))

        def add_marker(self):
            if self.new_marker is not None:
                return
            self.new_marker = list()

        def mouse_clicked(self, ev):
            pos = self.image_plot.vb.mapSceneToView(ev.scenePos())

            # First click: start new line
            if self.new_marker is not None and len(self.new_marker) == 0:
                self.new_marker = [[pos.x(), pos.y()]]

            # Second click: end line and create rectangular ROI + subplot
            elif self.new_marker is not None and len(self.new_marker) == 1:
                # Set second point of line
                self.new_marker.append([pos.x(), pos.y()])

                # Create line
                line_seg_roi = EyePositionDetector.Line(self, self.current_id, self.new_marker,
                                                      pen=pg.mkPen(color='FF0000', width=2))
                self.lines[self.current_id] = line_seg_roi
                self.image_plot.vb.addItem(self.lines[self.current_id])

                # Create rect
                rect_roi = EyePositionDetector.Rect(self, self.current_id, self.new_marker)
                self.roi_rects[self.current_id] = rect_roi
                self.image_plot.vb.addItem(self.roi_rects[self.current_id])

                # Add subplot
                self.subplots[self.current_id] = dict()
                sp = self.addPlot(1, self.current_id)
                ii = pg.ImageItem()
                sp.hideAxis('left')
                sp.hideAxis('bottom')
                sp.setAspectLocked(True)
                sp.vb.setMouseEnabled(x=False, y=False)
                sp.addItem(ii)

                self.subplots[self.current_id]['imageitem'] = ii
                self.subplots[self.current_id]['plotitem'] = sp

                self.current_id += 1
                self.new_marker = None

        def update_subplots(self):

            # Draw rectangular ROIs
            routine = EyePositionDetector.detection_routine
            attr_path = f'{routine.__name__}/{routine.extracted_rect_prefix}'
            for id in self.roi_rects:
                idx, time, rect = IPC.Routines.Camera.read(f'{attr_path}{id}')
                rect = rect[0]

                if rect is None:
                    return

                self.subplots[id]['imageitem'].setImage(np.rot90(rect, -1))

    class Line(pg.LineSegmentROI):
        def __init__(self, parent, id, *args, **kwargs):
            self.parent = parent
            self.id = id
            pg.LineSegmentROI.__init__(self, *args, **kwargs, movable=False, removable=True)

    class Rect(pg.RectROI):

        def __init__(self, parent, id, coords):
            pg.RectROI.__init__(self, [0,0], [0,0], movable=False, centered=True, pen=(255,0,0))
            self.parent = parent
            self.id = id

            # Start position and size
            self.setPos(coords[0])
            line_length = np.linalg.norm(np.array(coords[0]) - np.array(coords[1]))
            self.setSize(line_length * np.array([0.8, 1.3]))

            self.parent.lines[self.id].sigRegionChangeFinished.connect(self.update_rect)
            self.sigRegionChangeFinished.connect(self.update_rect)

            self.update_rect()

        def update_rect(self):
            line_points = self.parent.lines[self.id].listPoints()
            line_coords = [[line_points[0].x(), line_points[0].y()], [line_points[1].x(), line_points[1].y()]]
            line_start = np.array(line_coords[0])
            lineEnd = np.array(line_coords[1])
            line = geometry.vecNormalize(lineEnd - line_start)
            line_angle_rad = np.arccos(np.dot(geometry.vecNormalize(np.array([-1.0,0.0])),line))

            if line[1] > 0:
               line_angle_rad = 2 * np.pi - line_angle_rad

            self.setPos(line_start, finish=False)
            self.setAngle(360 * line_angle_rad / (2 * np.pi), finish=False)

            self.translate(-0.5 * self.size().x() * np.array([np.cos(line_angle_rad), np.sin(line_angle_rad)])
                           + 0.5 * self.size().y() * np.array([np.sin(line_angle_rad),-np.cos(line_angle_rad)]),
                           finish=False)

            self.rect = [line_start, np.array(self.size()), 360 * line_angle_rad / (2 * np.pi)]

            # Set updates ROI parameters
            self.parent.roi_params[self.id] = self.rect
            # Send update to detector routine
            IPC.rpc(Def.Process.Camera, routines.camera.Core.EyePositionDetection.set_roi, self.id, self.rect)
            #routines.camera.Core.EyePositionDetection.set_roi(self.id, self.rect)