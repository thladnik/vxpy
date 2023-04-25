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
import cv2
import numpy as np
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QLabel
import pyqtgraph as pg
from scipy.spatial import distance

from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.devices.camera as vxcamera
import vxpy.core.dependency as vxdependency
import vxpy.core.io as vxio
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.definitions import *
from vxpy.utils import geometry
from vxpy.utils.widgets import IntSliderWidget, UniformWidth

log = vxlogger.getLogger(__name__)


class EyePositionDetectionAddon(vxui.CameraAddonWidget):

    display_name = 'Eye position detection'

    _vspacer = QtWidgets.QSpacerItem(1, 20,
                                     QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def __init__(self, *args, **kwargs):
        vxui.CameraAddonWidget.__init__(self, *args, **kwargs)

        self.routine = EyePositionDetectionRoutine.instance

        self.central_widget.setLayout(QtWidgets.QVBoxLayout())

        self.ctrl_panel = QtWidgets.QWidget(self)
        self.ctrl_panel.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Maximum)
        self.ctrl_panel.setLayout(QtWidgets.QVBoxLayout())
        self.central_widget.layout().addWidget(self.ctrl_panel)

        # Set up control panel
        self.ctrl_panel.layout().addWidget(QLabel('<b>Eye detection</b>'))

        label_width = 125
        self.uniform_label_width = UniformWidth()
        # Image threshold
        self.image_threshold = IntSliderWidget(self, 'Threshold',
                                               limits=(1, 255), default=self.routine.binary_threshold,
                                               label_width=label_width, step_size=1)
        self.image_threshold.connect_callback(self.update_image_threshold)
        # self.image_threshold.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.image_threshold)
        self.uniform_label_width.add_widget(self.image_threshold.label)

        # Particle size
        self.particle_minsize = IntSliderWidget(self, 'Min. particle size',
                                                limits=(1, 1000), default=self.routine.min_particle_size,
                                                label_width=label_width, step_size=1)
        self.particle_minsize.connect_callback(self.update_particle_minsize)
        # self.particle_minsize.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.particle_minsize)
        self.uniform_label_width.add_widget(self.particle_minsize.label)

        # Saccade detection
        self.ctrl_panel.layout().addItem(self._vspacer)
        self.ctrl_panel.layout().addWidget(QLabel('<b>Saccade detection</b>'))
        self.sacc_threshold = IntSliderWidget(self, 'Sacc. threshold [deg/s]',
                                              limits=(1, 10000), default=self.routine.saccade_threshold,
                                              label_width=label_width, step_size=1)
        self.sacc_threshold.connect_callback(self.update_sacc_threshold)
        # self.sacc_threshold.emit_current_value()
        self.ctrl_panel.layout().addWidget(self.sacc_threshold)
        self.uniform_label_width.add_widget(self.sacc_threshold.label)

        # Set up image plot
        self.graphics_widget = FramePlot(parent=self)
        self.graphics_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.central_widget.layout().addWidget(self.graphics_widget)

        # Add button for new ROI creation
        self.ctrl_panel.layout().addItem(self._vspacer)
        self.add_roi_btn = QtWidgets.QPushButton('Add ROI')
        self.add_roi_btn.clicked.connect(self.graphics_widget.add_marker)
        self.ctrl_panel.layout().addWidget(self.add_roi_btn)

        self.connect_to_timer(self.update_frame)

    def update_image_threshold(self, im_thresh):
        self.call_routine(EyePositionDetectionRoutine.set_threshold, im_thresh)

    def update_particle_minsize(self, minsize):
        self.call_routine(EyePositionDetectionRoutine.set_min_particle_size, minsize)

    def update_sacc_threshold(self, sacc_thresh):
        self.call_routine(EyePositionDetectionRoutine.set_saccade_threshold, sacc_thresh)

    def update_frame(self):
        idx, time, frame = vxattribute.read_attribute(EyePositionDetectionRoutine.frame_name)
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
        routine_cls = EyePositionDetectionRoutine
        for roi_id in self.roi_rects:
            rect_data = vxattribute.read_attribute(f'{routine_cls.extracted_rect_prefix}{roi_id}')

            # If this rect does not exist, skip
            if rect_data is None:
                continue

            idx, time, rect = rect_data
            rect = rect[0]

            if rect is None:
                return

            self.subplots[roi_id]['imageitem'].setImage(np.rot90(rect, -1))


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
        vxipc.rpc(PROCESS_CAMERA, EyePositionDetectionRoutine.set_roi, self.id, self.rect)


