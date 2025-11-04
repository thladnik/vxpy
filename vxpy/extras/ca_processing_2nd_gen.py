from __future__ import annotations
from typing import List, Dict, Union, Callable, Optional, Set

import matplotlib as mpl
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore, QtGui
import copy
from PySide6.QtWidgets import QProgressBar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
#TODO: dependencies need an upgrade for cellpose (problem if vxpy is installed prior to cellpose --> cellpose dependency clash... solution install cellpose first)
from cellpose.models import CellposeModel
from cellpose import models
# from stardist.models import StarDist2D
from csbdeep.utils import normalize

from multiprocessing import Process, Queue
import multiprocessing as mp
from skimage.measure import regionprops, label
from scipy.ndimage import binary_erosion
from skimage.segmentation import find_boundaries
import torch
import cv2
import math

import vxpy.core.attribute as vxattribute
import vxpy.core.event as vxevent
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.utils import widgets
from vxpy.extras.server import ScanImageFrameReceiverTcpServer
# from vxpy.extras.sys_con import SysConRoutine
from vxpy.extras.Watershed import WatershedSegmenter

log = vxlogger.getLogger(__name__)


def get_roi_color(index: int):
    return (255 * np.array(mpl.colormaps['tab10'](index)[:3])).astype(np.uint8)


def run_detect_rois(
    diameter: float,
    cellprob_threshold: float,
    flow_threshold: float,
    mproj: np.ndarray,
    layer_idx: int,
    strategy: str,
    queue: mp.Queue,
    device_id: int = 0,
) -> None:
    """
    Run ROI (Region of Interest) detection using different segmentation strategies.

    Args:
        diameter (float): Expected object diameter for segmentation.
        cellprob_threshold (float): Cell probability threshold (Cellpose).
        flow_threshold (float): Flow threshold (Cellpose).
        mproj (np.ndarray): 2D image or projection to segment.
        layer_idx (int): Layer index (for identification in results).
        strategy (str): Segmentation strategy ('cellpose', 'watershed', ...).
        queue (multiprocessing.Queue): Queue to push results into.
        device_id (int, optional): GPU device ID. Defaults to 0.

    Puts into queue:
        ('result', layer_idx, masks, contour_mask)
    """

    print(f"Running {strategy} on layer {layer_idx}, shape: {mproj.shape, mproj.dtype} on GPU {device_id}")

    if strategy == "cellpose":

        torch.cuda.set_device(device_id)
        model = CellposeModel(
            gpu=True)

        masks, flows, _ = model.eval(
            mproj,
            channels=[0, 0],
            diameter=diameter,
            cellprob_threshold=cellprob_threshold,
            flow_threshold=flow_threshold)

        print(f"min {np.min(masks)} max {np.max(masks)}, unique: {len(np.unique(masks))}")


    # Experimental addition
    # elif strategy == "stardist":
    #     os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    #     model = StarDist2D.from_pretrained('2D_versatile_fluo')
    #     # image_norm = normalize(mproj.astype(np.float32), 1, 99.8)
    #     masks, _ = model.predict_instances(mproj)
    #     plot_labeled_mask(masks, title=f"Instance Mask (Cellpose) {layer_idx}")
    #     print(f"min {np.min(masks)} max {np.max(masks)}, unique: {np.unique(masks)}")

    # elif strategy == "bioimageio":
    #     print(f"Running bioimageio on layer {layer_idx}, shape: {mproj.shape}, dtype: {mproj.dtype} on GPU {device_id}")
    #     # Normalize if needed (optional)
    #     mproj_norm = (mproj - np.min(mproj)) / (np.max(mproj) - np.min(mproj))
    #     # Prepare model
    #     model = torch.jit.load("model.pt").to(f"cuda:{device_id}")
    #     model.eval()
    #     input_tensor = transforms.ToTensor()(mproj_norm).unsqueeze(0).to(f"cuda:{device_id}")
    #     with torch.no_grad():
    #         pred = model(input_tensor)[0, 0].cpu().numpy()
    #     masks = label(pred > 0.5)[0].astype(np.uint16)


    elif strategy == "watershed":
            watershed_segmenter = WatershedSegmenter()
            masks = watershed_segmenter.segment(mproj)

    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    print(f"finished for layer {layer_idx}, masks: {masks.shape}, {masks.dtype}")
    contour_mask = NextGenTrackerRoutine.get_contour_mask(masks)
    queue.put(('result', layer_idx, masks, contour_mask))



