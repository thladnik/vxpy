from __future__ import annotations
from typing import List, Dict

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph as pg
import scipy.stats
from PySide6 import QtWidgets

import vxpy.core.attribute as vxattribute
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.utils import widgets

log = vxlogger.getLogger(__name__)


def get_roi_color(index: int):
    return (255 * np.array(mpl.colormaps['tab10'](index)[:3])).astype(np.uint8)


class RoiActivityTrackerRoutine(vxroutine.WorkerRoutine):
    input_frame_name: str = 'tcp_server_frame'
    input_num_interlaced_layers: int = 2
    output_frame_name: str = 'roi_activity_tracker_frame'
    roi_max_num: int = 5
    roi_name_prefix: str = 'roi_activity'
    roi_thresholds: Dict[tuple, int] = {}
    lower_px_threshold: int = 10
    roi_activity_trigger_name: str = 'roi_activity_trigger'
    frame_width: int = 256
    frame_height: int = 256
    frame_dtype: str = 'float64'

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.roi_slice_params: Dict[tuple, tuple] = {}
        self._f0 = [0] * 20

    def require(self) -> bool:

        # Get frame type and shape
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        shape = (self.frame_width, self.frame_height)

        # Set up all layer/ROI attributes
        for layer_idx in range(self.input_num_interlaced_layers):

            # Create frame attribute
            vxattribute.ArrayAttribute(f'{self.output_frame_name}_{layer_idx}', shape, dtype)

            for roi_idx in range(self.roi_max_num):
                self.roi_slice_params[(layer_idx, roi_idx)] = ()
                self.roi_thresholds[(layer_idx, roi_idx)] = 2000

                # Create ROI attribute
                vxattribute.ArrayAttribute(self.roi_name(layer_idx, roi_idx), (1,), vxattribute.ArrayType.float64)
                vxattribute.ArrayAttribute(f'{self.roi_name(layer_idx, roi_idx)}_zscore', (1,),
                                           vxattribute.ArrayType.float64)

                # Register with plotter
                vxui.register_with_plotter(self.roi_name(layer_idx, roi_idx),
                                           name=f'ROI {roi_idx}', axis=f'Layer {layer_idx}',
                                           color=get_roi_color(roi_idx))
                vxui.register_with_plotter(f'{self.roi_name(layer_idx, roi_idx)}_zscore',
                                           name=f'ROI {roi_idx}', axis=f'Layer {layer_idx} zscore',
                                           color=get_roi_color(roi_idx))
                vxattribute.write_to_file(self, self.roi_name(layer_idx, roi_idx))

            # Create trigger attribute
            vxattribute.ArrayAttribute(self.trigger_name(layer_idx), (1,), vxattribute.ArrayType.uint8)
            vxui.register_with_plotter(self.trigger_name(layer_idx), name=f'ROI activity {layer_idx}', axis='Trigger')

        return True

    def initialize(self):
        # Creatre trigger to which routine should react to
        self.trigger = vxevent.NewDataTrigger(self.input_frame_name, callback=self._process_frame)
        self.trigger.set_active()

    def main(self, *args, **kwargs):
        # Routine only works on trigger callback
        pass

    def _process_frame(self, last_idx, last_time, last_frame):
        """Method gets last written input frame data as arguments"""

        _, _, last_counter = vxattribute.get_attribute(f'{self.input_frame_name}_index')[int(last_idx)]

        last_frame = last_frame.astype(np.float64)

        # frame preprocessing
        # preprocessed_frame = np.where(last_frame < np.histogram(last_frame, bins=2)[1][1], last_frame, 0)
        # preprocessed_frame = np.where(preprocessed_frame > self.lower_px_threshold, preprocessed_frame, 0)
        preprocessed_frame = last_frame

        # Write to corresponding attribute for interleaved layer
        current_layer_idx = int(last_counter) % self.input_num_interlaced_layers
        vxattribute.write_attribute(f'{self.output_frame_name}_{current_layer_idx}', preprocessed_frame)

        over_thresh = False
        for (layer_idx, roi_idx), slice_params in self.roi_slice_params.items():
            if layer_idx != current_layer_idx or len(slice_params) == 0:
                continue

            # Get ROI data
            _slice = pg.affineSlice(preprocessed_frame, slice_params[0], slice_params[2], slice_params[1], (0, 1))

            # Calculate activity
            activity = (np.std(_slice) * np.mean(_slice)) / 1000
            # Write activity attribute
            vxattribute.write_attribute(self.roi_name(layer_idx, roi_idx), activity)

            # Calculate zscore
            _, _, past_activities = vxattribute.read_attribute(self.roi_name(layer_idx, roi_idx), last=40)
            past_activities = past_activities.flatten()
            current_zscore = scipy.stats.zmap(past_activities[-1], past_activities[:-1])
            vxattribute.write_attribute(f'{self.roi_name(layer_idx, roi_idx)}_zscore', current_zscore)

            # Threshold exceeded for this ROI?
            # over_thresh = current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
            # over_thresh = over_thresh or current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
            over_thresh = over_thresh or activity > self.roi_thresholds[(layer_idx, roi_idx)]

        # Write trigger
        vxattribute.write_attribute(self.trigger_name(current_layer_idx), int(over_thresh))

    def roi_name(self, layer_idx: int, roi_idx: int) -> str:
        return f'{self.roi_name_prefix}_{layer_idx}_{roi_idx}'

    def trigger_name(self, layer_idx: int) -> str:
        return f'{self.roi_activity_trigger_name}_{layer_idx}'

    @vxroutine.WorkerRoutine.callback
    def update_roi(self, layer_idx: int, roi_idx, new_slice_params: tuple):
        log.debug(f'Received slice params for layer {layer_idx}: {new_slice_params}')
        # print(new_slice_params)
        # self.roi_slice_params[layer_idx][roi_idx] = new_slice_params
        # print(self.roi_slice_params)


