"""Eye tracking for zebrafish larvae - routine and user interface
"""
from __future__ import annotations

from typing import Dict, Hashable, List, Tuple, Union

import cv2
import numpy as np
from PySide6 import QtWidgets, QtCore
import pyqtgraph as pg
from scipy.spatial import distance

import vxpy.core.attribute as vxattribute
import vxpy.core.devices.camera as vxcamera
import vxpy.core.dependency as vxdependency
import vxpy.core.io as vxio
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.utils.widgets import Checkbox, DoubleSliderWidget, IntSliderWidget, UniformWidth

log = vxlogger.getLogger(__name__)


class ZFEyeTrackingUI(vxui.CameraAddonWidget):
    display_name = 'ZF eye tracking'

    _vspacer = QtWidgets.QSpacerItem(1, 20,
                                     QtWidgets.QSizePolicy.Policy.Maximum,
                                     QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def __init__(self, *args, **kwargs):
        vxui.CameraAddonWidget.__init__(self, *args, **kwargs)

        self.central_widget.setLayout(QtWidgets.QHBoxLayout())

        # Set up control panel
        self.ctrl_panel = QtWidgets.QWidget(self)
        self.ctrl_panel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                      QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.ctrl_panel.setLayout(QtWidgets.QVBoxLayout())
        self.central_widget.layout().addWidget(self.ctrl_panel)

        self.uniform_label_width = UniformWidth()

        # Image processing
        self.img_proc = QtWidgets.QGroupBox('Image processing')
        self.ctrl_panel.layout().addWidget(self.img_proc)
        self.img_proc.setLayout(QtWidgets.QVBoxLayout())
        self.use_img_corr = Checkbox(self, 'Use image correction',
                                     default=ZFEyeTracking.instance().use_image_correction)
        self.use_img_corr.connect_callback(self.update_use_img_corr)
        self.uniform_label_width.add_widget(self.use_img_corr.label)
        self.img_proc.layout().addWidget(self.use_img_corr)
        self.img_contrast = DoubleSliderWidget(self.ctrl_panel, 'Contrast', default=ZFEyeTracking.instance().contrast,
                                               limits=(0, 3), step_size=0.01)
        self.img_contrast.connect_callback(self.update_contrast)
        self.uniform_label_width.add_widget(self.img_contrast.label)
        self.img_proc.layout().addWidget(self.img_contrast)
        self.img_brightness = IntSliderWidget(self.ctrl_panel, 'Brightness',
                                              default=ZFEyeTracking.instance().brightness, limits=(-200, 200))
        self.img_brightness.connect_callback(self.update_brightness)
        self.uniform_label_width.add_widget(self.img_brightness.label)
        self.img_proc.layout().addWidget(self.img_brightness)
        self.use_motion_corr = Checkbox(self, 'Use motion correction',
                                        default=ZFEyeTracking.instance().use_motion_correction)
        self.use_motion_corr.connect_callback(self.update_use_motion_corr)
        self.uniform_label_width.add_widget(self.use_motion_corr.label)
        self.img_proc.layout().addWidget(self.use_motion_corr)

        # Eye position detection
        self.eye_detect = QtWidgets.QGroupBox('Eye position detection')
        self.eye_detect.setLayout(QtWidgets.QVBoxLayout())
        self.ctrl_panel.layout().addWidget(self.eye_detect)

        # Flip direction option
        self.flip_direction = Checkbox(self, 'Flip directions', ZFEyeTracking.instance().flip_direction)
        self.flip_direction.connect_callback(self.update_flip_direction)
        self.eye_detect.layout().addWidget(self.flip_direction)
        self.uniform_label_width.add_widget(self.flip_direction.label)

        # Image threshold
        self.particle_threshold = IntSliderWidget(self, 'Threshold',
                                                  limits=(1, 255),
                                                  default=ZFEyeTracking.instance().binary_threshold,
                                                  step_size=1)
        self.particle_threshold.connect_callback(self.update_particle_threshold)
        self.eye_detect.layout().addWidget(self.particle_threshold)
        self.uniform_label_width.add_widget(self.particle_threshold.label)

        # Particle size
        self.particle_minsize = IntSliderWidget(self, 'Min. particle size',
                                                limits=(1, 1000),
                                                default=ZFEyeTracking.instance().min_particle_size,
                                                step_size=1)
        self.particle_minsize.connect_callback(self.update_particle_minsize)
        self.eye_detect.layout().addWidget(self.particle_minsize)
        self.uniform_label_width.add_widget(self.particle_minsize.label)

        # Saccade detection
        self.saccade_detect = QtWidgets.QGroupBox('Saccade detection')
        self.saccade_detect.setLayout(QtWidgets.QHBoxLayout())
        self.ctrl_panel.layout().addWidget(self.saccade_detect)
        self.sacc_threshold = IntSliderWidget(self, 'Sacc. threshold [deg/s]',
                                              limits=(1, 10000),
                                              default=ZFEyeTracking.instance().saccade_threshold,
                                              step_size=1)
        self.sacc_threshold.connect_callback(self.update_sacc_threshold)
        self.saccade_detect.layout().addWidget(self.sacc_threshold)
        self.uniform_label_width.add_widget(self.sacc_threshold.label)

        self.hist_plot = HistogramPlot(parent=self)
        self.ctrl_panel.layout().addWidget(self.hist_plot)

        # Add button for new ROI creation
        self.ctrl_panel.layout().addItem(self._vspacer)
        self.add_roi_btn = QtWidgets.QPushButton('Add ROI')
        self.add_roi_btn.clicked.connect(self.add_roi)
        self.ctrl_panel.layout().addWidget(self.add_roi_btn)

        # Set up image plot
        self.frame_plot = FramePlot(parent=self)
        self.frame_plot.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.central_widget.layout().addWidget(self.frame_plot)

        self.connect_to_timer(self.update_frame)

    def add_roi(self):
        self.frame_plot.add_roi()

    @staticmethod
    def update_use_img_corr(value):
        ZFEyeTracking.instance().use_image_correction = bool(value)

    @staticmethod
    def update_contrast(value):
        ZFEyeTracking.instance().contrast = value

    @staticmethod
    def update_brightness(value):
        ZFEyeTracking.instance().brightness = value

    @staticmethod
    def update_use_motion_corr(value):
        ZFEyeTracking.instance().use_motion_correction = value

    @staticmethod
    def update_flip_direction(state):
        ZFEyeTracking.instance().flip_direction = bool(state)

    @staticmethod
    def update_particle_threshold(im_thresh):
        ZFEyeTracking.instance().binary_threshold = im_thresh

    @staticmethod
    def update_particle_minsize(minsize):
        ZFEyeTracking.instance().min_particle_size = minsize

    @staticmethod
    def update_sacc_threshold(sacc_thresh):
        ZFEyeTracking.instance().saccade_threshold = sacc_thresh

    def update_frame(self):

        frame = None

        # If image or motion correction is enabled, display corrected frame
        if ZFEyeTracking.instance().use_image_correction or ZFEyeTracking.instance().use_motion_correction:
            # Try to read corrected frame
            idx, time, frame = vxattribute.read_attribute(ZFEyeTracking.frame_corrected_name)
            frame = frame[0]

        # Fallback to raw frame
        if frame is None:
            idx, time, frame = vxattribute.read_attribute(ZFEyeTracking.frame_name)
            frame = frame[0]

            if frame is None:
                return

        # Update image
        self.frame_plot.image_item.setImage(frame)
        # Update pixel histogram
        self.hist_plot.update_histogram(self.frame_plot.image_item)


class HistogramPlot(QtWidgets.QGroupBox):

    def __init__(self, **kwargs):
        QtWidgets.QGroupBox.__init__(self, 'Histogram', **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.histogram = pg.HistogramLUTWidget(orientation='horizontal')
        self.histogram.item.setHistogramRange(0, 255)
        self.histogram.item.setLevels(0, 255)
        self.layout().addWidget(self.histogram)

        self.histogram.item.sigLevelsChanged.connect(self.update_levels)

    def update_histogram(self, image_item: pg.ImageItem):

        bins, counts = image_item.getHistogram()
        logcounts = counts.astype(np.float64)
        logcounts[counts == 0] = 0.1
        logcounts = np.log10(logcounts)
        logcounts[np.isclose(logcounts, -1)] = 0
        self.histogram.item.plot.setData(bins, logcounts)

    def update_levels(self, item: pg.HistogramLUTItem):
        lower, upper = item.getLevels()

        # Correct out of bounds values
        if lower < 0:
            lower = 0
            item.setLevels(lower, upper)
        if upper > 255:
            upper = 255
            item.setLevels(lower, upper)

        ZFEyeTracking.instance().brightness_min = int(lower)
        ZFEyeTracking.instance().brightness_max = int(upper)


class FramePlot(pg.GraphicsLayoutWidget):
    # Set up basics
    eye_markers: List[EyeMarker] = []
    subplots: List[EyePlot] = []
    line_coordinates = None
    current_id = 0

    def __init__(self, **kwargs):
        pg.GraphicsLayoutWidget.__init__(self, **kwargs)

        # Set up plot image item
        self.image_plot = self.addPlot(0, 0, 1, 10)
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.invertY(True)
        self.image_plot.setAspectLocked(True)
        self.image_item = pg.ImageItem()
        self.image_plot.addItem(self.image_item)

        # Set up scatter item for tracking motion correction features
        self.scatter_item = pg.ScatterPlotItem(pen=pg.mkPen(color='blue'), brush=None)
        self.image_plot.addItem(self.scatter_item)

        # Make subplots update with whole camera frame
        self.image_item.sigImageChanged.connect(self.update_subplots)
        # Bind mouse click event for drawing of lines
        self.image_plot.scene().sigMouseClicked.connect(self.mouse_clicked)

    def resizeEvent(self, ev):
        pg.GraphicsLayoutWidget.resizeEvent(self, ev)

        # Update widget height
        if hasattr(self, 'ci'):
            self.ci.layout.setRowMaximumHeight(1, self.height() // 6)

    def add_roi(self):
        self.line_coordinates = []

    def mouse_clicked(self, ev):
        pos = self.image_plot.vb.mapSceneToView(ev.scenePos())

        # First click: start new line
        if self.line_coordinates is not None and len(self.line_coordinates) == 0:
            self.line_coordinates = [[pos.x(), pos.y()]]

        # Second click: end line and create rectangular ROI + subplot
        elif self.line_coordinates is not None and len(self.line_coordinates) == 1:
            # Set second point of line
            self.line_coordinates.append([pos.x(), pos.y()])

            # Create line
            eye_marker = EyeMarker(len(self.eye_markers), np.array(self.line_coordinates))
            self.eye_markers.append(eye_marker)
            self.image_plot.vb.addItem(eye_marker.line)
            self.image_plot.vb.addItem(eye_marker.rect)

            # Add subplot
            self.subplots.append(EyePlot(len(self.eye_markers), self.addPlot(1, len(self.eye_markers))))

            # Reset for next ROI
            self.line_coordinates = None

    def update_subplots(self):

        ref_points = np.array(ZFEyeTracking.instance().reference_points).squeeze()
        if ref_points.ndim == 2:
            self.scatter_item.setData(pos=ref_points)
        else:
            self.scatter_item.clear()

        # print(ZFEyeTracking.instance().reference_points)

        # Draw rectangular ROIs
        for roi_id in range(len(ZFEyeTracking.instance().rois)):
            rect_data = vxattribute.read_attribute(f'{ZFEyeTracking.instance().extracted_rect_prefix}{roi_id}')

            # If this rect does not exist, skip
            if rect_data is None:
                continue

            idx, time, rect = rect_data
            rect = rect[0]

            if rect is None:
                return

            self.subplots[roi_id].update(rect)


class EyePlot:

    def __init__(self, roi_id: int, plot_item: pg.PlotItem):
        self.roi_id = roi_id
        self.plot_item = plot_item

        # Format
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.plot_item.setAspectLocked(True)
        self.plot_item.invertY(True)
        self.plot_item.vb.setMouseEnabled(x=False, y=False)
        # Add image item
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

    def update(self, image: np.ndarray):

        # Transpose
        if image.ndim == 2:
            image = image.T
        elif image.ndim == 3:
            image = image.transpose(1, 0, 2)
        else:
            log.error('AN IMAGE PLEASE!!!')
            return

        # Update
        self.image_item.setImage(image)


class EyeMarker:

    def __init__(self, roi_id, line_coordinates):
        self.roi_id = roi_id

        roi_pen = pg.mkPen(color='red', width=4)
        handle_pen = pg.mkPen(color='blue')
        hover_pen = pg.mkPen(color='green')

        # Create line
        self.line = pg.LineSegmentROI(positions=line_coordinates, movable=False, removable=True,
                                      pen=roi_pen, handlePen=handle_pen, handleHoverPen=hover_pen)

        # Create rect
        self.rect = pg.RectROI(pos=[0, 0], size=[1, 1], movable=False, centered=True,
                               pen=roi_pen, handlePen=handle_pen, handleHoverPen=hover_pen)
        self.rect.setSize(np.linalg.norm(line_coordinates[0] - line_coordinates[1]) * np.array([0.8, 1.3]))

        self.line.sigRegionChangeFinished.connect(self.update)
        self.rect.sigRegionChangeFinished.connect(self.update_size)

        ZFEyeTracking.instance().rois.append([])
        self.update(self.line)

    def update(self, line_segment: pg.LineSegmentROI):

        # Check if this one was removed by routine
        if self.roi_id >= len(ZFEyeTracking.instance().rois):
            self.line.getViewBox().removeItem(self.line)
            self.rect.getViewBox().removeItem(self.rect)
            del self
            return

        p1, p2 = [np.array(p.pos()) for p in line_segment.endpoints]
        line = p2 - p1
        line_dir = line / np.linalg.norm(line)

        line_angle = np.arccos(np.dot(np.array([-1.0, 0.0]), line_dir))
        if line[1] > 0:
            line_angle = 2 * np.pi - line_angle

        # Move rect
        self.rect.setPos(p1, finish=False)
        self.rect.setAngle(line_angle * 180 / np.pi, finish=False)
        self.rect.translate(-0.5 * self.rect.size().x() * np.array([np.cos(line_angle), np.sin(line_angle)])
                            + 0.5 * self.rect.size().y() * np.array([np.sin(line_angle), -np.cos(line_angle)]),
                            finish=False)

        # Update ROI information / format: center, size, angle
        _center = (int(p1[0]), int(p1[1]))
        _size = (int(self.rect.size()[0]), int(self.rect.size()[1]))
        _angle = line_angle * 180 / np.pi
        ZFEyeTracking.instance().rois[self.roi_id] = _center, _size, _angle

    def update_size(self, *args, **kwargs):
        # Just call the line segment update, it sets everything including rect size
        self.update(self.line)


class ZFEyeTracking(vxroutine.CameraRoutine):
    """Routine that detects an arbitrary number of zebrafish eye pairs in a
    monochrome input frame

    Args:
        roi_maxnum (int): maximum number of eye pairs to be detected
        thresh (int): initial binary threshold to use for segmentation
        min_size (int): initial minimal particle size. Anything below this size will be discarded
        saccade_threshold (int): initial saccade velocity threshold for binary saccade trigger
    """

    # Set required device
    camera_device_id = 'fish_embedded'

    # Names
    routine_prefix = 'eyepos_'
    extracted_rect_prefix = f'{routine_prefix}extracted_rect_'
    ang_le_pos_prefix = f'{routine_prefix}ang_le_pos_'
    ang_re_pos_prefix = f'{routine_prefix}ang_re_pos_'
    le_axes_prefix = f'{routine_prefix}le_axes_'
    re_axes_prefix = f'{routine_prefix}re_axes_'
    ang_le_vel_prefix = f'{routine_prefix}ang_le_vel_'
    ang_re_vel_prefix = f'{routine_prefix}ang_re_vel_'
    le_sacc_prefix = f'{routine_prefix}le_saccade_'
    re_sacc_prefix = f'{routine_prefix}re_saccade_'
    le_sacc_direction_prefix = f'{routine_prefix}le_saccade_direction_'
    re_sacc_direction_prefix = f'{routine_prefix}re_saccade_direction_'
    frame_name = f'{routine_prefix}frame'
    frame_corrected_name = f'{routine_prefix}corrected_frame'
    sacc_trigger_name = f'{routine_prefix}saccade_trigger'

    # Parameters
    # Image corrections
    use_image_correction = False
    contrast = 1.0
    brightness = 0
    brightness_min = 0
    brightness_max = 255
    use_motion_correction = False
    # Eye detection
    roi_maxnum = 5
    flip_direction = False
    binary_threshold = 60
    min_particle_size = 20
    # Saccade detection
    saccade_threshold = 600

    # Internal
    reference_frame: Union[None, np.ndarray] = None
    reference_points = []
    rois: List[tuple] = []
    current_roi_count = 0

    def __init__(self, *args, **kwargs):
        vxroutine.CameraRoutine.__init__(self, *args, **kwargs)

    def require(self):
        # Add camera device to deps
        vxdependency.require_camera_device(self.camera_device_id)

    def setup(self):

        # Get camera specs
        camera = vxcamera.get_camera_by_id(self.camera_device_id)
        if camera is None:
            log.error(f'Camera {self.camera_device_id} unavailable for eye position tracking')
            return

        # Add frames
        vxattribute.ArrayAttribute(self.frame_name, (camera.width, camera.height), vxattribute.ArrayType.uint8)
        vxattribute.ArrayAttribute(self.frame_corrected_name, (camera.width, camera.height),
                                   vxattribute.ArrayType.uint8)

        # Add saccade trigger buffer
        vxattribute.ArrayAttribute(self.sacc_trigger_name, (1,), vxattribute.ArrayType.bool)

        # Add attributes per fish
        for i in range(self.roi_maxnum):
            # Rectangle
            vxattribute.ObjectAttribute(f'{self.extracted_rect_prefix}{i}')

            # Position
            vxattribute.ArrayAttribute(f'{self.ang_le_pos_prefix}{i}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.ang_re_pos_prefix}{i}', (1,), vxattribute.ArrayType.float64)

            # Major/minor axes length attribute
            vxattribute.ArrayAttribute(f'{self.le_axes_prefix}{i}', (2,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.re_axes_prefix}{i}', (2,), vxattribute.ArrayType.float64)

            # Velocity
            vxattribute.ArrayAttribute(f'{self.ang_le_vel_prefix}{i}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.ang_re_vel_prefix}{i}', (1,), vxattribute.ArrayType.float64)

            # Saccade detection
            vxattribute.ArrayAttribute(f'{self.le_sacc_prefix}{i}', (1,), vxattribute.ArrayType.float64)
            vxattribute.ArrayAttribute(f'{self.re_sacc_prefix}{i}', (1,), vxattribute.ArrayType.float64)

            # Saccade direction
            vxattribute.ArrayAttribute(f'{self.le_sacc_direction_prefix}{i}', (1,), vxattribute.ArrayType.int8)
            vxattribute.ArrayAttribute(f'{self.re_sacc_direction_prefix}{i}', (1,), vxattribute.ArrayType.int8)

    def initialize(self):
        pass

    def _create_roi(self, roi_num: int):
        """Register buffer attributes with plotter
        """

        if len(self.rois) > self.roi_maxnum:
            log.error(f'Maximum number of ROIs for eye tracking ({self.roi_maxnum}) exceeded')
            self.rois.pop(-1)
            return

        # For first ROI: also add the generic saccade trigger output
        if len(self.rois) == 1:
            # Set saccade trigger (LE and RE) signal to "saccade_trigger" channel by default
            vxio.set_digital_output('saccade_trigger_output', self.sacc_trigger_name)
            vxui.register_with_plotter(self.sacc_trigger_name)

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

        # Saccade Direction
        vxui.register_with_plotter(f'{self.le_sacc_direction_prefix}{roi_num}', name=f'sacc_dir(LE {roi_num})',
                                   axis='sacc')
        vxui.register_with_plotter(f'{self.re_sacc_direction_prefix}{roi_num}', name=f'sacc_dir(RE {roi_num})',
                                   axis='sacc')

        # Add attributes to save-to-file list:
        vxattribute.write_to_file(self, f'{self.ang_le_pos_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_re_pos_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.le_axes_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.re_axes_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_le_vel_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.ang_re_vel_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.le_sacc_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.re_sacc_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.le_sacc_direction_prefix}{roi_num}')
        vxattribute.write_to_file(self, f'{self.re_sacc_direction_prefix}{roi_num}')

    @staticmethod
    def _extract_roi_rect(frame, rect_params):

        # Get rect and frame parameters
        center, size, angle = rect_params
        height, width = frame.shape[0], frame.shape[1]

        # Rotate
        M = cv2.getRotationMatrix2D(center, angle, 1)
        rot_frame = cv2.warpAffine(frame, M, (width, height))

        # Crop rect from frame
        rect = cv2.getRectSubPix(rot_frame, size, center)

        # Rotate rect so that "up" direction in image corresponds to "foward" for the fish
        center = (size[0] / 2, size[1] / 2)
        width, height = size
        M = cv2.getRotationMatrix2D(center, 90, 1)

        # New bound width/height
        bound_width = int(height * abs(M[0, 1]) + width * abs(M[0, 0]))
        bound_height = int(height * abs(M[0, 0]) + width * abs(M[0, 1]))

        # Subtract old image center
        M[0, 2] += bound_width / 2 - center[0]
        M[1, 2] += bound_height / 2 - center[1]
        # Rotate
        rot_rect = cv2.warpAffine(rect, M, (bound_width, bound_height))

        return rot_rect

    def _get_eye_positions(self, rect):
        # Formatting for drawing
        line_thickness = np.ceil(np.mean(rect.shape) / 100).astype(int)
        line_thickness = 1 if line_thickness == 0 else line_thickness
        marker_size = line_thickness * 5

        # Set rect center
        rect_center = (rect.shape[1] // 2, rect.shape[0] // 2)

        # Apply threshold
        _, thresh = cv2.threshold(rect[:, :], self.binary_threshold, 255, cv2.THRESH_BINARY_INV)

        # Detect contours
        cnts, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cnts = list(cnts)

        # Make RGB
        rgb = np.repeat(thresh[:, :, None], 3, -1)  # np.stack((thresh, thresh, thresh), axis=-1)

        # Collect contour parameters and filter contours
        areas = []
        barycenters = []
        hulls = []
        feret_points = []
        thetas = []
        axes = []
        dists = []
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
            center = (M['m10'] / A, M['m01'] / A)

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
            theta = (1 / 2 * np.arctan(b / (a - c)) + (a < c) - 1) / np.pi * 180  # * np.pi / 2
            L = np.sqrt(8 * (a + c + np.sqrt(b ** 2 + (a - c) ** 2)))
            W = np.sqrt(8 * (a + c - np.sqrt(b ** 2 + (a - c) ** 2)))

            thetas.append(theta)
            barycenters.append(center)
            axes.append((W, L))
            areas.append(A)
            hulls.append(hull)
            dists.append(distance.euclidean(center, rect_center))
            feret_points.append((hull[np.argmin(hull[:, 1])], hull[np.argmax(hull[:, 1])]))

            i += 1

        # Additional filtering of particles to idenfity both eyes if more than 2
        if len(cnts) > 2:
            dists, areas, barycenters, hulls, feret_points, thetas, axes = \
                list(zip(*sorted(list(zip(dists, areas, barycenters, hulls, feret_points, thetas, axes)))[:2]))

        forward_vec = np.array([0, -1])
        forward_vec_norm = forward_vec / np.linalg.norm(forward_vec)
        # Draw rect center and midline marker for debugging
        # (Important: this has to happen AFTER detection of contours,
        # as it alters the tresh'ed image)
        cv2.drawMarker(rgb, rect_center, (0, 255, 0), cv2.MARKER_DIAMOND, marker_size * 2, line_thickness)
        cv2.arrowedLine(rgb,
                        tuple(rect_center), tuple((rect_center + rect.shape[0] / 3 * forward_vec_norm).astype(int)),
                        (0, 255, 0), line_thickness, tipLength=0.3)

        # Draw hull contours for debugging (before possible premature return)
        cv2.drawContours(rgb, hulls, -1, (128, 128, 0), line_thickness)

        # If less than two particles, return
        if len(cnts) < 2:
            return np.nan, np.nan, np.nan, np.nan, rgb

        # At this point there should only be 2 particles left
        le_idx = 0 if (barycenters[0][0] < rect_center[0]) else 1
        re_idx = 1 if (barycenters[0][0] < rect_center[0]) else 0

        # Draw ellipses
        try:
            for center, axis, theta in zip(barycenters, axes, thetas):
                center = tuple((int(i) for i in center))
                axis = tuple((int(i//2) for i in axis))
                angle = float(theta)
                start_angle = 0.
                end_angle = 360.
                color = (255, 0, 0)

                cv2.ellipse(rgb,
                            center,
                            axis,
                            angle, start_angle, end_angle, color, line_thickness)
        except Exception as exc:
            import traceback
            traceback.print_exc()

        # Draw eye label
        le_center = np.array(barycenters[le_idx]) - np.array([1, -1]) * np.linalg.norm(axes[le_idx]) / 4
        cv2.putText(rgb, 'L', (int(le_center[0]), int(le_center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0),
                    line_thickness, cv2.LINE_AA)
        re_center = np.array(barycenters[re_idx]) - np.array([1, -1]) * np.linalg.norm(axes[le_idx]) / 4
        cv2.putText(rgb, 'R', (int(re_center[0]), int(re_center[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0),
                    line_thickness, cv2.LINE_AA)

        return thetas[le_idx], thetas[re_idx], axes[le_idx][::-1], axes[re_idx][::-1], rgb

    def update_motion_reference(self, frame: np.ndarray):

        # Update reference frame
        self.reference_frame = frame.copy()

        # Find reference points
        ref_points = cv2.goodFeaturesToTrack(self.reference_frame,
                                             maxCorners=200,
                                             qualityLevel=0.01,
                                             minDistance=30,
                                             blockSize=3)

        # Filter to make sure they are not within a ROI (i.e. on the tracked eyes)
        good_ref_points = np.zeros(ref_points.shape[0])
        for i, pt in enumerate(ref_points):
            for center, size, angle in self.rois:
                if ((pt[0][0] - center[0])**2 + (pt[0][1] - center[1])**2) < max(size)**2:
                    good_ref_points[i] = 1
                    break

        # Update reference points
        valid_ref_points = ref_points[good_ref_points.astype(bool)]
        self.reference_points[:] = valid_ref_points

    def apply_motion_correction(self, frame: np.ndarray) -> Union[np.ndarray, None]:
        if self.reference_frame is None:
            self.update_motion_reference(frame)
            return

        # ListProxy needs to be re-converted into array for OpenCV
        ref_points = np.array(self.reference_points)

        # Calculate optic flow
        new_points, status, _ = cv2.calcOpticalFlowPyrLK(self.reference_frame, frame, ref_points, None)

        if ref_points.shape != new_points.shape:
            log.warning('Motion correction failed. Reference point number != frame point number')
            return

        # Filter valid points
        idx = np.where(status == 1)[0]
        ref_points = ref_points[idx]
        new_points = new_points[idx]

        # Get transform matrix
        M, _ = cv2.estimateAffinePartial2D(new_points, ref_points)

        # Apply & return
        return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))

    def apply_image_correction(self, frame: np.ndarray) -> np.ndarray:
        return np.clip(self.contrast * frame + self.brightness, 0, 255).astype(np.uint8)

    def apply_range(self, frame: np.ndarray) -> np.ndarray:
        return np.clip(frame, self.brightness_min, self.brightness_max).astype(np.uint8)

    def main(self, **frames):

        # New ROI?
        if len(self.rois) > self.current_roi_count:
            self._create_roi(len(self.rois) - 1)
            self.current_roi_count += 1

        # Read frame
        frame = frames.get(self.camera_device_id)

        # for point in self.reference_points:
        #     frame = cv2.circle(frame, (int(point[0][0]), int(point[0][1])), radius=3, color=255, thickness=-1)

        # Check if frame was returned
        if frame is None:
            return

        # Reduce to mono
        if frame.ndim > 2:
            frame = frame[:, :, 0]

        corrected_frame = None

        # Apply motion correction
        if self.use_motion_correction:
            corrected_frame = self.apply_motion_correction(frame)
        # Reset reference frame for motion correction (if set) in case motion correction is disabled
        else:
            if self.reference_frame is not None:
                self.reference_frame = None
                self.reference_points[:] = []

        # Apply image correction
        if self.use_image_correction:
            corrected_frame = self.apply_image_correction(frame if corrected_frame is None else corrected_frame)

        # Apply range after image/motion correction
        frame = self.apply_range(frame)

        # Write original frame to buffer
        vxattribute.write_attribute(self.frame_name, frame.T)

        # After original frame has been written to attribute:
        # If any image processing was enabled, write result to corrected frame's attribute and use as default frame
        if corrected_frame is not None:
            frame = self.apply_range(corrected_frame)
            vxattribute.write_attribute(self.frame_corrected_name, frame.T)
        # # If not corrected frame exists, fix range of original one and use that one
        # else:
        #     # Fix intensity range
        #     frame = self.apply_range(frame)

        # If there are no ROIs, there's nothing to detect
        if len(self.rois) == 0:
            return

        # If eyes were marked: iterate over ROIs and extract eye positions
        saccade_happened = False
        for roi_num, rect_params in enumerate(self.rois):

            if len(rect_params) == 0:
                continue

            # Extract rectangular ROI
            rot_rect = self._extract_roi_rect(frame, rect_params)

            # Apply detection function on cropped rect which contains eyes
            le_pos, re_pos, le_axes, re_axes, new_rect = self._get_eye_positions(rot_rect)

            if self.flip_direction:
                le_pos = -le_pos
                re_pos = -re_pos

            # Get shared attributes
            le_pos_attr = vxattribute.get_attribute(f'{self.ang_le_pos_prefix}{roi_num}')
            re_pos_attr = vxattribute.get_attribute(f'{self.ang_re_pos_prefix}{roi_num}')
            le_axes_attr = vxattribute.get_attribute(f'{self.le_axes_prefix}{roi_num}')
            re_axes_attr = vxattribute.get_attribute(f'{self.re_axes_prefix}{roi_num}')
            le_vel_attr = vxattribute.get_attribute(f'{self.ang_le_vel_prefix}{roi_num}')
            re_vel_attr = vxattribute.get_attribute(f'{self.ang_re_vel_prefix}{roi_num}')
            le_sacc_attr = vxattribute.get_attribute(f'{self.le_sacc_prefix}{roi_num}')
            re_sacc_attr = vxattribute.get_attribute(f'{self.re_sacc_prefix}{roi_num}')
            le_sacc_dir_attr = vxattribute.get_attribute(f'{self.le_sacc_direction_prefix}{roi_num}')
            re_sacc_dir_attr = vxattribute.get_attribute(f'{self.re_sacc_direction_prefix}{roi_num}')
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
            le_vel = (le_pos - last_le_pos) / dt
            re_vel = (re_pos - last_re_pos) / dt

            # Calculate saccade trigger
            _, _, last_le_vel = le_vel_attr.read()
            last_le_vel = last_le_vel[0]
            _, _, last_re_vel = re_vel_attr.read()
            last_re_vel = last_re_vel[0]

            le_sacc = int(np.abs(last_le_vel) < self.saccade_threshold < np.abs(le_vel))
            re_sacc = int(np.abs(last_re_vel) < self.saccade_threshold < np.abs(re_vel))

            is_saccade = bool(le_sacc) or bool(re_sacc)
            saccade_happened = saccade_happened or is_saccade

            if le_vel > self.saccade_threshold:
                le_sacc_dir = 1
            elif le_vel < -self.saccade_threshold:
                le_sacc_dir = -1
            else:
                le_sacc_dir = 0

            if re_vel > self.saccade_threshold:
                re_sacc_dir = 1
            elif re_vel < -self.saccade_threshold:
                re_sacc_dir = -1
            else:
                re_sacc_dir = 0

            # Write to buffer
            le_pos_attr.write(le_pos)
            re_pos_attr.write(re_pos)
            le_axes_attr.write(le_axes)
            re_axes_attr.write(re_axes)
            le_vel_attr.write(np.abs(le_vel))
            re_vel_attr.write(np.abs(re_vel))
            le_sacc_dir_attr.write(le_sacc_dir)
            re_sacc_dir_attr.write(re_sacc_dir)

            le_sacc_attr.write(le_sacc)
            re_sacc_attr.write(re_sacc)

            # Set current rect ROI data
            rect_roi_attr.write(new_rect)

        # Write saccade_happened trigger attribute (this is evaluated for all eyes of all ROIs)
        vxattribute.write_attribute(self.sacc_trigger_name, saccade_happened)