class NextGenTrackerRoutine(vxroutine.WorkerRoutine):
    """
    Routine to track ROI activity across multiple layers. Handles automatic segmentation,
    stores ROI masks, thresholds, projection data, and evaluation measurements.
    """

    # -------------------- Output / Frame Settings --------------------
    output_frame_name: str = 'roi_activity_tracker_frame'    # Base name for output frames for attribute file
    frame_width: int = 256                                   # Width of each iamge frame
    frame_height: int = 256                                  # Height of each image frame #TODO: Is this not better done as init ?
    frame_dtype: str = 'float64'                             # Data type of frame arrays
    layer_max_num: int = 5                                   # Max number of layers to track
    analysis_box_max_num: int = layer_max_num*2

    # -------------------- Runtime / Trigger --------------------
    trigger: vxevent.NewDataTrigger = None                     # Trigger for new incoming data
    current_layer_num: int = -1                                # Index of currently processed layer
    new_metadata: bool = False                                 # Flag: indicating new metadata is available
    attrs_written_to_file: List[str] = []                      # List of attributes already written to Attribute writer class

    # -------------------- ROI Settings --------------------
    roi_max_num: int = 10                                    # Max number of ROIs that can be tracked across all layers #TODO: here Problem for larger numbers ... why ?
    roi_slice_params: Dict[tuple, BaseROI] = {}                 # Stores ROI class instance (layer_idx, roi_idx) -> ROI
    rois_to_process: Dict[tuple, BaseROI] = {}
    roi_thresholds: Dict[tuple, int] = {}                   # Threshold value for triggers per ROI
    initial_roi_trigger_threshold = 2                       # Initial trigger threshold value # TODO: what should this be ?


    roi_analysis_boxes: Dict[tuple, Analysis_Box] ={}
    rois_to_analyse: Dict[tuple, BaseROI] = {}               # Stores ROI class instance (layer_idx, roi_idx) -> ROI that are selected via analysis boxes

    # -------------------- Default Segmentation Parameters --------------------
    number_of_projection_frames: int = 60                    # Default number of frames used for projection in automated cell segmentation
    q_min: int = 0                                           # Min quantile cut off for projections
    q_max: int = 100                                         # Max quantile cutoff for projections
    projection_calculation: str = "mean"                     # How projection is calculated
    lower_px_threshold: int = 10                             # Pixel threshold for image plots
    segmentation_strategy: str = "cellpose"                  # Default segmentation strategy
    #Cellpose parameters
    diameter: int = 10                                       # Expected object diameter for segmentation
    cellprob_threshold: float = 0.0                          # Cellpose probability threshold
    flow_threshold: float = 1.5                              # Cellpose flow threshold
    pretrained_model: str = "cpsam"                          # Pretrained model name (default in cellpose)

    # -------------------- Progress Tracking --------------------
    layer_progress: Dict[int, float] = {}                      # Tracks segmentation progress of layers
    current_progress: float = 0.0                              # Overall segmentation progress percentage per segmentation
    start_auto_roi_search = False
    layer_to_segment = None

    layer_masks: Dict[int, Dict[str, np.ndarray]] = {}

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the tracker routine, including queues and runtime flags.

        Args:
            *args: Passed to base WorkerRoutine.
            **kwargs: Passed to base WorkerRoutine.
        """
        super().__init__(*args, **kwargs)  # Initialize base class

        # Frame placeholder list for projections
        self._f0: list[int] = [0] * 20

        # Queue for multiprocessing of automated segmentation results
        self.segmentation_queue: Queue = Queue()

        # Store cell segmentation masks for each layer

        # Runtime flags / counters
        self.current_auto_segment: bool = False  # Flag: Whether auto segmentation is active (prohibits new segmentations while already running)
        self.expected_run_results: int = 0       # How many segmentation results (layers) are expected
        self.current_run_results: int = 0        # Number of segmentation results received
        self.is_pool_closed: bool = True         # Flag: Whether the multiprocessing pool is closed

        print("Initialized tracker routine new")

    def require(self) -> bool:
        """
        Define and register all required attributes for layers, ROIs, and triggers.

        Returns:
            bool: Always True if setup succeeds.
        """
        # Get frame type and shape based on class-level configuration
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        shape = (self.frame_width, self.frame_height)

        # Create attributes for each layer and its ROIs
        for layer_idx in range(self.layer_max_num):

            # Frame attribute: stores full layer data
            vxattribute.ArrayAttribute(f'{self.output_frame_name}_{layer_idx}', shape, dtype)

            for roi_idx in range(self.roi_max_num):
                # print(f'Create ROI {roi_idx}')
                # Initialize ROI slice container and threshold
                self.roi_slice_params[(layer_idx, roi_idx)] = BaseROI(layer_idx= layer_idx, roi_idx=roi_idx)
                self.roi_thresholds[(layer_idx, roi_idx)] = self.initial_roi_trigger_threshold

                # Create ROI attributes for raw value and z-score
                vxattribute.ArrayAttribute(
                    self.roi_name(layer_idx, roi_idx), (1,), vxattribute.ArrayType.float64
                )
                vxattribute.ArrayAttribute(
                    f'{self.roi_name(layer_idx, roi_idx)}_zscore', (1,), vxattribute.ArrayType.float64
                )

            # Create trigger attribute for signaling ROI updates on this layer
            vxattribute.ArrayAttribute(self.trigger_name(layer_idx), (1,), vxattribute.ArrayType.uint8)

        return True

    def initialize(self) -> None:
        """
        Set up runtime triggers to start processing incoming frames.
        """
        # Trigger fires whenever a new scanimage frame is available
        self.trigger = vxevent.NewDataTrigger('scanimage_frame', callback=self._process_frame)
        self.trigger.set_active()  # Enable trigger immediately

    def main(self, *args, **kwargs) -> None:
        """
        Main loop of the routine.

        Note:
            Processing is event-driven (via trigger callback), so this
            function remains empty.
        """
        # Routine only reacts to the trigger callback

        if self.start_auto_roi_search == True:
            self.button_start_segmentation_clicked(layer_id = self.layer_to_segment)
            self.start_auto_roi_search = False
        pass


    def _process_frame(self, last_idx, last_time, last_frame) -> None:
        """
        Process the last acquired input frame, update ROI activity, and handle evaluation.

        Args:
            last_idx (int): Index of the last received frame.
            last_time (float): Timestamp of the last received frame.
            last_frame (np.ndarray): Raw frame data from the acquisition.
        """
        # Get current layer number from the ScanImageFrame server
        layer_num = ScanImageFrameReceiverTcpServer.instance().layer_num

        self.check_segmentation_result()

        # If layer has changed, reset ROI metadata
        if self.current_layer_num != layer_num:
            self.new_metadata = True
            self.current_layer_num = layer_num

            # Reset all ROI slices for all layers and ROIs
            for (layer_idx, roi_idx) in self.roi_slice_params.keys():
                self.roi_slice_params[(layer_idx, roi_idx)] = BaseROI(layer_idx= layer_idx, roi_idx=roi_idx)

        # Retrieve the last frame index from system attributes
        _, _, last_frame_index = vxattribute.get_attribute('scanimage_frame_index')[int(last_idx)]

        # Ensure frame is float64 for consistent processing
        last_frame = last_frame.astype(np.float64)

        # -------------------- Frame preprocessing --------------------
        # Zero out pixels above histogram threshold
        preprocessed_frame = np.where(last_frame < np.histogram(last_frame, bins=2)[1][1], last_frame, 0)
        # Zero out pixels below minimum threshold
        preprocessed_frame = np.where(preprocessed_frame > self.lower_px_threshold, preprocessed_frame, 0)

        # Write preprocessed frame to the attribute corresponding to the current layer
        current_layer_idx = int(last_frame_index) % ScanImageFrameReceiverTcpServer.instance().layer_num
        vxattribute.write_attribute(f'{self.output_frame_name}_{current_layer_idx}', preprocessed_frame)

        # -------------------- ROI activity calculation --------------------
        over_thresh = False  # Flag indicating if any ROI is over the corresponding trigger threshold TODO: set this up for specific ROIs ?

        for (layer_idx, roi_idx), roi in self.roi_slice_params.items():
            # Skip if not the current layer or ROI not defined
            if layer_idx != current_layer_idx or roi.tracked is False:
                continue

            roi_str = self.roi_name(layer_idx, roi_idx)  # Attribute name for this ROI
            activity = roi.calculate_activity(preprocessed_frame)  # Compute activity
            vxattribute.write_attribute(roi_str, activity)  # Write activity to attribute

            # Update over-threshold flag
            over_thresh = over_thresh or activity > self.roi_thresholds[(layer_idx, roi_idx)]

            # Add ROI attribute to file if not already written
            if roi_str not in self.attrs_written_to_file:
                vxattribute.write_to_file(self, roi_str)
                self.attrs_written_to_file.append(roi_str)

        # -------------------- Trigger attribute --------------------
        trigger_str = self.trigger_name(current_layer_idx)
        vxattribute.write_attribute(trigger_str, int(over_thresh))  # Write trigger
        if trigger_str not in self.attrs_written_to_file:
            vxattribute.write_to_file(self, trigger_str)
            self.attrs_written_to_file.append(trigger_str)

        self._update_rois_for_processing()
        self.update_cells_in_analysis_boxes()

        # print(f"we want to test some stuff: {self.cellprob_threshold, self.number_of_projection_frames, self.q_max, self.projection_calculation}")

    def _update_rois_for_processing(self):

        self.rois_to_process.clear()

        for (layer_idx, roi_idx), roi in self.roi_slice_params.items():
            if roi.tracked:
                self.rois_to_process[(layer_idx, roi_idx)] = roi


    def get_projection_for_layer(self, layer_idx: int, n_frames: int, mode: str = 'mean') -> np.ndarray | None:
        """
        Compute a projection (mean, max, etc.) of the last `n_frames` for a given layer.

        Args:
            layer_idx (int): Index of the layer to process.
            n_frames (int): Number of frames to use for projection.
            mode (str): Projection method. One of:
                        'mean', 'max', 'min', 'sum', 'std', 'median'.

        Returns:
            np.ndarray | None: Projection image (2D array), or None if no frames available.
        """
        # Read last n_frames from attribute storage
        _, _, frames = vxattribute.read_attribute(f'{self.output_frame_name}_{layer_idx}', last=n_frames)

        if frames is None or len(frames) == 0:
            return None

        # Dispatch by projection mode
        if mode == 'mean':
            return np.mean(frames, axis=0)
        elif mode == 'max':
            return np.max(frames, axis=0)
        elif mode == "min":
            return np.min(frames, axis=0)
        elif mode == "sum":
            return np.sum(frames, axis=0)
        elif mode == "std":
            return np.std(frames, axis=0)
        elif mode == "median":
            return np.median(frames, axis=0)
        else:
            raise ValueError(f'Invalid mode {mode}. Must be one of mean/max/min/sum/std/median.')


    def button_start_segmentation_clicked(self, layer_id: int | None = None) -> None:
        """
        Start segmentation on one or all layers.

        Args:
            layer_id (int | None): If None, segment all layers. Otherwise, segment only the given layer.
        """
        if layer_id is not None:
            log.info(f"Start segmentation on Layer ID: {layer_id}")
        else:
            log.info("Start segmentation on ALL Layers")

        # Determine which layers to process
        if layer_id is None:
            num_layers = ScanImageFrameReceiverTcpServer.instance().layer_num
            layer_indices = list(range(num_layers))
        else:
            layer_indices = [layer_id]
            num_layers = 1

        # Reset state
        self.is_pool_closed = False
        self.current_run_results = 0
        self.expected_run_results = num_layers
        self.layer_progress = {idx: 0.0 for idx in layer_indices}
        self.current_progress = 0.0

        # Build projections for each layer
        projections = []
        for layer_idx in layer_indices:
            mproj = self.get_projection_for_layer(layer_idx, self.number_of_projection_frames, self.projection_calculation)
            if mproj is None:
                log.warning(f"No data to segment for layer {layer_idx}")
                return

            # Clip projection pixel values to quantile thresholds before segmentation
            mproj = self.quantile_clipping(mproj, self.q_min, self.q_max)
            projections.append(mproj)

        # Setup multiprocessing manager and result queue
        self.manager = mp.Manager()
        self.segmentation_queue = self.manager.Queue()

        # Use as many processes as layers or available GPUs (whichever is smaller)
        num_gpus = torch.cuda.device_count()
        # processes = min(len(layer_indices), num_gpus)

        if num_gpus == 0:
            log.warning("No GPUs available, falling back to CPU segmentation")
            processes = 1
        else:
            processes = min(len(layer_indices), num_gpus)


        # Create worker pool
        self.pool = mp.Pool(processes=processes)

        # Dispatch segmentation tasks (round-robin GPU assignment)
        for i, (layer_idx, mproj) in enumerate(zip(layer_indices, projections)):
            device_id = i % processes
            args = (
                self.diameter,
                self.cellprob_threshold,
                self.flow_threshold,
                mproj,
                layer_idx,
                self.segmentation_strategy,
                self.segmentation_queue,
                device_id,
            )
            self.pool.apply_async(run_detect_rois, args=args)

    def check_segmentation_result(self) -> None:
        """
        Poll the segmentation queue for finished results and update progress.

        Notes:
            - Updates self.layer_masks with results.
            - Tracks progress across all layers.
            - Shuts down the pool when all results are collected.
        """
        # Collect results from queue while segmentation is active
        while self.current_auto_segment and self.segmentation_queue and not self.segmentation_queue.empty(): #
            print("Scanning for results...")
            msg = self.segmentation_queue.get()

            if msg[0] == 'result':
                _, layer_idx, merged_mask, contour_mask = msg
                # Store segmentation result as labled masks
                self.layer_masks[layer_idx] = {
                    'merged_mask': merged_mask,
                    'contour_mask': contour_mask}

                self.current_run_results += 1
                # Mark this layer as complete
                self.layer_progress[layer_idx] = 1.0

        # Compute overall progress across all layers
        total_layers = self.expected_run_results
        if total_layers > 0:
            self.current_progress = (sum(self.layer_progress.values()) / total_layers) * 100

        # If all layers are done, clean up pool and manager
        if (
            self.expected_run_results == self.current_run_results
            and not self.is_pool_closed
            and self.current_auto_segment
        ):
            print("All segmentations complete.")
            self.current_auto_segment = False
            self.pool.close()
            self.pool.join()
            self.manager.shutdown()
            self.is_pool_closed = True

    def update_cells_in_analysis_boxes(self):
        """
        Updates all ROI instances in self.rois_to_analyse based on current analysis boxes.
        Ensures that only cells that have at least one pixel in any box are included.
        """
        current_cells = set()  # Track all (layer_idx, cell_label) currently inside any box

        for (layer_idx, box_idx), slice_params in self.roi_analysis_boxes.items():
            # print(f"slice_params: {slice_params}")
            y_slice = slice_params['y_slice']
            x_slice = slice_params['x_slice']

            if layer_idx not in self.layer_masks or 'merged_mask' not in self.layer_masks[layer_idx]:
                continue

            # Extract masks for this layer
            mask = self.layer_masks[layer_idx]['merged_mask']
            contour_mask = self.layer_masks[layer_idx]['contour_mask']
            mask_patch = mask[y_slice, x_slice]

            # Get unique labels in this patch, excluding background
            unique_labels = np.unique(mask_patch)
            unique_labels = unique_labels[unique_labels != 0]

            for label in unique_labels:
                current_cells.add((layer_idx, label))

                # Only create ROI if it doesn't exist yet
                if (layer_idx, label) not in self.rois_to_analyse:
                    points = self.get_contour_outline(mask, label)# get all pixels of this label
                    roi_instance = GeneralPolylineROI(
                        params=points,
                        layer_idx=layer_idx,
                        roi_idx=label,
                        reference_frame_shape=(
                            ScanImageFrameReceiverTcpServer.instance().frame_height,
                            ScanImageFrameReceiverTcpServer.instance().frame_width
                        )
                    )
                    # print(f"Pixel mask shape of roi instance: {roi_instance.pixel_mask.shape} in layer {layer_idx, label}")
                    self.rois_to_analyse[(layer_idx, label)] = roi_instance

        # Remove any old ROIs that are no longer inside any box
        for key in list(self.rois_to_analyse.keys()):
            if key not in current_cells:
                del self.rois_to_analyse[key]

        # print(f"self.rois_to_analyse: {len(self.rois_to_analyse)}")

    @staticmethod
    def quantile_clipping(frame: np.ndarray, q_min: float = 0.0, q_max: float = 100.0) -> np.ndarray:
        """
        Clamp pixel values outside a quantile range.

        Args:
            frame (np.ndarray): Input image or frame.
            q_min (float): Lower quantile in percent (0–100).
            q_max (float): Upper quantile in percent (0–100).

        Returns:
            np.ndarray: Frame with values clipped to quantile boundaries.
        """
        # Convert percentages to fractions
        q_min_frac = q_min / 100
        q_max_frac = q_max / 100

        # Get quantile thresholds
        lower = np.quantile(frame, q_min_frac)
        upper = np.quantile(frame, q_max_frac)

        # Clamp values to range
        return np.clip(frame, lower, upper)

    @staticmethod
    def get_contour_mask(label_mask: np.ndarray) -> np.ndarray:
        """
        Extract contours of labeled regions in a mask.

        Args:
            label_mask (np.ndarray): 2D mask with 0 as background and positive integers as region labels.

        Returns:
            np.ndarray: Contour mask (same shape) where pixel values = label IDs at contour positions.
        """
        contour = np.zeros_like(label_mask, dtype=np.uint8)

        for label in np.unique(label_mask):
            if label == 0:
                continue  # skip background

            # Create binary mask for this label
            binary_region = np.uint8(label_mask == label) * 255

            # Extract contours for the region
            contours, _ = cv2.findContours(binary_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            # Draw contours into mask (label ID used as intensity value)
            cv2.drawContours(contour, contours, -1, int(label), thickness=0)

        return contour

    @staticmethod
    def roi_name(layer_idx: int, roi_idx: int) -> str:
        """
        Construct a unique ROI name from layer and ROI indices.
        """
        return f'roi_activity_{layer_idx}_{roi_idx}'

    @staticmethod
    def trigger_name(layer_idx: int) -> str:
        """
        Construct a unique trigger name for a given layer index.
        """
        return f'roi_activity_trigger_{layer_idx}'

    @staticmethod
    def find_nearest_label(y: int, x: int, label_mask: np.ndarray) -> int | None:
        """
        Find the label ID nearest to a given (y, x) coordinate in a mask.

        Args:
            y (int): Row coordinate.
            x (int): Column coordinate.
            label_mask (np.ndarray): 2D mask with 0 as background and positive integers as region labels.


        Returns:
            int | None: Label ID nearest to (y, x), or None if no labels exist.
        """
        roi_coords = np.argwhere(label_mask > 0)  # get coordinates of all labeled pixels
        if roi_coords.size == 0:
            return None

        # Compute squared Euclidean distances to (y, x)
        distances = np.sum((roi_coords - [y, x]) ** 2, axis=1)

        # Find nearest label coordinate
        nearest_coord = roi_coords[np.argmin(distances)]
        return label_mask[tuple(nearest_coord)]

    @staticmethod
    def get_contour_outline(label_mask: np.ndarray, label_id: int) -> list[tuple[int, int]] | None:
        """
        Get the outer contour of a labeled region as a list of coordinates.

        Args:
            label_mask (np.ndarray): 2D mask with 0 as background and positive integers as region labels.
            label_id (int): Label ID of the region.

        Returns:
            list[tuple[int, int]] | None: List of (y, x) coordinates for contour,
            or None if no contour is found.
        """
        # Keep only the pixels of the target label
        mask = (label_mask == label_id).astype(np.uint8)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return None

        # Extract largest contour (outer boundary)
        largest_contour = max(contours, key=cv2.contourArea)

        # Convert to (y, x) tuples instead of OpenCV’s [[x,y]] format
        return [(pt[0][1], pt[0][0]) for pt in largest_contour]




class NextGenTrackerWidget(vxui.WorkerAddonWidget):

    """
    Main widget for managing imaging streams, ROI tracking, and visualization
    within the NextGenTracker system.

    This class extends `vxui.WorkerAddonWidget` and provides:
    - An image stream viewer (multi-layer plots).
    - ROI (Region of Interest) controls and visualization.
    - Adjustable display and segmentation settings.
    - Integration with frame update routines.
    """

    display_name = 'Imaging stream'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize tracking state
        self.current_num_layers = -1
        self.image_plots = {}  # layer_idx -> ImagePlot instance
        self.histograms = {}    # layer_idx -> Image Plot histogram
        self.init_histograms = []
        self.rois = {}          # (layer_idx, roi_idx) -> Pyqt Graph ROI instance (ellipse or polyline)
        self.analysis_boxses = {}
        self.threshold_widgets = {} # roi_index -> threshold widget


        self.selected_measurement = "mean"  # projection_calculation for image plot streams
        self.frame_window = 10              # number of frames to use for projections

        # === Layout Setup ===
        self.central_widget.setLayout(QtWidgets.QVBoxLayout())

        # --- Warning label ---
        warning_label = QtWidgets.QLabel(
            '!!! WARNING: disconnect imaging client BEFORE closing vxpy !!!')
        warning_label.setStyleSheet('font-weight:bold; color: #FF0000; text-align: center; '
                                    'border: 1px solid #FF0000; padding: 5px;')
        self.central_widget.layout().addWidget(warning_label)

        # --- Collapsible Help section ---
        help_panel = CollapsibleHelp("Help", parent=self)
        self.central_widget.layout().addWidget(help_panel)

        # --- Splitter between plots and control panel ---
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.central_widget.layout().addWidget(splitter, stretch=1)

        # === Left side: Image plot container ===
        self.img_plot_widget = pg.GraphicsLayoutWidget()
        splitter.addWidget(self.img_plot_widget)
        self.cols = 0
        self.rows = 0

        # === Right side: Controls ===
        right_container = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container)
        splitter.addWidget(right_container)

        # --- ROI control group ---
        self.selected_roi_container = QtWidgets.QGroupBox("Selected ROI Controls")
        self.selected_roi_container.setLayout(QtWidgets.QVBoxLayout())

        # Scroll area inside the group box
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.selected_roi_container.layout().addWidget(self.scroll_area)

        # Widget and grid layout inside the scroll area
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QGridLayout()
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        # --- Controls and Settings Tabs ---
        self.tabs = QtWidgets.QTabWidget()

        # --- Controls tab (your original buttons) ---
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QVBoxLayout(button_container)

        self.add_auto_btn = QtWidgets.QPushButton('Automated ROI Search')
        self.add_auto_btn.clicked.connect(lambda: self.automated_roi_search())
        button_layout.addWidget(self.add_auto_btn)

        # Progress bar (initially hidden)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)

        # # Toggle mask button
        self.toggle_mask_btn = QtWidgets.QPushButton('Show ROI mask')
        button_layout.addWidget(self.toggle_mask_btn)
        self.toggle_mask_btn.clicked.connect(lambda: self.toggle_mask(only_contours=True))
        self.toggle_mask_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.toggle_mask_btn.customContextMenuRequested.connect(lambda _: self.toggle_mask(only_contours=False))

        ### Experimental:
        # self.eval_button = QtWidgets.QPushButton('Get Evaluation')
        # self.eval_button.clicked.connect(self.get_evaluation)
        # button_layout.addWidget(self.eval_button)
        ###

        self.selected_histogram_layer = None
        self.plot_highlight_rect = None

        # self.open_window_btn = QtWidgets.QPushButton('Export to SysCon')
        # self.open_window_btn.clicked.connect(self.to_holo)
        # button_layout.addWidget(self.open_window_btn)

        button_layout.addStretch()
        self.tabs.addTab(button_container, "Controls")

        # --- Display Settings tab ---
        display_settings_container = QtWidgets.QWidget()
        display_settings_layout = QtWidgets.QFormLayout(display_settings_container)

        # --- Measurement display type ---
        self.measurement_selector = QtWidgets.QComboBox()
        self.measurement_selector.addItems(["mean", "median", "std", "min", "max", "sum"])
        display_settings_layout.addRow("Display Measurement:", self.measurement_selector)

        # --- Frame averaging window size ---
        self.frame_avg_spin = QtWidgets.QSpinBox()
        self.frame_avg_spin.setRange(1, 1000)
        self.frame_avg_spin.setValue(10)
        display_settings_layout.addRow("Frames for Display:", self.frame_avg_spin)

        self.pixel_threshold = widgets.IntSliderWidget(
            display_settings_container,
            label='Lower pixel threshold',
            default=NextGenTrackerRoutine.instance().lower_px_threshold,
            limits=(1, 2 ** 16),
            step_size=10
        )
        self.pixel_threshold.connect_callback(self.update_pixel_threshold)
        display_settings_layout.addRow(self.pixel_threshold)

        # --- Display Reset Button ---
        display_reset_btn = QtWidgets.QPushButton("Reset to Defaults")
        display_reset_btn.clicked.connect(self.reset_display_settings_to_defaults)
        display_settings_layout.addRow(display_reset_btn)

        self.tabs.addTab(display_settings_container, "Display")

        # --- Segmentation Settings tab ---
        segmentation_settings_container = QtWidgets.QWidget()
        segmentation_settings_layout = QtWidgets.QFormLayout(segmentation_settings_container)

        # --- Measurement display type ---
        self.segmentation_measurement_selector = QtWidgets.QComboBox()
        self.segmentation_measurement_selector.addItems(["mean", "median", "std", "min", "max", "sum"])
        segmentation_settings_layout.addRow("Segmentation Measurement:", self.segmentation_measurement_selector)


        # --- Timeframe for Segmentation ---
        self.segmentation_timeframe_edit = QtWidgets.QSpinBox()
        self.segmentation_timeframe_edit.setRange(1, 1000000)  # Only positive ints within this range
        self.segmentation_timeframe_edit.setValue(NextGenTrackerRoutine.instance().number_of_projection_frames)
        segmentation_settings_layout.addRow("Timeframe:", self.segmentation_timeframe_edit)

        # --- Quantile Remove Option with Min/Max SpinBoxes ---
        quantile_widget = QtWidgets.QWidget()
        quantile_layout = QtWidgets.QHBoxLayout(quantile_widget)
        quantile_layout.setContentsMargins(0, 0, 0, 0)
        quantile_layout.setSpacing(10)
        min_label = QtWidgets.QLabel("Min:")
        quantile_layout.addWidget(min_label)
        self.q_min_spin = QtWidgets.QSpinBox()
        self.q_min_spin.setRange(0, 100)
        self.q_min_spin.setValue(0)
        self.q_min_spin.setSuffix(" %")
        self.q_min_spin.setFixedWidth(60)
        quantile_layout.addWidget(self.q_min_spin)

        # Max label and spin box
        max_label = QtWidgets.QLabel("Max:")
        quantile_layout.addWidget(max_label)
        self.q_max_spin = QtWidgets.QSpinBox()
        self.q_max_spin.setRange(0, 100)
        self.q_max_spin.setValue(100)
        self.q_max_spin.setSuffix(" %")
        self.q_max_spin.setFixedWidth(60)
        quantile_layout.addWidget(self.q_max_spin)

        # Add the quantile widget as a row in your layout
        segmentation_settings_layout.addRow("Quantile Remove:", quantile_widget)

        # --- Segmentation Strategy ---
        self.segmentation_strategy = QtWidgets.QComboBox()
        self.segmentation_strategy.addItems(["cellpose", "watershed"]) # , "stardist"
        self.segmentation_strategy.setCurrentText("cellpose")
        segmentation_settings_layout.addRow("Segmentation Strategy:", self.segmentation_strategy)

        # Group Cellpose params in a widget
        self.cellpose_params_widget = QtWidgets.QWidget()
        cellpose_params_layout = QtWidgets.QFormLayout(self.cellpose_params_widget)

        self.cellpose_diameter = QtWidgets.QSpinBox()
        self.cellpose_diameter.setRange(1, 100)
        self.cellpose_diameter.setValue(10)
        cellpose_params_layout.addRow("Cellpose Diameter:", self.cellpose_diameter)

        self.cellpose_cellprob = QtWidgets.QDoubleSpinBox()
        self.cellpose_cellprob.setDecimals(2)
        self.cellpose_cellprob.setRange(-1.0, 1.0)
        self.cellpose_cellprob.setSingleStep(0.1)
        self.cellpose_cellprob.setValue(0.0)
        cellpose_params_layout.addRow("CellProb Threshold:", self.cellpose_cellprob)

        self.cellpose_flow = QtWidgets.QDoubleSpinBox()
        self.cellpose_flow.setDecimals(2)
        self.cellpose_flow.setRange(0.0, 10.0)
        self.cellpose_flow.setSingleStep(0.1)
        self.cellpose_flow.setValue(1.5)
        cellpose_params_layout.addRow("Flow Threshold:", self.cellpose_flow)

        segmentation_settings_layout.addRow(self.cellpose_params_widget)

        # Connect to update visibility
        self.segmentation_strategy.currentTextChanged.connect(self.update_segmentation_params_visibility)

        # Initialize visibility
        self.update_segmentation_params_visibility()

        # --- Display Reset Button ---
        segmentation_reset_btn = QtWidgets.QPushButton("Reset to Defaults")
        segmentation_reset_btn.clicked.connect(self.reset_segment_settings_to_defaults)
        segmentation_settings_layout.addRow(segmentation_reset_btn)

        self.tabs.addTab(segmentation_settings_container, "Segmentation")

        # --- Split ROI Controls and Tabbed Controls with a Vertical Splitter ---
        vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_splitter.addWidget(self.selected_roi_container)
        vertical_splitter.addWidget(self.tabs)
        vertical_splitter.setStretchFactor(0, 3)  # ROI controls take more space
        vertical_splitter.setStretchFactor(1, 1)  # Tabs take less

        right_layout.addWidget(vertical_splitter)

        # --- Frame routine integration ---
        self.frame_name = NextGenTrackerRoutine.instance().output_frame_name
        self.connect_to_timer(self.update_frame)

    def update_segmentation_params_visibility(self) -> None:
        """
        Show or hide segmentation parameter widgets depending on the selected strategy.
        Also updates the active segmentation strategy in the routine instance.
        """
        strategy = self.segmentation_strategy.currentText()

        if strategy == "cellpose":
            self.cellpose_params_widget.show()
        else:
            self.cellpose_params_widget.hide()

        # Sync selected strategy with the routine
        NextGenTrackerRoutine.instance().segmentation_strategy = strategy

    def reset_display_settings_to_defaults(self) -> None:
        """
        Reset display-related settings (measurement type, averaging window, thresholds)
        back to their default values.
        """
        self.measurement_selector.setCurrentText("mean")
        self.frame_avg_spin.setValue(10)
        self.pixel_threshold.set_value(10)

    def reset_segment_settings_to_defaults(self) -> None:
        """
        Reset segmentation-related settings (measurement type, timeframe, thresholds, strategy, etc.)
        back to their default values.
        """
        self.segmentation_measurement_selector.setCurrentText("mean")
        self.segmentation_timeframe_edit.setValue(60)
        self.q_min_spin.setValue(0)
        self.q_max_spin.setValue(100)

        # Reset strategy and Cellpose parameters
        self.segmentation_strategy.setCurrentText("cellpose")
        self.cellpose_diameter.setValue(10)
        self.cellpose_cellprob.setValue(0.0)
        self.cellpose_flow.setValue(1.5)

    def calculate_frame(self, frames: np.ndarray) -> np.ndarray:
        """
        Apply the selected aggregation method (mean, std, min, max, sum, median)
        to a stack of frames.

        Args:
            frames (np.ndarray): A stack of image frames (N, H, W).

        Returns:
            np.ndarray: Aggregated single frame (H, W).
        """
        method = self.measurement_selector.currentText()

        if method == "mean":
            return np.mean(frames, axis=0)
        elif method == "std":
            return np.std(frames, axis=0)
        elif method == "min":
            return np.min(frames, axis=0)
        elif method == "max":
            return np.max(frames, axis=0)
        elif method == "sum":
            return np.sum(frames, axis=0)
        elif method == "median":
            return np.median(frames, axis=0)
        else:
            # Fallback for unexpected values
            print(f"Invalid measurement type: {method}, falling back to 'mean'.")
            return np.mean(frames, axis=0)

    def update_frame(self) -> None:
        """
        Pull frames from the routine and update plots, histograms, and UI state.
        Also syncs widget values back to the routine instance.
        """
        routine = NextGenTrackerRoutine.instance()
        layer_num = routine.current_layer_num

        # Ensure segmentation results are checked/updated
        # routine.check_segmentation_result() #TODO: move this to routine?

        # Update progress bar if available
        if hasattr(routine, "current_progress"):
            self.progress_bar.setValue(int(routine.current_progress))

        # Rebuild plots if metadata changed or layer count changed
        if routine.new_metadata or (layer_num != self.current_num_layers):
            self._rebuild_image_plots(layer_num)
            routine.new_metadata = False


        mask_dict = copy.deepcopy(routine.layer_masks)
        mask_keys = list(mask_dict.keys())
        # Update each image plot
        for layer_idx, image_plot in self.image_plots.items():
            idx, time, frame = vxattribute.read_attribute(
                f"{self.frame_name}_{layer_idx}", last=self.frame_window
            )
            if len(idx) == 0:
                continue  # Skip if no frames available

            # Aggregate frames into one representative frame
            frame_avg = self.calculate_frame(frame)
            image_plot.update_frame(frame_avg)

            #Show number of segmented cells
            if layer_idx in mask_keys:
                masks = mask_dict.get(layer_idx)
                merged_mask = masks.get("merged_mask")
                if merged_mask is not None:
                    # Count cells, ignoring background labeled as 0
                    unique_labels = np.unique(merged_mask)
                    n_cells = len(unique_labels) - (1 if 0 in unique_labels else 0)
                    # Update the text label
                    image_plot.mask_text.setText(f"Cells: {n_cells}")


            # Initialize histogram range once per layer
            if self.init_histograms[layer_idx] is True:
                immin, immax = np.min(frame), np.max(frame)
                self.histograms[layer_idx].setHistogramRange(immin, immax)
                self.histograms[layer_idx].setLevels(immin, immax)
                self.init_histograms[layer_idx] = False

        # Update button state (e.g., enable/disable certain actions)
        self.update_button_state()

        # Persist display-related selections
        self.selected_measurement = self.measurement_selector.currentText()
        self.frame_window = self.frame_avg_spin.value()

        # Push segmentation settings back to routine
        routine.number_of_projection_frames = self.segmentation_timeframe_edit.value()
        routine.q_min = self.q_min_spin.value()
        routine.q_max = self.q_max_spin.value()
        routine.projection_calculation = self.segmentation_measurement_selector.currentText()
        routine.diameter = self.cellpose_diameter.value()
        routine.cellprob_threshold = self.cellpose_cellprob.value()
        routine.flow_threshold = self.cellpose_flow.value()

        # Update highlighted rectangle around selected histogram (if any)
        if self.plot_highlight_rect and self.selected_histogram_layer is not None:
            plot_item = self.image_plots[self.selected_histogram_layer].get_plot_item()
            new_rect = plot_item.sceneBoundingRect()
            if new_rect != self.plot_highlight_rect.rect():
                self.plot_highlight_rect.setRect(new_rect)


    def _rebuild_image_plots(self, num_layers: int) -> None:
        """
        Rebuild all image plots and histograms for the given number of layers.

        Args:
            num_layers (int): Number of layers (channels) to display.
        """
        # Clear existing plots
        self.img_plot_widget.clear()
        self.image_plots.clear()
        self.histograms.clear()

        # Layout grid (square-ish arrangement)
        self.cols = math.ceil(math.sqrt(num_layers))
        self.rows = math.ceil(math.sqrt(num_layers))

        # Initialize histogram flags for each layer
        self.init_histograms = [True] * num_layers

        for i in range(num_layers):
            # Create new ImagePlot with ROI and segmentation callbacks
            image_plot = ImagePlot(
                i,
                on_roi_selected=self.handle_roi_click,
                on_histogram_selected=self.select_histogram,
                on_segment_layer=self.automated_roi_search,
                on_analysis_box=self.add_analysis_box
            )

            # Store references
            self.image_plots[i] = image_plot
            self.histograms[i] = pg.HistogramLUTItem(image_plot.image_item)
            # self.histograms[i].disableAutoHistogramRange()  # Optional control

            # Add plot to grid
            self.img_plot_widget.addItem(
                image_plot.plot_item, row=i // self.cols, col=i % self.cols
            )

        # Track current layer count
        self.current_num_layers = num_layers

    def select_histogram(self, layer_idx: int) -> None:
        """
        Show or hide the histogram for a given layer.
        Also toggles plot highlight.

        Args:
            layer_idx (int): Index of the selected layer.
        """

        # Case 1: Same layer clicked again → hide histogram
        if self.selected_histogram_layer == layer_idx:
            self.img_plot_widget.removeItem(self.histograms[layer_idx])
            self._remove_plot_highlight()
            self.selected_histogram_layer = None
            return

        # Case 2: Switch from a different layer
        if self.selected_histogram_layer is not None:
            self.img_plot_widget.removeItem(
                self.histograms[self.selected_histogram_layer]
            )
            self._remove_plot_highlight()

        # Show histogram for the new layer
        self.selected_histogram_layer = layer_idx
        self.img_plot_widget.addItem(
            self.histograms[layer_idx],
            col=self.cols + 1,  # Place histograms in a dedicated column
            row=0,
            rowspan=self.rows,
        )

        # Highlight the associated plot
        self._highlight_plot_item(self.image_plots[layer_idx].get_plot_item())

    def _highlight_plot_item(self, plot_item) -> None:
        """
        Draw a yellow border highlight around a given plot.

        Args:
            plot_item: The plot item to highlight.
        """
        # Ensure only one highlight at a time
        self._remove_plot_highlight()

        rect = plot_item.sceneBoundingRect()
        highlight_rect = QtWidgets.QGraphicsRectItem(rect)
        highlight_rect.setPen(pg.mkPen("y", width=2))
        highlight_rect.setZValue(1000)  # Ensure highlight is on top
        self.img_plot_widget.scene().addItem(highlight_rect)

        self.plot_highlight_rect = highlight_rect

    def _remove_plot_highlight(self) -> None:
        """
        Remove any active highlight rectangle from the plots.
        """
        if getattr(self, "plot_highlight_rect", None):
            self.img_plot_widget.scene().removeItem(self.plot_highlight_rect)
            self.plot_highlight_rect = None


    def add_analysis_box(self, layer_idx: int, x: int, y: int, zoom_factor=None) -> None:

        base_diameter = NextGenTrackerRoutine.instance().frame_width // 4


        position = (x, y)
        # Adjust with zoom factor (avoid divide by zero)
        diameter = (
            base_diameter / zoom_factor
            if zoom_factor and zoom_factor != 0
            else base_diameter
        )

        # Use given position or default to frame center
        if position is not None:
            center_y, center_x = position
        else:
            routine = NextGenTrackerRoutine.instance()
            center_x = routine.frame_width // 2
            center_y = routine.frame_height // 2

        # Convert center to top-left coordinates
        top_left_x = center_x - diameter / 2
        top_left_y = center_y - diameter / 2

        if layer_idx == -1:
            layer_indices = np.arange(0, self.current_num_layers)
        else:
            layer_indices = [layer_idx]

        # Get next available ROI index


        for idx in layer_indices:
            box_idx = self.get_next_free_analysis_box_index()
            if box_idx is None:
                log.warning("Failed to add Box. Maximum number of Boxs exceeded")
                return
            image_plot = self.image_plots.get(idx)
            analysis_box = Analysis_Box(
                layer_idx=idx,
                box_idx=box_idx,
                image_plot=image_plot,
                update_callback=self.analysis_box_update,
                delete_callback=self.delete_analysis_box,
                pos=(0, 0),
                size=(1, 1),  # Temporary, will be updated below
            )
            image_plot.add_roi_to_plot(analysis_box)

            # Place the ROI at the desired location
            analysis_box.setPos((top_left_x, top_left_y))
            analysis_box.setSize((diameter, diameter))

            self.analysis_boxses[(layer_idx, box_idx)] = analysis_box

    def analysis_box_update(self, analysis_box: Analysis_Box, layer_idx: int, box_idx: int,
                            image_plot: ImagePlot) -> None:
        """
        Save the parameters needed to extract the mask for this analysis box.
        Stores integer slices that can be directly used to index the mask.
        """
        log.debug(f"Update Analysis_Box {box_idx} for layer {layer_idx}")

        shape, vectors, origin = analysis_box.getAffineSliceParams(
            image_plot.image_item.image, image_plot.image_item, fromBoundingRect=True
        )

        # Convert to integer pixel coordinates
        x0 = int(round(origin[1]))
        y0 = int(round(origin[0]))
        x1 = x0 + int(round(shape[1]))
        y1 = y0 + int(round(shape[0]))

        # Clip to image bounds
        img_height, img_width = image_plot.image_item.image.shape[:2]
        y0 = max(0, y0)
        x0 = max(0, x0)
        y1 = min(img_height, y1)
        x1 = min(img_width, x1)

        # Store as a dict for clarity
        slice_params = {
            'x_slice': slice(x0, x1),
            'y_slice': slice(y0, y1),
            'origin': origin,
            'shape': shape,
            'vectors': vectors
        }

        # Save to the tracker instance
        routine = NextGenTrackerRoutine.instance()
        routine.roi_analysis_boxes[(layer_idx, box_idx)] = slice_params

    def delete_analysis_box(self, analysis_box: Analysis_Box, layer_idx: int, box_idx:int, image_plot: ImagePlot) -> None:
        log.debug(f"Delete Analysis_Box for layer {layer_idx}")
        # Remove Analysis graphics
        self.rois.pop((layer_idx, box_idx), None)
        # plot.plot_item.getViewBox().removeItem(analysis_box)
        if hasattr(analysis_box, "label"):
            image_plot.plot_item.removeItem(analysis_box.label)
            image_plot.plot_item.removeItem(analysis_box.delete_btn)
        image_plot.plot_item.getViewBox().removeItem(analysis_box)

    def handle_roi_click(self, layer_idx: int, x: int, y: int, roi_style: str, zoom_factor=None) -> None:
        """
        Handle interactive ROI selection from a mouse click.

        Args:
            layer (int): Layer index of the clicked image.
            x (int): X-coordinate in image space.
            y (int): Y-coordinate in image space.
            roi_style (str): Type of ROI ("ellipse", "poly_line", etc.).
            zoom_factor (float, optional): Zoom factor for ellipse ROI.
        """
        routine = NextGenTrackerRoutine.instance()
        mask_data = routine.layer_masks.get(layer_idx, {}).get("merged_mask")

        # Direct ellipse ROI (doesn't require a mask)
        if roi_style == "ellipse":
            self.add_roi(
                layer_idx=layer_idx,
                roi_style=roi_style,
                position=(x, y),
                zoom_factor=zoom_factor,
            )

        # Validate mask availability and click location
        if mask_data is None or not (0 <= x < mask_data.shape[1] and 0 <= y < mask_data.shape[0]):
            return

        # Get ROI label at clicked pixel (or nearest if background)
        label_id = mask_data[y, x]
        if label_id == 0:
            label_id = routine.find_nearest_label(y, x, mask_data)

        if not label_id:
            print("No ROI found")
            return

        # Handle polyline ROI extraction from mask outline
        if roi_style == "poly_line":
            outline = routine.get_contour_outline(mask_data, label_id)
            if outline:
                self.add_roi(
                    layer_idx=layer_idx,
                    roi_style=roi_style,
                    contours=outline,
                )

    def add_roi(
        self,
        layer_idx: int,
        position=None,
        size=None,
        angle_degree=None,
        roi_style="ellipse",
        contours=None,
        zoom_factor=None,
    ) -> None:
        """
        Add a new ROI (Region of Interest) to the specified image layer.

        Args:
            layer_idx (int): Layer index where ROI should be added.
            position (tuple[int, int], optional): (y, x) center position for ROI.
            size (tuple[int, int], optional): Explicit width and height for ROI.
            angle_degree (float, optional): Rotation angle for ellipse ROI.
            roi_style (str): Type of ROI ("ellipse" or "poly_line").
            contours (list, optional): Contour points for polyline ROI.
            zoom_factor (float, optional): Scaling factor for ellipse diameter.
        """
        image_plot = self.image_plots.get(layer_idx)
        if image_plot is None:
            print(f"No ImagePlot found for layer {layer_idx}")
            return

        # Get next available ROI index
        roi_idx = self.get_next_free_roi_index()
        if roi_idx is None:
            log.warning("Failed to add ROI. Maximum number of ROIs exceeded")
            return

        # Register trigger axis on first ROI
        if len(self.rois) == 0:
            vxui.register_with_plotter(
                NextGenTrackerRoutine.trigger_name(layer_idx),
                name=f"Activity trigger for layer {layer_idx}",
                axis="Trigger",
            )

        # Register ROI with plotting system
        vxui.register_with_plotter(
            NextGenTrackerRoutine.roi_name(layer_idx, roi_idx),
            name=f"ROI {roi_idx}",
            axis=f"Layer {layer_idx}",
            color=get_roi_color(roi_idx),
        )
        vxui.register_with_plotter(
            f"{NextGenTrackerRoutine.roi_name(layer_idx, roi_idx)}_zscore",
            name=f"ROI {roi_idx}",
            axis=f"Layer {layer_idx} zscore",
            color=get_roi_color(roi_idx),
        )

        # ------------------------------------------------------------------ #
        # ROI creation depending on style
        # ------------------------------------------------------------------ #
        if roi_style == "ellipse":
            # Base diameter = quarter of frame width
            base_diameter = NextGenTrackerRoutine.instance().frame_width // 4

            # Adjust with zoom factor (avoid divide by zero)
            diameter = (
                base_diameter / zoom_factor
                if zoom_factor and zoom_factor != 0
                else base_diameter
            )

            # Use given position or default to frame center
            if position is not None:
                center_y, center_x = position
            else:
                routine = NextGenTrackerRoutine.instance()
                center_x = routine.frame_width // 2
                center_y = routine.frame_height // 2

            # Convert center to top-left coordinates
            top_left_x = center_x - diameter / 2
            top_left_y = center_y - diameter / 2

            # Rotation angle (default 0°)
            angle = 0 if angle_degree is None else angle_degree

            # Create and configure ROI
            roi = EllipseRoi(
                layer_idx=layer_idx,
                idx=roi_idx,
                image_plot=image_plot,
                update_callback=self.roi_updated,
                delete_callback=self.delete_specific_roi,
                pos=(0, 0),
                size=(1, 1),  # Temporary, will be updated below
            )
            image_plot.add_roi_to_plot(roi)

            roi.setPos((top_left_x, top_left_y))  # Position uses top-left coords
            roi.setSize((diameter, diameter))
            roi.setAngle(angle)

        elif roi_style == "poly_line":
            roi = PolyLineRoi(
                layer_idx,
                roi_idx,
                image_plot,
                points=contours,
                delete_callback=self.delete_specific_roi
            )
            image_plot.add_roi_to_plot(roi)
            self.roi_updated(roi)#, layer_idx, image_plot)

        # Track ROI reference
        self.rois[(layer_idx, roi_idx)] = roi

        # ------------------------------------------------------------------ #
        # UI setup: label + threshold slider
        # ------------------------------------------------------------------ #
        label_button = QtWidgets.QPushButton(f"ROI {roi_idx} [{layer_idx}]")
        label_button.setFlat(True)
        label_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # Context menu → delete ROI
        def context_menu_handler(_):
            self.delete_specific_roi(roi_idx=roi_idx, layer_idx=layer_idx)

        label_button.customContextMenuRequested.connect(context_menu_handler)
        self.scroll_layout.addWidget(label_button, roi_idx, 0)

        # Threshold slider widget
        thresh = widgets.DoubleSliderWidget(
            self.scroll_widget,
            default=NextGenTrackerRoutine.instance().initial_roi_trigger_threshold,
            limits=(
                0,
                2 * NextGenTrackerRoutine.instance().initial_roi_trigger_threshold,
            ),
            step_size=0.1,
        )
        thresh.connect_callback(roi.update_threshold)
        self.scroll_layout.addWidget(thresh, roi_idx, 1)

        # Store UI references
        self.threshold_widgets[roi_idx] = thresh
        roi.label_button = label_button

    def delete_specific_roi(self, layer_idx: int, roi_idx: int) -> None:
        """
        Delete a specific ROI from both the data model and UI.

        Args:
            layer_idx (int): Corresponding layer index of the ROI.
            roi_idx (int): ROI index to delete.
        """
        # Remove from ROI registry
        roi = self.rois.pop((layer_idx, roi_idx), None)
        if roi is None:
            log.warning(f"ROI {roi_idx} not found on layer {layer_idx}")
            return

        # Remove ROI graphics
        plot = self.image_plots[layer_idx]
        plot.plot_item.getViewBox().removeItem(roi)
        if hasattr(roi, "label"):
            plot.plot_item.removeItem(roi.label)
        if hasattr(roi, "delete_btn"):
            plot.plot_item.removeItem(roi.delete_btn)


        # Remove threshold slider
        thresh_widget = self.threshold_widgets.pop(roi_idx, None)
        if thresh_widget:
            self.scroll_widget.layout().removeWidget(thresh_widget)
            thresh_widget.deleteLater()

        # Remove label button
        if hasattr(roi, "label_button"):
            self.scroll_widget.layout().removeWidget(roi.label_button)
            roi.label_button.deleteLater()

        # Update routine state
        routine = NextGenTrackerRoutine.instance()
        del routine.roi_slice_params[(layer_idx, roi_idx)]
        routine.roi_thresholds[(layer_idx, roi_idx)] = (
            routine.initial_roi_trigger_threshold
        )

        # Remove ROI from plotter system
        vxui.remove_from_plotter(
            NextGenTrackerRoutine.roi_name(layer_idx, roi_idx),
            axis=f"Layer {layer_idx}",
        )
        vxui.remove_from_plotter(
            f"{NextGenTrackerRoutine.roi_name(layer_idx, roi_idx)}_zscore",
            axis=f"Layer {layer_idx} zscore",
        )

        log.info(f"Deleted ROI {roi_idx} from layer {layer_idx}")



    def roi_updated(self, roi: Union[EllipseRoi, PolyLineRoi]): #, layer_idx: int, image_plot: ImagePlot) -> None:
        """
        Register and update ROI in the routine when it changes parameters.

        Args:
            roi (EllipseRoi | PolyLineRoi): The updated ROI object.
            layer_idx (int): Index of the image layer the ROI belongs to.
            image_plot (ImagePlot): Plot containing the ROI.
        """
        log.debug(f"Update ROI for layer {roi.layer_idx}, ROI idx {roi.idx}")

        frame_shape = roi.image_plot.image_item.image.shape

        if isinstance(roi, PolyLineRoi):
            # Polyline ROI stores its points directly
            points = roi.getState()["points"]
            roi_instance = GeneralPolylineROI(params=points, layer_idx=roi.layer_idx, roi_idx=roi.idx, reference_frame_shape = frame_shape) # mode="polyline_points",

        elif isinstance(roi, EllipseRoi):
            # Ellipse ROI requires affine slice params
            slice_params = roi.getAffineSliceParams(
                roi.image_plot.image_item.image, roi.image_plot.image_item
            )
            roi_instance = GeneralEllipseROI(params=slice_params, layer_idx=roi.layer_idx, roi_idx=roi.idx, reference_frame_shape = frame_shape) # mode="affine_slice",

        else:
            raise ValueError(f"Invalid ROI type: {type(roi)}")

        # Compute ROI metadata
        # frame_height = ScanImageFrameReceiverTcpServer.instance().frame_height
        # frame_width = ScanImageFrameReceiverTcpServer.instance().frame_width
        # roi_instance.calculate_center() #image_frame=np.zeros((frame_height, frame_width))
        # roi_instance.calculate_z()
        roi_instance.tracked = True

        print(f"New Slices: {roi_instance.x_center, roi_instance.y_center, roi_instance.z_center}")
        # Register ROI in the routine
        NextGenTrackerRoutine.instance().roi_slice_params[(roi.layer_idx, roi.idx)] = roi_instance

    def get_next_free_roi_index(self) -> Optional[int]:
        """
        Find the next available ROI index.

        Returns:
            int | None: Free ROI index, or None if max reached.
        """
        used_indices = {roi_idx for (_, roi_idx) in self.rois.keys()}
        for i in range(NextGenTrackerRoutine.instance().roi_max_num):
            if i not in used_indices:
                return i
        return None

    def get_next_free_analysis_box_index(self) -> Optional[int]:
        used_indices = {box_idx for (layer_idx, box_idx) in self.analysis_boxses.keys()}
        for i in range(NextGenTrackerRoutine.instance().analysis_box_max_num):
            if i not in used_indices:
                return i
        return None

    def toggle_mask(self, only_contours: bool = True) -> None:
        """
        Toggle visibility of segmentation masks for all layers.

        Args:
            only_contours (bool): If True, show contour masks in red.
                                  If False, show full merged masks.
        """
        mask_dict = NextGenTrackerRoutine.instance().layer_masks
        mask_keys = list(mask_dict.keys())

        if not mask_keys:
            QtWidgets.QMessageBox.information(
                self, "No Masks", "No segmentation masks found."
            )
            return

        # Toggle based on the first layer's current state
        first_layer_idx = mask_keys[0]
        first_plot = self.image_plots.get(first_layer_idx)
        target_visibility = not first_plot.mask_visible if first_plot else True

        for layer_idx in mask_keys:
            masks = mask_dict.get(layer_idx)
            image_plot = self.image_plots.get(layer_idx)
            if not image_plot or masks is None:
                continue

            image_plot.mask_visible = target_visibility
            image_plot.mask_item.setVisible(target_visibility)

            if target_visibility:
                if only_contours:
                    # Show contour mask in red
                    mask_array = masks.get("contour_mask")
                    if mask_array is not None:
                        red_mask = np.zeros(
                            (mask_array.shape[0], mask_array.shape[1], 3),
                            dtype=np.uint8,
                        )
                        red_mask[mask_array > 0, 0] = 255  # Red channel
                        image_plot.mask_item.setImage(red_mask)
                    else:
                        image_plot.mask_item.setImage(mask_array)
                else:
                    # Show binary merged mask
                    mask_array = masks.get("merged_mask")
                    image_plot.mask_item.setImage(mask_array > 0)


        self.toggle_mask_btn.setText(
            "Hide ROI mask" if target_visibility else "Show ROI mask"
        )

    def update_button_state(self) -> None:
        """Enable or disable automated segmentation button based on ongoing segmentations."""
        routine = NextGenTrackerRoutine.instance()
        self.add_auto_btn.setEnabled(not routine.current_auto_segment)

    def automated_roi_search(self, layer_idx: int | None = None) -> None:
        """
        Trigger automated ROI detection for the given layer.

        Args:
            layer_idx (int | None): Optional layer index for segmentation in a specific layer.
        """
        routine = NextGenTrackerRoutine.instance()
        if not routine.current_auto_segment:
            routine.current_auto_segment = True

            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # routine.button_start_segmentation_clicked(layer_id=layer_idx)
            routine.start_auto_roi_search = True
            routine.layer_to_segment = layer_idx
        else:
            print("Automated ROI search already running.")

    # def to_holo(self):
    #     """
    #     Export current ROIs to SysConRoutine for downstream processing.
    #     Used to hand off ROIs for stimulation control.
    #     """
    #     syscon = SysConRoutine.instance()
    #     syscon.num_layers = self.current_num_layers
    #     syscon.rois_to_stimulate.clear()
    #     syscon.rois_to_stimulate.update(NextGenTrackerRoutine.instance().roi_slice_params)
    #     syscon.new_rois_set = True



    # def get_evaluation(self) -> None:
    #     """
    #     Open or close the ROI evaluation window.
    #     Allows manual inspection and correction of ROIs.
    #     """
    #     routine = NextGenTrackerRoutine.instance()
    #
    #     if not getattr(routine, "layer_masks", None) or len(routine.layer_masks) == 0:
    #         QtWidgets.QMessageBox.warning(
    #             self, "No ROI Data", "No segmentation masks available for evaluation."
    #         )
    #         return
    #
    #     # Toggle evaluation window
    #     if hasattr(self, "_eval_window") and self._eval_window.isVisible():
    #         routine.eval_active = False
    #         self._eval_window.close()
    #         del self._eval_window
    #     else:
    #         routine.eval_active = True
    #         self._eval_window = EvalWindow(
    #             tracker_routine=routine,
    #             add_roi_callback=self.add_roi,
    #         )
    #         self._eval_window.show()

    @staticmethod
    def update_pixel_threshold(value: int) -> None:
        """
        Update pixel threshold in the core processing routine.

        Args:
            value (int): New pixel threshold value.
        """
        NextGenTrackerRoutine.instance().lower_px_threshold = value

