"""
MappApp ./gui/camera/zf_tracking_widgets.py
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
from __future__ import annotations
import numpy as np
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QLabel
import pyqtgraph as pg

from vxpy.definitions import *
import vxpy.core.ipc as vxipc
from vxpy.api.attribute import read_attribute
import vxpy.core.ui as vxui
from vxpy.routines import zf_tracking
from vxpy.utils import geometry
from vxpy.utils.widgets import IntSliderWidget, UniformWidth


class EyePositionDetector(vxui.CameraAddonWidget):

    _vspacer = QtWidgets.QSpacerItem(1, 20,
                                     QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def __init__(self, *args, **kwargs):

        vxui.CameraAddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.ctrl_panel = QtWidgets.QWidget(self)
        self.ctrl_panel.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Maximum)
        self.ctrl_panel.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.ctrl_panel)

        # Set up left control panel
        self.ctrl_panel.layout().addWidget(QLabel('<b>Eye detection</b>'))

        label_width = 125
        self.uniform_label_width = UniformWidth()
        # Image threshold
        self.image_threshold = IntSliderWidget(self, 'Threshold',
                                               limits=(1, 255), default=60,
                                               label_width=label_width, step_size=1)
        self.image_threshold.connect_callback(self.update_image_threshold)
        self.image_threshold.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.image_threshold)
        self.uniform_label_width.add_widget(self.image_threshold.label)

        # Particle size
        self.particle_minsize = IntSliderWidget(self, 'Min. particle size',
                                                limits=(1, 1000), default=60,
                                                label_width=label_width, step_size=1)
        self.particle_minsize.connect_callback(self.update_particle_minsize)
        self.particle_minsize.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.particle_minsize)
        self.uniform_label_width.add_widget(self.particle_minsize.label)

        # Saccade detection
        self.ctrl_panel.layout().addItem(self._vspacer)
        self.ctrl_panel.layout().addWidget(QLabel('<b>Saccade detection</b>'))
        self.sacc_threshold = IntSliderWidget(self, 'Sacc. threshold [deg/s]',
                                              limits=(1, 10000), default=2000,
                                              label_width=label_width, step_size=1)
        self.sacc_threshold.connect_callback(self.update_sacc_threshold)
        self.sacc_threshold.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.sacc_threshold)
        self.uniform_label_width.add_widget(self.sacc_threshold.label)

        # Set up image plot
        self.graphics_widget = FramePlot(parent=self)
        self.graphics_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.layout().addWidget(self.graphics_widget)

        # Add button for new ROI creation
        self.ctrl_panel.layout().addItem(self._vspacer)
        self.add_roi_btn = QtWidgets.QPushButton('Add ROI')
        self.add_roi_btn.clicked.connect(self.graphics_widget.add_marker)
        self.ctrl_panel.layout().addWidget(self.add_roi_btn)

        self.connect_to_timer(self.update_frame)

    def update_image_threshold(self, im_thresh):
        self.call_routine(zf_tracking.EyePositionDetection.set_threshold, im_thresh)

    def update_particle_minsize(self, minsize):
        self.call_routine(zf_tracking.EyePositionDetection.set_min_particle_size, minsize)

    def update_sacc_threshold(self, sacc_thresh):
        self.call_routine(zf_tracking.EyePositionDetection.set_saccade_threshold, sacc_thresh)

    def update_frame(self):
        idx, time, frame = read_attribute(zf_tracking.EyePositionDetection.frame_name)
        frame = frame[0]

        if frame is None:
            return

        self.graphics_widget.image_item.setImage(frame)


class FramePlot(pg.GraphicsLayoutWidget):
    def __init__(self, **kwargs):
        pg.GraphicsLayoutWidget.__init__(self, **kwargs)

        # Set up basics
        self.lines = dict()
        self.roi_params = dict()
        self.roi_rects = dict()
        self.subplots = dict()
        self.new_marker = None
        self.current_id = 0

        # Set up plot image item
        self.image_plot = self.addPlot(0, 0, 1, 10)
        self.image_item = pg.ImageItem()
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)
        self.image_plot.addItem(self.image_item)
        self.image_plot.invertY(True)

        # Make subplots update with whole camera frame
        self.image_item.sigImageChanged.connect(self.update_subplots)
        # Bind mouse click event for drawing of lines
        self.image_plot.scene().sigMouseClicked.connect(self.mouse_clicked)

    def resizeEvent(self, ev):
        pg.GraphicsLayoutWidget.resizeEvent(self, ev)

        # Update widget height
        if hasattr(self, 'ci'):
            self.ci.layout.setRowMaximumHeight(1, self.height() // 6)

    def add_marker(self):
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
            line_seg_roi = Line(self, self.current_id, self.new_marker,
                                pen=pg.mkPen(color=pg.mkColor((1.0, 0.0, 0.0)), width=2))
            self.lines[self.current_id] = line_seg_roi
            self.image_plot.vb.addItem(self.lines[self.current_id])

            # Create rect
            rect_roi = Rect(self, self.current_id, self.new_marker)
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
        routine_cls = zf_tracking.EyePositionDetection
        for id in self.roi_rects:
            idx, time, rect = read_attribute(f'{routine_cls.extracted_rect_prefix}{id}')
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
        pg.RectROI.__init__(self, [0, 0], [0, 0], movable=False, centered=True, pen=(255, 0, 0))
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
        line_angle_rad = np.arccos(np.dot(geometry.vecNormalize(np.array([-1.0, 0.0])), line))

        if line[1] > 0:
            line_angle_rad = 2 * np.pi - line_angle_rad

        self.setPos(line_start, finish=False)
        self.setAngle(360 * line_angle_rad / (2 * np.pi), finish=False)

        self.translate(-0.5 * self.size().x() * np.array([np.cos(line_angle_rad), np.sin(line_angle_rad)])
                       + 0.5 * self.size().y() * np.array([np.sin(line_angle_rad), -np.cos(line_angle_rad)]),
                       finish=False)

        self.rect = [line_start, np.array(self.size()), 360 * line_angle_rad / (2 * np.pi)]

        # Set updates ROI parameters
        self.parent.roi_params[self.id] = self.rect
        # Send update to detector routine
        vxipc.rpc(PROCESS_CAMERA, zf_tracking.EyePositionDetection.set_roi, self.id, self.rect)