class RoiActivityTrackerWidget(vxui.WorkerAddonWidget):
    display_name = 'ROI activity tracker'

    def __init__(self, *args, **kwargs):
        vxui.WorkerAddonWidget.__init__(self, *args, **kwargs)

        # Get datatype
        _dtype = np.dtype(getattr(np, RoiActivityTrackerRoutine.instance().frame_dtype))
        assert np.issubdtype(_dtype, np.integer), 'dtype is not an integer'
        upper_lim = 2 ** (8 * _dtype.itemsize)

        self.central_widget.setLayout(QtWidgets.QVBoxLayout())

        self.pixel_threshold = widgets.IntSliderWidget(self.central_widget,
                                                       label='Lower pixel threshold',
                                                       default=RoiActivityTrackerRoutine.instance().lower_px_threshold,
                                                       limits=(1, upper_lim), step_size=10)
        self.pixel_threshold.connect_callback(self.update_pixel_threshold)
        self.central_widget.layout().addWidget(self.pixel_threshold)

        self.img_plot_widget = QtWidgets.QWidget()
        self.img_plot_widget.setLayout(QtWidgets.QGridLayout())
        self.central_widget.layout().addWidget(self.img_plot_widget)

        self.frame_name = RoiActivityTrackerRoutine.instance().output_frame_name
        self.layer_num = RoiActivityTrackerRoutine.instance().input_num_interlaced_layers

        # Create image widgets for each layer
        self.image_widgets: List[ImageWidget] = []
        for layer_idx in range(self.layer_num):
            image_widget = ImageWidget(layer_idx, parent=self)
            self.img_plot_widget.layout().addWidget(image_widget, layer_idx // self.layer_num, layer_idx % self.layer_num)
            self.image_widgets.append(image_widget)

        # Connect timer
        self.connect_to_timer(self.update_frame)

    @staticmethod
    def update_pixel_threshold(value: int):
        """Set minimum pixel brightness threshold on routine"""
        RoiActivityTrackerRoutine.instance().lower_px_threshold = value

    def update_frame(self):
        """Update frame on for each interleaved sublayer"""

        for layer_idx in range(self.layer_num):
            idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}')

            if len(idx) == 0:
                return

            self.image_widgets[layer_idx].update_frame(frame[0])