class CollapsibleHelp(QtWidgets.QWidget):
    def __init__(self, title="Help", *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Toggle button (header)
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { font-weight: bold; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_toggled)

        # Collapsible content area
        self.content_area = QtWidgets.QScrollArea()
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.content_area.setMaximumHeight(0)  # collapsed
        self.content_area.setMinimumHeight(0)

        # Inner content (inherits palette from parent)
        help_label = QtWidgets.QLabel(
            "<b>Controls:</b><br>"
            "- Show plot context menu: <i>Right-click on plot area</i><br>"
            "- Add ROI:<br>"
            "&nbsp;&nbsp;• Ellipse ROI: <i>Alt + Left-click</i> (or via context menu)<br>"
            "&nbsp;&nbsp;• Polyline ROI: <i>Shift + Left-click</i> (or via context menu)<br>"
            "- Delete ROI: <i>Right-click on selected ROI in top-right display</i><br>"
            "- Show/Hide Image histogram: <i>Double-click plot area</i><br>"
        )
        help_label.setWordWrap(True)

        inner_widget = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner_widget)
        inner_layout.addWidget(help_label)
        inner_layout.addStretch()

        self.content_area.setWidget(inner_widget)
        self.content_area.setWidgetResizable(True)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

        # Smooth expand/collapse animation
        self.animation = QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def on_toggled(self, checked):
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
        content_height = self.content_area.sizeHint().height()

        self.animation.setStartValue(self.content_area.maximumHeight())
        self.animation.setEndValue(content_height if checked else 0)
        self.animation.start()