class EyePositionDetectionRoutine(vxroutine.CameraRoutine):

    # Set required device
    camera_device_id = 'fish_embedded'

    routine_prefix = 'eyepos_'

    extracted_rect_prefix = f'{routine_prefix}extracted_rect_'
    ang_le_pos_prefix = f'{routine_prefix}ang_le_pos_'
    ang_re_pos_prefix = f'{routine_prefix}ang_re_pos_'
    ang_le_vel_prefix = f'{routine_prefix}ang_le_vel_'
    ang_re_vel_prefix = f'{routine_prefix}ang_re_vel_'
    le_sacc_prefix = f'{routine_prefix}le_saccade_'
    re_sacc_prefix = f'{routine_prefix}re_saccade_'
    frame_name = f'{routine_prefix}frame'
    sacc_trigger_name = f'{routine_prefix}saccade_trigger'

    binary_threshold: int = None
    min_particle_size: int = None
    saccade_threshold: int = None

    def __init__(self, *args, **kwargs):
        vxroutine.CameraRoutine.__init__(self, *args, **kwargs)

        roi_maxnum = kwargs.get('roi_maxnum')
        if roi_maxnum is not None and isinstance(roi_maxnum, int):
            self.roi_maxnum = roi_maxnum
        else:
            self.roi_maxnum = 5

        thresh = kwargs.get('thresh')
        if thresh is not None and isinstance(thresh, int):
            self.binary_threshold = thresh
        else:
            self.binary_threshold = 60

        min_size = kwargs.get('min_size')
        if min_size is not None and isinstance(min_size, int):
            self.min_particle_size = min_size
        else:
            self.min_particle_size = 60

        saccade_threshold = kwargs.get('saccade_threshold')
        if saccade_threshold is not None and isinstance(saccade_threshold, int):
            self.saccade_threshold = saccade_threshold
        else:
            self.saccade_threshold = 600

        log.info(f'Set max number of ROIs to {self.roi_maxnum}')

        self.rois = {}

    def require(self):
        vxdependency.require_camera_device(self.camera_device_id)

        # Get camera specs
        camera = vxcamera.get_camera_by_id(self.camera_device_id)
        if camera is None:
            log.error(f'Camera {self.camera_device_id} unavailable for eye position tracking')
            return

        # Add frame
        vxattribute.ArrayAttribute(self.frame_name, (camera.width, camera.height), vxattribute.ArrayType.uint8)

        # Add saccade trigger buffer
        vxattribute.ArrayAttribute(self.sacc_trigger_name, (1, ), vxattribute.ArrayType.bool)

        # Add attributes per fish
        for id in range(self.roi_maxnum):
            # Rectangle
            vxattribute.ObjectAttribute(f'{self.extracted_rect_prefix}{id}')

            # Position
            vxattribute.ArrayAttribute(f'{self.ang_le_pos_prefix}{id}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.ang_re_pos_prefix}{id}', (1,), vxattribute.ArrayType.float64)

            # Velocity
            vxattribute.ArrayAttribute(f'{self.ang_le_vel_prefix}{id}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.ang_re_vel_prefix}{id}', (1,), vxattribute.ArrayType.float64)

            # Saccade detection
            vxattribute.ArrayAttribute(f'{self.le_sacc_prefix}{id}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.re_sacc_prefix}{id}', (1,), vxattribute.ArrayType.float64)

    def initialize(self):
        pass

    @vxroutine.CameraRoutine.callback
    def set_threshold(self, thresh):
        self.binary_threshold = thresh

    @vxroutine.CameraRoutine.callback
    def set_min_particle_size(self, size):
        self.min_particle_size = size

    @vxroutine.CameraRoutine.callback
    def set_saccade_threshold(self, thresh):
        self.saccade_threshold = thresh

    @vxroutine.CameraRoutine.callback
    def set_roi(self, roi_id: int, params):

        roi_num = -1

        # Check if new ROI needs to be created
        if roi_id not in self.rois:
            if len(self.rois) >= self.roi_maxnum:
                log.error(f'Maximum number of ROIs for eye tracking ({self.roi_maxnum}) exceeded')
                return
            log.info(f'Create new ROI at {params}')
            roi_num = len(self.rois)
            self._create_roi(roi_num)

            # For first ROI: also add the generic saccade trigger output
            if len(self.rois) == 0:
                # Set saccade trigger (LE and RE) signal to "saccade_trigger" channel by default
                vxio.set_digital_output('saccade_trigger_output', self.sacc_trigger_name)
                vxui.register_with_plotter(self.sacc_trigger_name)

        # Set parameters

        # Preserve corresponding roi_num, if ROI is an existing one
        if roi_num < 0:
            roi_num = self.rois[roi_id][0]

        # Brief clarification
        #  roi_id: externally generated id, provided for example by a UI widget
        #  roi_num: internally generated, continuous number that is used in attributes for example
        self.rois[roi_id] = (roi_num, params)

    def _create_roi(self, roi_num: int):
        # Resgister buffer attributes with plotter

        # Position
        vxui.register_with_plotter(f'{self.ang_le_pos_prefix}{roi_num}', name=f'eye_pos(LE {roi_num})', axis='eye_pos',
                                   units='deg')
        vxui.register_with_plotter(f'{self.ang_re_pos_prefix}{roi_num}', name=f'eye_pos(RE {roi_num})', axis='eye_pos',
                                   units='deg')

        # Velocity
        vxui.register_with_plotter(f'{self.ang_le_vel_prefix}{roi_num}', name=f'eye_vel(LE {roi_num})', axis='eye_vel',
                                   units='deg/s')
        vxui.register_with_plotter(f'{self.ang_re_vel_prefix}{roi_num}', name=f'eye_vel(RE {roi_num})', axis='eye_vel',
                                   units='deg/s')

        # Saccade trigger
        vxui.register_with_plotter(f'{self.le_sacc_prefix}{roi_num}', name=f'sacc(LE {roi_num})', axis='sacc')
        vxui.register_with_plotter(f'{self.re_sacc_prefix}{roi_num}', name=f'sacc(RE {roi_num})', axis='sacc')

        # Add attributes to save-to-file list:
        vxattribute.write_to_file(self, f'{self.ang_le_pos_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_re_pos_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_le_vel_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_re_vel_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.le_sacc_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.re_sacc_prefix}{roi_num}')

    def from_ellipse(self, rect):
        # Formatting for drawing
        line_thickness = np.ceil(np.mean(rect.shape) / 50).astype(int)
        line_thickness = 1 if line_thickness == 0 else line_thickness
        marker_size = line_thickness * 5

        # Set rect center
        rect_center = (rect.shape[1] // 2, rect.shape[0] // 2)

        # Apply threshold
        _, thresh = cv2.threshold(rect[:,:], self.binary_threshold, 255, cv2.THRESH_BINARY_INV)

        # Detect contours
        cnts, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cnts = list(cnts)

        # Make RGB
        thresh = np.stack((thresh, thresh, thresh), axis=-1)

        # Collect contour parameters and filter contours
        areas = list()
        barycenters = list()
        hulls = list()
        feret_points = list()
        thetas = list()
        axes = list()
        dists = list()
        i = 0
        while i < len(cnts):

            cnt = cnts[i]
            M = cv2.moments(cnt)
            A = M['m00']

            # Discard if contour has no area
            if A < self.min_particle_size:
                del cnts[i]
                continue

            # Particle center
            center = (M['m10']/A, M['m01']/A)

            # Hull of particle
            hull = cv2.convexHull(cnt).squeeze()

            # Ellipse axes lengths
            a = M['m20'] / M['m00'] - center[0] ** 2
            b = 2 * (M['m11'] / M['m00'] - center[0] * center[1])
            c = M['m02'] / M['m00'] - center[1] ** 2

            # Avoid divisions by zero
            if (a - c) == 0.:
                del cnts[i]
                continue

            # Ellipse's major axis angle
            theta = (1 / 2 * np.arctan(b / (a - c)) + (a < c) - 1) / np.pi * 180 #* np.pi / 2
            W = np.sqrt(8 * (a + c - np.sqrt(b ** 2 + (a - c) ** 2))) / 2
            L = np.sqrt(8 * (a + c + np.sqrt(b ** 2 + (a - c) ** 2))) / 2

            thetas.append(theta)
            barycenters.append(center)
            axes.append((W, L))
            areas.append(A)
            hulls.append(hull)
            dists.append(distance.euclidean(center, rect_center))
            feret_points.append((hull[np.argmin(hull[:,1])], hull[np.argmax(hull[:,1])]))

            i += 1

        # Additional filtering of particles to idenfity both eyes if more than 2
        if len(cnts) > 2:
            dists, areas, barycenters, hulls, feret_points, thetas, axes = \
                list(zip(*sorted(list(zip(dists, areas, barycenters, hulls, feret_points, thetas, axes)))[:2]))

        forward_vec = np.array([0,-1])
        forward_vec_norm = forward_vec / np.linalg.norm(forward_vec)
        # Draw rect center and midline marker for debugging
        # (Important: this has to happen AFTER detection of contours,
        # as it alters the tresh'ed image)
        cv2.drawMarker(thresh, rect_center, (0, 255, 0), cv2.MARKER_DIAMOND, marker_size * 2, line_thickness)
        cv2.arrowedLine(thresh,
                        tuple(rect_center), tuple((rect_center + rect.shape[0]/3 * forward_vec_norm).astype(int)),
                        (0, 255, 0), line_thickness, tipLength=0.3)

        # Draw hull contours for debugging (before possible premature return)
        cv2.drawContours(thresh, hulls, -1, (128, 128, 0), line_thickness)

        # If less than two particles, return
        if len(cnts) < 2:
            return [np.nan, np.nan], thresh

        # At this point there should only be 2 particles left
        le_idx = 0 if (barycenters[0][0] < rect_center[0]) else 1
        re_idx = 1 if (barycenters[0][0] < rect_center[0]) else 0

        try:
            for center, axis, theta in zip(barycenters, axes, thetas):
                center = tuple((int(i) for i in center))
                axis = tuple((int(i) for i in axis))
                angle = float(theta)
                start_angle = 0.
                end_angle = 360.
                color = (255, 0, 0)

                cv2.ellipse(thresh,
                            center,
                            axis,
                            angle, start_angle, end_angle, color, line_thickness)
        except Exception as exc:
            import traceback
            traceback.print_exc()

        return [thetas[le_idx], thetas[re_idx]], thresh

    def main(self, **frames):

        # Read frame
        frame = frames.get(self.camera_device_id)

        # Check if frame was returned
        if frame is None:
            return

        # Reduce to mono
        if frame.ndim > 2:
            frame = frame[:,:,0]

        # Write frame to buffer
        vxattribute.write_attribute(self.frame_name, frame.T)

        # If there are no ROIs, there's nothing to detect
        if len(self.rois) == 0:
            return

        # If eyes were marked: iterate over ROIs and extract eye positions
        saccade_happened = False
        for roi_id, (roi_num, rect_params) in self.rois.items():

            # Extract rectanglular ROI

            # Get rect and frame parameters
            center, size, angle = rect_params[0], rect_params[1], rect_params[2]
            center, size = tuple(map(int, center)), tuple(map(int, size))
            height, width = frame.shape[0], frame.shape[1]

            # Rotate
            M = cv2.getRotationMatrix2D(center, angle, 1)
            rotFrame = cv2.warpAffine(frame, M, (width, height))

            # Crop rect from frame
            cropRect = cv2.getRectSubPix(rotFrame, size, center)

            # Rotate rect so that "up" direction in image corresponds to "foward" for the fish
            center = (size[0]/2, size[1]/2)
            width, height = size
            M = cv2.getRotationMatrix2D(center, 90, 1)
            absCos = abs(M[0, 0])
            absSin = abs(M[0, 1])

            # New bound width/height
            wBound = int(height * absSin + width * absCos)
            hBound = int(height * absCos + width * absSin)

            # Subtract old image center
            M[0, 2] += wBound / 2 - center[0]
            M[1, 2] += hBound / 2 - center[1]
            # Rotate
            rot_rect = cv2.warpAffine(cropRect, M, (wBound, hBound))

            # Calculate eye angular POSITIONS

            # Apply detection function on cropped rect which contains eyes
            (le_pos, re_pos), new_rect = self.from_ellipse(rot_rect)

            # Get shared attributes
            le_pos_attr = vxattribute.get_attribute(f'{self.ang_le_pos_prefix}{roi_num}')
            re_pos_attr = vxattribute.get_attribute(f'{self.ang_re_pos_prefix}{roi_num}')
            le_vel_attr = vxattribute.get_attribute(f'{self.ang_le_vel_prefix}{roi_num}')
            re_vel_attr = vxattribute.get_attribute(f'{self.ang_re_vel_prefix}{roi_num}')
            le_sacc_attr = vxattribute.get_attribute(f'{self.le_sacc_prefix}{roi_num}')
            re_sacc_attr = vxattribute.get_attribute(f'{self.re_sacc_prefix}{roi_num}')
            rect_roi_attr = vxattribute.get_attribute(f'{self.extracted_rect_prefix}{roi_num}')

            # Calculate eye angular VELOCITIES
            _, _, last_le_pos = le_pos_attr.read()
            last_le_pos = last_le_pos[0]
            _, last_time, last_re_pos = re_pos_attr.read()
            last_re_pos = last_re_pos[0]
            last_time = last_time[-1]
            if last_time is None:
                last_time = -np.inf

            # Calculate time elapsed since last frame
            current_time = vxipc.get_time()
            dt = (current_time - last_time)

            # Calculate velocities
            le_vel = np.abs((le_pos - last_le_pos) / dt)
            re_vel = np.abs((re_pos - last_re_pos) / dt)

            # Calculate saccade trigger
            _, _, last_le_vel = le_vel_attr.read()
            last_le_vel = last_le_vel[0]
            _, _, last_re_vel = re_vel_attr.read()
            last_re_vel = last_re_vel[0]

            le_sacc = int(last_le_vel < self.saccade_threshold < le_vel)
            re_sacc = int(last_re_vel < self.saccade_threshold < re_vel)

            is_saccade = bool(le_sacc) or bool(re_sacc)
            saccade_happened = saccade_happened or is_saccade

            # Write to buffer
            le_pos_attr.write(le_pos)
            re_pos_attr.write(re_pos)
            le_vel_attr.write(le_vel)
            re_vel_attr.write(re_vel)

            le_sacc_attr.write(le_sacc)
            re_sacc_attr.write(re_sacc)

            # Set current rect ROI data
            rect_roi_attr.write(new_rect)

        # Write saccade_happened trigger attribute (this is evaluated for all eyes of all ROIs)
        vxattribute.write_attribute(self.sacc_trigger_name, saccade_happened)
