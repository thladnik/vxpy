from __future__ import annotations
from typing import List

import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets

import vxpy.core.attribute as vxattribute
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.utils import widgets

log = vxlogger.getLogger(__name__)


class RoiActivityTrackerRoutine(vxroutine.WorkerRoutine):

    input_frame_name: str = 'activity_tracker_frame'
    input_num_interlaced_layers: int = 1
    output_frame_name: str = 'roi_activity_tracker_frame'
    roi_max_num: int = 5
    roi_activity_prefix: str = 'roi_activity'
    roi_activity_threshold: int = 500
    roi_activity_trigger_name: str = 'roi_activity_trigger'
    frame_width: int = 512
    frame_height: int = 512
    frame_dtype: str = 'uint8'

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.roi_slice_params: List[List[tuple]] = []

    def require(self) -> bool:

        # Get frame type and shape
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        shape = (self.frame_width, self.frame_height)

        # Set up all layer/ROI attributes
        for layer_idx in range(self.input_num_interlaced_layers):

            # Create frame attribute
            vxattribute.ArrayAttribute(f'{self.output_frame_name}_{layer_idx}', shape, dtype)
            self.roi_slice_params.append([() for _ in range(self.roi_max_num)])

            for roi_idx in range(self.roi_max_num):

                # Create ROI attribute
                vxattribute.ArrayAttribute(self.roi_name(layer_idx, roi_idx), (1,), vxattribute.ArrayType.float64)

                # Register with plotter
                vxui.register_with_plotter(self.roi_name(layer_idx, roi_idx),
                                           name=f'ROI {layer_idx}/{roi_idx}', axis='ROI activity')

            # Create trigger attribute
            vxattribute.ArrayAttribute(self.trigger_name(layer_idx), (1,), vxattribute.ArrayType.uint8)
            vxui.register_with_plotter(self.trigger_name(layer_idx), name=f'ROI activity', axis='Trigger')

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

        _, _, last_counter = vxattribute.get_attribute(f'{self.input_frame_name}_counter')[int(last_idx)]

        # Write to corresponding attribute for interleaved layer
        layer_idx = int(last_counter) % self.input_num_interlaced_layers
        vxattribute.write_attribute(f'{self.output_frame_name}_{layer_idx}', last_frame)

        over_thresh = False
        for roi_idx, roi_slice_params in enumerate(self.roi_slice_params[layer_idx]):
            if len(roi_slice_params) == 0:
                continue

            # Get sliced array and activity
            _slice = pg.affineSlice(last_frame, roi_slice_params[0], roi_slice_params[2], roi_slice_params[1], (0, 1))
            activity = np.mean(_slice)

            # Write activity attribute
            vxattribute.write_attribute(self.roi_name(layer_idx, roi_idx), activity)

            if activity > self.roi_activity_threshold:
                over_thresh = True

        # Write trigger
        vxattribute.write_attribute(self.trigger_name(layer_idx), int(over_thresh))

    def roi_name(self, layer_idx: int, roi_idx: int) -> str:
        return f'{self.roi_activity_prefix}_{layer_idx}_{roi_idx}'

    def trigger_name(self, layer_idx: int) -> str:
        return f'{self.roi_activity_trigger_name}_{layer_idx}'

    @vxroutine.WorkerRoutine.callback
    def update_roi(self, layer_idx: int, roi_idx, new_slice_params: tuple):

        log.debug(f'Received slice params for layer {layer_idx}: {new_slice_params}')
        self.roi_slice_params[layer_idx][roi_idx] = new_slice_params

    @vxroutine.WorkerRoutine.callback
    def update_activity_threshold(self, value: int):
        self.roi_activity_threshold = value


class RoiActivityTrackerWidget(vxui.WorkerAddonWidget):

    display_name = 'ROI activity tracker'

    def __init__(self, *args, **kwargs):
        vxui.WorkerAddonWidget.__init__(self, *args, **kwargs)

        _dtype = RoiActivityTrackerRoutine.instance().frame_dtype
        upper_lim = 10**4
        if _dtype.endswith('8'):
            upper_lim = 2**8
        elif _dtype.endswith('16'):
            upper_lim = 2**16

        self.central_widget.setLayout(QtWidgets.QVBoxLayout())

        self.activity_threshold = widgets.IntSliderWidget(self.central_widget,
                                                             label='ROI activity threshold',
                                                             default=500, limits=(1, upper_lim), step_size=10)
        self.activity_threshold.connect_callback(self.update_threshold)
        self.central_widget.layout().addWidget(self.activity_threshold)

        self.img_plot_widget = QtWidgets.QWidget()
        self.img_plot_widget.setLayout(QtWidgets.QGridLayout())
        self.central_widget.layout().addWidget(self.img_plot_widget)

        self.frame_name = RoiActivityTrackerRoutine.instance().output_frame_name
        self.interlaced_layers = RoiActivityTrackerRoutine.instance().input_num_interlaced_layers

        # Create image widgets for each layer
        self.image_widgets: List[ImageWidget] = []
        for layer_idx in range(self.interlaced_layers):
            image_widget = ImageWidget(layer_idx, parent=self)
            self.img_plot_widget.layout().addWidget(image_widget, layer_idx // 2, layer_idx % 2)
            self.image_widgets.append(image_widget)

        # Connect timer
        self.connect_to_timer(self.update_frame)

    def update_threshold(self, value: int):
        vxipc.worker_rpc(RoiActivityTrackerRoutine.update_activity_threshold, value)

    def update_frame(self):

        for layer_idx in range(self.interlaced_layers):
            idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}')

            if len(idx) == 0:
                return

            self.image_widgets[layer_idx].update_frame(frame[0])


class ImageWidget(pg.ImageView):

    def __init__(self, layer_idx: int, **kwargs):
        pg.ImageView.__init__(self, **kwargs)
        # Hide builtin ROI option
        self.ui.roiBtn.hide()

        self.layer_idx = layer_idx

        # Add ROI
        self.rois: List[Roi] = []
        for idx in range(RoiActivityTrackerRoutine.instance().roi_max_num):
            roi = Roi(idx, self, [0, 0], [10, 10])
            self.rois.append(roi)
            self.imageItem.getViewBox().addItem(roi)

    def update_frame(self, frame: np.ndarray):
        self.setImage(frame, autoLevels=False, autoHistogramRange=False, autoRange=False)

    def roi_updated(self, roi: Roi):
        log.debug(f'Update ROI for layer {self.layer_idx}')
        img = self.imageItem
        data = img.image
        slice_params = roi.getAffineSliceParams(data, img)
        vxipc.worker_rpc(RoiActivityTrackerRoutine.update_roi, self.layer_idx, roi.idx, slice_params)


class Roi(pg.RectROI):

    def __init__(self, idx: int, image_widget: ImageWidget, *args, **kwargs):
        pg.RectROI.__init__(self, *args, sideScalers=True, **kwargs)
        self.idx = idx
        self.image_widget = image_widget

        self.sigRegionChangeFinished.connect(self.image_widget.roi_updated)