class CustomViewBox(pg.ViewBox):
    """
    Custom ViewBox with a context menu specific to each plot.

    Adds ROI creation, mask toggling, zoom reset, and layer segmentation
    to the right-click menu inside a given plot area.
    """

    def __init__(self, parent_plot, *args, **kwargs):
        """
        Args:
            parent_plot (ImagePlot): Reference to the parent ImagePlot object.
            *args, **kwargs: Passed to the pg.ViewBox constructor.
        """
        super().__init__(*args, **kwargs)
        self.parent_plot = parent_plot

        # Enable custom context menu and disable pyqtgraph's default one
        self.setMenuEnabled(True)

    def raiseContextMenu(self, ev):
        """
        Show the context menu when right-clicking inside this ViewBox.

        Args:
            ev (QGraphicsSceneMouseEvent): Mouse event triggering the context menu.
        """
        # Ensure click is inside the plot's bounds
        if not self.sceneBoundingRect().contains(ev.scenePos()):
            return

        # Convert click position to image coordinates
        mouse_point = self.mapSceneToView(ev.scenePos())
        y, x = int(mouse_point.x()), int(mouse_point.y())
        zoom_factor = self.parent_plot.get_zoom_factor()

        # Build context menu
        menu = QtWidgets.QMenu()

        # ROI submenu
        roi_menu = menu.addMenu("Add ROI")
        poly_action = roi_menu.addAction("Polygon ROI")
        ellipse_action = roi_menu.addAction("Ellipse ROI")

        # General actions
        menu.addSeparator()
        toggle_mask_action = menu.addAction("Toggle Mask Overlay")
        reset_zoom_action = menu.addAction("Reset Zoom")
        segment_layer_action = menu.addAction(
            f"Segment Layer {self.parent_plot.layer_idx}"
        )
        analysis_box = menu.addMenu("Add Analysis Box")
        single_analysis_box = analysis_box.addAction(f"Layer {self.parent_plot.layer_idx}")
        all_analysis_box = analysis_box.addAction("All Layers")

        # Show menu and get selected action
        action = menu.exec(ev.screenPos().toPoint())

        # --- Handle actions ---
        # ROI actions
        if action == poly_action and self.parent_plot.on_roi_selected:
            self.parent_plot.on_roi_selected(
                layer_idx=self.parent_plot.layer_idx,
                x=x,
                y=y,
                roi_style="poly_line",
                zoom_factor=zoom_factor,
            )

        elif action == ellipse_action and self.parent_plot.on_roi_selected:
            self.parent_plot.on_roi_selected(
                layer_idx=self.parent_plot.layer_idx,
                x=x,
                y=y,
                roi_style="ellipse",
                zoom_factor=zoom_factor,
            )

        elif action == single_analysis_box and self.parent_plot.on_analysis_box:
            self.parent_plot.on_analysis_box(
                layer_idx=self.parent_plot.layer_idx,
                x=x,
                y=y,
                zoom_factor=zoom_factor,
            )        # Other plot actions
        elif action == all_analysis_box and self.parent_plot.on_analysis_box:
            self.parent_plot.on_analysis_box(
                layer_idx=-1,
                x=x,
                y=y,
                zoom_factor=zoom_factor,
            )  # Other plot actions
        elif action == toggle_mask_action:
            self.parent_plot.set_mask_visible()

        elif action == reset_zoom_action:
            self.parent_plot.reset_zoom()

        elif action == segment_layer_action:
            self.parent_plot.request_segmentation()