class ImageWidget(QtWidgets.QGroupBox):

    def __init__(self, layer_idx: int, **kwargs):
        QtWidgets.QGroupBox.__init__(self, **kwargs)
        self.layer_idx = layer_idx

        self.setLayout(QtWidgets.QVBoxLayout())
        # Add pyqtgraph graphics widget
        self.graphics_widget = pg.GraphicsLayoutWidget(parent=self)
        self.layout().addWidget(self.graphics_widget)
        # Add controls
        self.controls = QtWidgets.QWidget(parent=self)
        self.layout().addWidget(self.controls)
        self.controls.setLayout(QtWidgets.QGridLayout())

        # Add plot
        self.image_plot = self.graphics_widget.addPlot(0, 0, 1, 10)
        # Set up plot image item
        self.image_item = pg.ImageItem()
        self.image_plot.invertY(True)
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)
        self.image_plot.addItem(self.image_item)
        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.image_plot.addItem(self.text)
        self.text.setPos(0, 0)

        # Add ROI
        self.rois: List[Roi] = []
        self.threshold_widgets: List[widgets.DoubleSliderWidget] = []

        # spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Maximum,
        #                                QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        # self.controls.layout().addItem(spacer, RoiActivityTrackerRoutine.instance().roi_max_num, 0)

        self.add_roi_btn = QtWidgets.QPushButton('Add ROI')
        self.add_roi_btn.clicked.connect(self.add_roi)
        self.controls.layout().addWidget(self.add_roi_btn, RoiActivityTrackerRoutine.instance().roi_max_num + 1, 0)

    def add_roi(self):
        # Get next index
        roi_idx = len(self.rois)
        if roi_idx >= RoiActivityTrackerRoutine.instance().roi_max_num:
            log.warning('Failed to add ROI. Maximum number of ROIs exceeded')
            return

        # Add ROI
        width = RoiActivityTrackerRoutine.instance().frame_width
        roi = Roi(self.layer_idx, roi_idx, self, (0, 0), (1, 1))
        self.image_plot.getViewBox().addItem(roi)
        roi.setPos([width//2, width//2])
        roi.setSize([width//4, width//4])
        self.rois.append(roi)

        # Add ROI threshold widget
        thresh = widgets.DoubleSliderWidget(self.controls,
                                            label=f'ROI {roi_idx}',
                                            default=RoiActivityTrackerRoutine.instance().roi_thresholds[(self.layer_idx, roi_idx)],
                                            limits=(0, 50), step_size=0.1)
        thresh.connect_callback(roi.update_threshold)
        self.controls.layout().addWidget(thresh, roi_idx, 0)

    def update_frame(self, frame: np.ndarray):
        self.image_item.setImage(frame)

    def roi_updated(self, roi: Roi):
        log.debug(f'Update ROI for layer {self.layer_idx}')
        slice_params = roi.getAffineSliceParams(self.image_item.image, self.image_item)
        RoiActivityTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi.idx)] = slice_params


class Roi(pg.RectROI):

    def __init__(self, layer_idx: int, idx: int, image_widget: ImageWidget, *args, **kwargs):
        pg.RectROI.__init__(self, *args, sideScalers=True, **kwargs)
        self.layer_idx = layer_idx
        self.idx = idx
        self.image_widget = image_widget

        self.sigRegionChangeFinished.connect(self.image_widget.roi_updated)
        self.setPen(pg.mkPen(color=get_roi_color(self.idx)))
        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.label.setAnchor((0, 1))
        self.image_widget.image_plot.addItem(self.label)

        self.sigRegionChanged.connect(self.position_changed)

    def set_visible(self):
        self.label.setVisible(True)
        self.setVisible(True)

    def set_invisible(self):
        self.label.setVisible(False)
        self.setVisible(False)

    def position_changed(self, roi: Roi):
        self.label.setPos(roi.pos())

    def update_threshold(self, value: int):
        RoiActivityTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value