class ImagePlot:
    """
    A wrapper around pyqtgraph's PlotItem for displaying and interacting with
    per-layer images, ROIs, masks, and user input events.
    """

    def __init__(self, layer_idx, on_roi_selected=None, on_histogram_selected=None, on_segment_layer=None, on_analysis_box = None):
        """
        Initialize an ImagePlot.

        Args:
            layer_idx (int): Index of the image layer this plot belongs to.
            on_roi_selected (callable): Callback when an ROI is created.
            on_histogram_selected (callable): Callback for double-click (histogram).
            on_segment_layer (callable)): Callback for triggering segmentation on this layer.
        """
        self.layer_idx = layer_idx
        self.on_roi_selected = on_roi_selected
        self.on_histogram_selected = on_histogram_selected
        self.on_segment_layer = on_segment_layer
        self.on_analysis_box = on_analysis_box
        self.no_init = True  # Used to configure first frame only once

        # Custom view box with per-plot context menu
        self.vb = CustomViewBox(parent_plot=self)
        self.plot_item = pg.PlotItem(viewBox=self.vb)

        # Image item (main display)
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        # Plot settings
        self.plot_item.invertY(True)        # Match image coordinate system
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.plot_item.setAspectLocked(True)

        # ROI mask overlay (semi-transparent, hidden by default)
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)
        self.mask_item.setVisible(False)
        self.plot_item.addItem(self.mask_item)
        self.mask_visible = False

        # Add layer label
        self.mask_text = pg.TextItem(f'Cells: 0', color=(255, 0, 0))
        self.plot_item.addItem(self.mask_text)
        self.mask_text.setAnchor((0, 1))  # bottom-left
        x_range, y_range = self.plot_item.viewRange()
        self.mask_text.setPos(x_range[0], y_range[0])
        self.mask_text.setVisible(True)  # hidden by default

        # Delay connecting mouse events to ensure the scene is available
        QtCore.QTimer.singleShot(0, self.connect_scene_click)

        # Add layer label
        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.plot_item.addItem(self.text)
        self.text.setPos(0, 0)

    # -------------------------
    # Context Menu Actions
    # -------------------------
    def set_mask_visible(self):
        """Toggle visibility of the ROI mask overlay."""
        self.mask_visible = not self.mask_visible
        self.mask_item.setVisible(self.mask_visible)
        self.mask_text.setVisible(self.mask_visible)

    def reset_zoom(self):
        """Reset zoom to show the full image."""
        self.plot_item.vb.autoRange()

    def request_segmentation(self):
        """Trigger segmentation callback for this layer."""
        if self.on_segment_layer:
            self.on_segment_layer(self.layer_idx)

    # -------------------------
    # Interaction Helpers
    # -------------------------
    def get_zoom_factor(self) -> float:
        """
        Calculate the zoom factor based on current view range and image size.

        Returns:
            float: Average zoom factor for X and Y axes.
        """
        img = self.image_item.image
        if img is None:
            return 1.0  # Default zoom if no image loaded

        img_height, img_width = img.shape[:2]
        x_range, y_range = self.plot_item.vb.viewRange()

        current_width = x_range[1] - x_range[0]
        current_height = y_range[1] - y_range[0]

        zoom_x = img_width / current_width if current_width != 0 else 1.0
        zoom_y = img_height / current_height if current_height != 0 else 1.0

        return (zoom_x + zoom_y) / 2  # Average factor

    def handle_mouse_click(self, event):
        """
        Handle mouse click events on the scene.

        - Double left click → histogram selection callback
        - Ctrl + left click → polygon ROI selection
        - Alt + left click → ellipse ROI selection
        """
        if event.button() != QtCore.Qt.LeftButton:
            return

        # Only react if the click occurred inside this plot
        if not self.plot_item.sceneBoundingRect().contains(event.scenePos()):
            return

        mouse_point = self.plot_item.vb.mapSceneToView(event.scenePos())
        y, x = int(mouse_point.x()), int(mouse_point.y())
        zoom_factor = self.get_zoom_factor()

        if event.double():
            # Double-click = histogram selection
            if self.on_histogram_selected:
                self.on_histogram_selected(layer_idx=self.layer_idx)
        else:
            # Modifier-based ROI selection
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier and self.on_roi_selected:
                self.on_roi_selected(layer_idx=self.layer_idx, x=x, y=y, roi_style="poly_line")

            elif modifiers == QtCore.Qt.AltModifier and self.on_roi_selected:
                self.on_roi_selected(layer_idx=self.layer_idx, x=x, y=y, roi_style="ellipse", zoom_factor=zoom_factor)

    def connect_scene_click(self):
        """Connect mouse click handler to the plot scene."""
        scene = self.plot_item.scene()
        if scene:
            scene.sigMouseClicked.connect(self.handle_mouse_click)
        else:
            print(f"[Layer {self.layer_idx}] Scene not ready yet.")

    def get_plot_item(self):
        """Return the underlying PlotItem for embedding in layouts."""
        return self.plot_item

    # -------------------------
    # Image & ROI Updates
    # -------------------------
    def update_frame(self, frame: np.ndarray):
        """
        Update the displayed image.

        Args:
            frame (np.ndarray): New image frame to display.
        """
        if self.no_init:
            # First frame: initialize intensity levels
            immin, immax = np.min(frame), np.max(frame)
            self.image_item.setImage(frame, autoLevels=False, levels=(immin, immax))
            self.no_init = False

        self.image_item.setImage(frame, autoLevels=False)

    def interactive_roi_selection(self, event):
        """
        Handle interactive ROI selection with Ctrl + Left click.

        Args:
            event: Mouse event from the scene.
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if event.button() == QtCore.Qt.LeftButton and modifiers == QtCore.Qt.ControlModifier:
            mouse_point = self.plot_item.vb.mapSceneToView(event.scenePos())
            y, x = int(mouse_point.x()), int(mouse_point.y())
            if self.on_roi_selected:
                self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style="poly_line")

    def add_roi_to_plot(self, roi):
        """Add a new ROI item to this plot's ViewBox."""
        self.plot_item.getViewBox().addItem(roi)




# class ROI:
#     """
#     Represents a Region of Interest (ROI) for a Syscon sequence file.
#
#     Attributes
#     ----------
#     mode : str
#         The ROI mode ('affine_slice' or 'polyline_points').
#     tracked : bool
#         Whether the ROI is tracked.
#     prep_laser : bool
#         Whether the laser should be prepared for this ROI.
#     layer_idx : int
#         The layer index of the ROI.
#     x_center : float
#         X-coordinate of the ROI center.
#     y_center : float
#         Y-coordinate of the ROI center.
#     z_center : float
#         Z-coordinate of the ROI center (layer).
#     params : any
#         Parameters required to define the ROI (slice parameters or polyline points).
#     pixel_coords : np.ndarray
#         Array of pixel coordinates covered by the ROI.
#     laser_intensity : float
#         Laser intensity for the ROI.
#     """
#
#     def __init__(self, mode: str = '', params=None, layer_idx: int = 0, roi_idx: int = 0):
#         self.mode = mode
#         self.tracked: bool = False
#         self.prep_laser: bool = True
#         self.layer_idx = layer_idx
#         self.roi_idx = roi_idx
#         self.x_center: float = 0.0
#         self.y_center: float = 0.0
#         self.z_center: float = 0.0
#         self.params = params
#         self.pixel_coords: np.ndarray = np.array([])
#         self.laser_intensity: float = 0.0
#         self.activity_pixels : np.ndarray = np.array([])
#
#     def calculate_center(self, image_frame: np.ndarray):
#         """
#         Calculate the (x, y) center of the ROI.
#
#         Parameters
#         ----------
#         image_frame : np.ndarray
#             The image frame used for generating ROI pixel coordinates.
#
#         Updates
#         -------
#         self.x_center, self.y_center, self.pixel_coords
#         """
#         if self.mode == 'affine_slice':
#             slice_params = self.params
#             coords = pg.affineSliceCoords(
#                 slice_params[0],
#                 slice_params[2],
#                 slice_params[1],
#                 (0, 1)
#             )
#             ys, xs = coords
#             self.pixel_coords = np.vstack((ys, xs)).T
#             self.x_center = np.mean(xs)
#             self.y_center = np.mean(ys)
#
#         elif self.mode == 'polyline_points':
#             points = np.array(self.params)
#             points_int = np.round(points).astype(np.int32)
#             contour = points_int.reshape((-1, 1, 2))
#             contour = contour[..., [1, 0]]
#
#             mask = np.zeros(image_frame.shape, dtype=np.uint8)
#             cv2.fillPoly(mask, [contour], color=1)
#
#             ys, xs = np.nonzero(mask)
#             if len(xs) == 0 or len(ys) == 0:
#                 self.x_center = None
#                 self.y_center = None
#                 self.pixel_coords = None
#             else:
#                 self.pixel_coords = np.vstack((ys, xs)).T
#                 self.x_center = np.mean(xs)
#                 self.y_center = np.mean(ys)
#
#     def calculate_activity(self, preprocessed_frame: np.ndarray) -> float:
#         """
#         Calculate the average activity of the ROI in a preprocessed image.
#
#         Parameters
#         ----------
#         preprocessed_frame : np.ndarray
#             Image array used to compute activity.
#
#         Returns
#         -------
#         float
#             Mean activity of pixels in the ROI (scaled by 1/1000).
#         """
#         if self.mode == 'affine_slice':
#             slice_params = self.params
#             _slice, coords = pg.affineSlice(
#                 preprocessed_frame,
#                 slice_params[0],
#                 slice_params[2],
#                 slice_params[1],
#                 (0, 1),
#                 returnCoords=True
#             )
#             self.pixel_coords = coords
#             self.activity_pixels = _slice.flatten()
#
#         elif self.mode == 'polyline_points':
#             points = np.array(self.params)
#             points_int = np.round(points).astype(np.int32)
#             contour = points_int.reshape((-1, 1, 2))
#             contour = contour[..., [1, 0]]
#
#             mask = np.zeros(preprocessed_frame.shape, dtype=np.uint8)
#             cv2.fillPoly(mask, [contour], color=1)
#
#             self.pixel_coords = mask
#             self.activity_pixels = preprocessed_frame[mask > 0]
#
#         else:
#             raise ValueError(f"Unknown mode: {self.mode}")
#
#         roi_activity = np.mean(self.activity_pixels)/1000 if len(self.activity_pixels) > 0 else 0
#         return roi_activity
#
#     def calculate_z(self):
#         """
#         Set the Z-coordinate (layer index) for the ROI.
#         """
#         self.z_center = self.layer_idx



class BaseROI:
    def __init__(self, layer_idx: int, roi_idx: int, reference_frame_shape: tuple[int, int] | None = None):
        self.layer_idx = layer_idx
        self.roi_idx = roi_idx
        self.reference_frame_shape = reference_frame_shape

        self.tracked: bool = False
        self.prep_laser: bool = True
        self.laser_intensity: float = 0.0

        # core ROI data
        self._pixel_mask: np.ndarray | None = None   # (H, W), bool
        self._pixel_coords: np.ndarray | None = None # (N, 2), int
        self._activity_pixels: np.ndarray = np.array([])
        self.scaling_factor: float = 1000

        # derived
        self._x_center: float = np.nan
        self._y_center: float = np.nan
        self._z_center: float = float(layer_idx)

        self.activity_measurement = "mean"

    # --- canonical interface ---

    @property
    def pixel_mask(self) -> np.ndarray:
        """Return boolean mask of ROI, compute if needed."""
        if self._pixel_mask is None:
            if self.reference_frame_shape is None:
                raise RuntimeError("reference_frame_shape required")
            self._pixel_mask = self._compute_mask().astype(bool)
        return self._pixel_mask

    @property
    def pixel_coords(self) -> np.ndarray:
        """Return canonical (N, 2) coords (y, x)."""
        if self._pixel_coords is None:
            ys, xs = np.nonzero(self.pixel_mask)
            self._pixel_coords = np.column_stack((ys, xs))
        return self._pixel_coords

    @property
    def x_center(self) -> float:
        if np.isnan(self._x_center):
            self._compute_center()
        return self._x_center

    @property
    def y_center(self) -> float:
        if np.isnan(self._y_center):
            self._compute_center()
        return self._y_center

    @property
    def z_center(self) -> float:
        return self._z_center

    @property
    def activity_pixels(self) -> np.ndarray:
        return self._activity_pixels

    #Setup for serialization
    def to_dict(self) -> dict:
        """Serialize ROI into a plain Python dict (safe across processes)."""
        return {
            "class": self.__class__.__name__,
            "layer_idx": self.layer_idx,
            "roi_idx": self.roi_idx,
            "reference_frame_shape": self.reference_frame_shape,
            "tracked": self.tracked,
            "prep_laser": self.prep_laser,
            "laser_intensity": self.laser_intensity,
            "scaling_factor": self.scaling_factor,
            "activity_measurement": self.activity_measurement,
            # Optional derived fields (you can drop if not needed)
            "x_center": self._x_center,
            "y_center": self._y_center,
            "z_center": self._z_center,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaseROI":
        """Rebuild an ROI from its serialized dict."""
        roi = cls(
            layer_idx=data["layer_idx"],
            roi_idx=data["roi_idx"],
            reference_frame_shape=data["reference_frame_shape"],
        )
        roi.tracked = data["tracked"]
        roi.prep_laser = data["prep_laser"]
        roi.laser_intensity = data["laser_intensity"]
        roi.scaling_factor = data["scaling_factor"]
        roi.activity_measurement = data["activity_measurement"]

        roi._x_center = data.get("x_center", np.nan)
        roi._y_center = data.get("y_center", np.nan)
        roi._z_center = data.get("z_center", float(data["layer_idx"]))
        return roi


    # --- calculations ---

    def calculate_activity(self, preprocessed_frame: np.ndarray) -> float:
        """Extracts and summarizes activity in ROI."""
        self._activity_pixels = preprocessed_frame[self.pixel_mask]
        if self._activity_pixels.size == 0:
            return 0.0
        if self.activity_measurement == "mean":
            return float(np.mean(self._activity_pixels) / self.scaling_factor)
        elif self.activity_measurement == "sum":
            return float(np.sum(self._activity_pixels) / self.scaling_factor)
        elif self.activity_measurement == "max":
            return float(np.max(self._activity_pixels) / self.scaling_factor)
        else:
            raise ValueError(f"Unknown activity_measurement: {self.activity_measurement}")

    def calculate_center(self):
        self._compute_center()

    def calculate_z(self):
        self._z_center = float(self.layer_idx)

    # --- subclass contract ---

    def _compute_mask(self) -> np.ndarray:
        """Subclasses must return a (H, W) mask for the ROI."""
        raise NotImplementedError

    def _compute_center(self):
        if self.pixel_coords.size > 0:
            self._y_center = float(np.mean(self.pixel_coords[:, 0]))
            self._x_center = float(np.mean(self.pixel_coords[:, 1]))
        else:
            print(f"self.pixel_coords is empty: {self.pixel_coords}")
            self._y_center = self._x_center = np.nan

class GeneralEllipseROI(BaseROI):
    def __init__(self, params, layer_idx, roi_idx, reference_frame_shape,
                 use_slice_for_activity: bool = False,
                 use_slice_for_center: bool = False):
        self.slice_params = params
        self.use_slice_for_activity = use_slice_for_activity
        self.use_slice_for_center = use_slice_for_center
        super().__init__(layer_idx, roi_idx, reference_frame_shape)

    # ---- activity ----
    def calculate_activity(self, preprocessed_frame: np.ndarray) -> float:
        if self.use_slice_for_activity:
            return self.calculate_activity_from_slice(preprocessed_frame)
        else:
            return super().calculate_activity(preprocessed_frame)

    def calculate_activity_from_slice(self, preprocessed_frame: np.ndarray) -> float:
        slice_params = self.slice_params
        _slice, coords = pg.affineSlice(
            preprocessed_frame,
            slice_params[0],
            slice_params[2],
            slice_params[1],
            (0, 1),
            returnCoords=True
        )
        self._activity_pixels = _slice.flatten()
        if self._activity_pixels.size == 0:
            return 0.0

        if self.activity_measurement == "mean":
            return float(np.mean(self._activity_pixels) / self.scaling_factor)
        elif self.activity_measurement == "sum":
            return float(np.sum(self._activity_pixels) / self.scaling_factor)
        elif self.activity_measurement == "max":
            return float(np.max(self._activity_pixels) / self.scaling_factor)
        else:
            raise ValueError(f"Unknown activity_measurement: {self.activity_measurement}")

    # ---- center ----
    def calculate_center(self):
        if self.use_slice_for_center:
            self._compute_center_from_slice()
        else:
            super().calculate_center()

    def _compute_center_from_slice(self):
        coords = pg.affineSliceCoords(
            self.slice_params[0],
            self.slice_params[2],
            self.slice_params[1],
            (0, 1)
        )
        ys, xs = coords
        ys = ys.ravel()
        xs = xs.ravel()
        if ys.size == 0 or xs.size == 0:
            self._y_center = self._x_center = np.nan
        else:
            self._y_center = float(np.mean(ys))
            self._x_center = float(np.mean(xs))

    # ---- mask ----
    def _compute_mask(self) -> np.ndarray:
        mask = np.zeros(self.reference_frame_shape, dtype=bool)
        coords = pg.affineSliceCoords(
            self.slice_params[0],
            self.slice_params[2],
            self.slice_params[1],
            (0, 1)
        )
        ys, xs = coords
        ys = np.round(ys).astype(int).ravel()
        xs = np.round(xs).astype(int).ravel()

        # clip to frame #TODO: Here there might be an indixing error (by one pixel) because at max values you get a nan
        in_bounds = (
            (ys >= 0) & (ys < self.reference_frame_shape[0]) &
            (xs >= 0) & (xs < self.reference_frame_shape[1])
        )
        mask[ys[in_bounds], xs[in_bounds]] = True
        return mask

    #Addon for serialization
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "slice_params": self.slice_params,
            "use_slice_for_activity": self.use_slice_for_activity,
            "use_slice_for_center": self.use_slice_for_center,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GeneralEllipseROI":
        roi = cls(
            params=data["slice_params"],
            layer_idx=data["layer_idx"],
            roi_idx=data["roi_idx"],
            reference_frame_shape=data["reference_frame_shape"],
            use_slice_for_activity=data["use_slice_for_activity"],
            use_slice_for_center=data["use_slice_for_center"],
        )
        # fill common fields
        roi.tracked = data["tracked"]
        roi.prep_laser = data["prep_laser"]
        roi.laser_intensity = data["laser_intensity"]
        roi.scaling_factor = data["scaling_factor"]
        roi.activity_measurement = data["activity_measurement"]
        return roi


class GeneralPolylineROI(BaseROI):
    def __init__(self, params, layer_idx, roi_idx, reference_frame_shape):
        self.points = np.array(params)
        super().__init__(layer_idx, roi_idx, reference_frame_shape)

    def _compute_mask(self) -> np.ndarray:
        mask = np.zeros(self.reference_frame_shape, dtype=np.uint8)
        contour = np.round(self.points).astype(np.int32).reshape((-1, 1, 2))
        contour = contour[..., [1, 0]]  # xy -> row,col
        cv2.fillPoly(mask, [contour], color=1)
        return mask.astype(bool)


    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "points": self.points.tolist(),
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GeneralPolylineROI":
        roi = cls(
            params=data["points"],
            layer_idx=data["layer_idx"],
            roi_idx=data["roi_idx"],
            reference_frame_shape=data["reference_frame_shape"]
        )
        roi.tracked = data.get("tracked", False)
        roi.prep_laser = data.get("prep_laser", True)
        roi.laser_intensity = data.get("laser_intensity", 0.0)
        roi.scaling_factor = data.get("scaling_factor", 1000)
        roi.activity_measurement = data.get("activity_measurement", "mean")
        return roi







class EllipseRoi(pg.EllipseROI):
    """
    A labeled elliptical ROI (Region of Interest) bound to a specific layer.

    Extends pyqtgraph's EllipseROI with:
    - Automatic labeling
    - Update callbacks
    - Threshold tracking
    - Show/hide support
    """

    def __init__(
        self,
        layer_idx: int,
        idx: int,
        image_plot: ImagePlot,
        update_callback: Callable,
        delete_callback: Callable,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot
        self.maxBounds = self.image_plot.image_item.boundingRect()
        self.update_callback = update_callback
        self.delete_callback = delete_callback

        # ROI styling
        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))

        # Add label to the plot
        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.label.setAnchor((0, 1))  # Attach label to top-center of ellipse
        self.image_plot.plot_item.addItem(self.label)
        self.label_visible = True

        # Delete button (✕)
        self.delete_btn = pg.TextItem("✕", color=get_roi_color(self.idx), anchor=(0, 1))
        self.delete_btn.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.image_plot.plot_item.addItem(self.delete_btn)
        self.delete_btn.mouseClickEvent = self._on_delete_clicked

        # Event connections
        self.sigRegionChangeFinished.connect(self._notify_parent)
        self.sigRegionChanged.connect(self._update_label_position)

        # Place label initially
        self._update_label_position()

    # -------------------------
    # Internal helpers
    # -------------------------
    def _notify_parent(self):
        """Invoke the central callback when ROI editing is finished."""
        if self.update_callback:
            self.update_callback(self)#, self.layer_idx, self.image_plot)

    def _update_label_position(self):
        """Reposition the label to match the top center of the ellipse."""
        pos = self.pos()
        size = self.size()
        center_x = pos.x() + size.x() / 2
        center_y = pos.y()
        self.label.setPos(center_x + 2, center_y)
        self.delete_btn.setPos(center_x - 2, center_y)
    # -------------------------
    # Public API
    # -------------------------
    def set_visible(self):
        """Show ROI and its label."""
        self.label.setVisible(True)
        self.setVisible(True)

    def set_invisible(self):
        """Hide ROI and its label."""
        self.label.setVisible(False)
        self.setVisible(False)

    def _on_delete_clicked(self, ev):
        if self.delete_callback:
            self.delete_callback(self.layer_idx, self.idx)
        ev.accept()

    # def position_changed(self, roi: "EllipseRoi"):
    #     """Update label position when ROI is moved."""
    #     self.label.setPos(roi.pos())
    #     self.delete_btn.setPos(roi.pos())

    def update_threshold(self, value: int):
        """Update threshold for this ROI in the tracker routine."""
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value


# TODO: Make not movable after doubleclick,
# make second click removable
class PolyLineRoi(pg.PolyLineROI):
    """
    A labeled polyline ROI bound to a specific layer.

    Extends pyqtgraph's PolyLineROI with:
    - Automatic labeling at centroid
    - Interaction lock (non-editable polygon)
    - Threshold tracking
    - Show/hide support
    """

    def __init__(
        self,
        layer_idx: int,
        idx: int,
        image_plot: ImagePlot,
        points: list,
        delete_callback: Callable,
        closed: bool = True,
        **kwargs
    ):
        super().__init__(points, closed=closed, **kwargs)

        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot
        self.maxBounds = self.image_plot.image_item.boundingRect()
        self.delete_callback = delete_callback

        # ROI styling
        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))

        # Delete button (✕)
        # self.delete_btn = pg.TextItem("x", color=get_roi_color(self.idx), anchor=(0, 1))
        # self.delete_btn.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        # self.image_plot.plot_item.addItem(self.delete_btn)
        # self.delete_btn.mouseClickEvent = self._on_delete_clicked

        # Add label at centroid
        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.image_plot.plot_item.addItem(self.label)
        self.set_label_center()
        self.label_visible = True



        # Disable handle interactions → polygon is fixed, non-editable
        for handle_dict in self.handles:
            handle = handle_dict['item']
            handle.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
            handle.isMoving = False
            handle.mouseClickEvent = lambda ev: ev.ignore()
            handle.mouseDragEvent = lambda ev: ev.ignore()
            handle.movePoint = lambda pos, modifiers=None, finish=True: None

        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        if hasattr(self, 'setMovable'):
            self.setMovable(False)

    # -------------------------
    # Overridden mouse events
    # -------------------------
    def mouseClickEvent(self, ev):
        ev.ignore()

    def mouseDragEvent(self, ev):
        ev.ignore()

    # -------------------------
    # Public API
    # -------------------------
    def set_visible(self):
        """Show ROI and (optionally) its label."""
        self.setVisible(True)
        if self.label_visible:
            self.label.setVisible(True)

    # def _on_delete_clicked(self, ev):
    #     if self.delete_callback:
    #         self.delete_callback(self.layer_idx, self.idx)
    #     ev.accept()

    def set_label_center(self):
        """Recalculate centroid of polygon and reposition label."""
        pts = self.getState()['points']
        if not pts:
            return
        x_coords, y_coords = zip(*pts)
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        self.label.setPos(centroid_x + 2, centroid_y)

    def update_threshold(self, value: int):
        """Update threshold for this ROI in the tracker routine."""
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value


# TODO: Make so every polyline ROI inside is selected automatically and labled as polyline ROI
# TODO:
class Analysis_Box(pg.RectROI):
    def __init__(
        self,
        layer_idx: int,
        box_idx: int,
        image_plot,
        update_callback,
        delete_callback,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.layer_idx = layer_idx
        self.idx = box_idx
        self.image_plot = image_plot
        self.maxBounds = self.image_plot.image_item.boundingRect()
        self.update_callback = update_callback
        self.delete_callback = delete_callback

        # ROI styling
        self.setPen(pg.mkPen(color="red", width=2))

        # Label
        self.label = pg.TextItem(f"ROI_selection", color="red", anchor=(0, 1))
        self.image_plot.plot_item.addItem(self.label)

        # Delete button (✕)
        self.delete_btn = pg.TextItem("✕", color="red", anchor=(0, 1))
        self.delete_btn.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.image_plot.plot_item.addItem(self.delete_btn)
        self.delete_btn.mouseClickEvent = self._on_delete_clicked

        # Event connections
        self.sigRegionChangeFinished.connect(self._notify_parent)
        self.sigRegionChanged.connect(self._update_label_position)

        self._update_label_position()


    # -------------------------
    # Internal helpers
    # -------------------------
    def _notify_parent(self):
        if self.update_callback:
            self.update_callback(self, self.layer_idx, self.idx, self.image_plot)

    def _update_label_position(self):
        pos = self.pos()
        size = self.size()
        center_x = pos.x() + size.x() / 2
        center_y = pos.y()

        # Label at top-center
        self.label.setPos(center_x, center_y)

        # ✕ button just to the right
        self.delete_btn.setPos(pos)

    def _on_delete_clicked(self, ev):
        """Trigger central deletion when ✕ is clicked."""
        if self.delete_callback:
            # Tell parent "please delete this Analysis_Box"
            self.delete_callback(self, self.layer_idx, self.idx, self.image_plot)
        ev.accept()


    # -------------------------
    # Public API
    # -------------------------
    def set_visible(self):
        self.label.setVisible(True)
        self.delete_btn.setVisible(True)
        self.setVisible(True)

    def set_invisible(self):
        self.label.setVisible(False)
        self.delete_btn.setVisible(False)
        self.setVisible(False)

    def position_changed(self, box: "Analysis_Box"):
        self.label.setPos(box.pos())
        self.delete_btn.setPos(box.pos().x() + 20, box.pos().y())




