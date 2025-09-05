from __future__ import annotations
from typing import List, Dict, Union, Callable

import matplotlib as mpl
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore
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
from vxpy.extras.sys_con import SysConRoutine, ROI
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
    layer_max_num: int = 20                                  # Max number of layers to track

    # -------------------- Runtime / Trigger --------------------
    trigger: vxevent.NewDataTrigger = None                     # Trigger for new incoming data
    current_layer_num: int = -1                                # Index of currently processed layer
    new_metadata: bool = False                                 # Flag: indicating new metadata is available
    attrs_written_to_file: List[str] = []                      # List of attributes already written to Attribute writer class

    # -------------------- ROI Settings --------------------
    roi_max_num: int = 5                                    # Max number of ROIs that can be tracked across all layers
    roi_slice_params: Dict[tuple, ROI] = {}                 # Stores ROI class instance (layer_idx, roi_idx) -> ROI
    roi_thresholds: Dict[tuple, int] = {}                   # Threshold value for triggers per ROI
    initial_roi_trigger_threshold = 2                       # Initial trigger threshold value # TODO: what should this be ?

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



    #Experimental!
    # -------------------- Evaluation / Polyline ROI Tracking --------------------
    eval_active: bool = False                                 # Flag: Whether evaluation mode is active
    latest_measurements: Dict = {}                             # Stores latest measurements
    eval_n_frames: int = 10                                   # Number of frames to average
    eval_measurement_type: str = "mean"                       # How measurements are aggregated
    eval_min_pixels: int = 7                                   # Minimum pixels per ROI for evaluation
    eval_layer_indices = None                                  # Layers to evaluate, if subset


    def __init__(self, *args, **kwargs):
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
        self.layer_masks: Dict[int, np.ndarray] = {}

        # Runtime flags / counters
        self.current_auto_segment: bool = False  # Flag: Whether auto segmentation is active (prohibits new segmentations while already running)
        self.expected_run_results: int = 0       # How many segmentation results (layers) are expected
        self.current_run_results: int = 0        # Number of segmentation results received
        self.is_pool_closed: bool = True         # Flag: Whether the multiprocessing pool is closed


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
                # Initialize ROI slice container and threshold
                self.roi_slice_params[(layer_idx, roi_idx)] = ROI()
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
        pass


    def _process_frame(self, last_idx, last_time, last_frame):
        """
        Process the last acquired input frame, update ROI activity, and handle evaluation.

        Args:
            last_idx (int): Index of the last received frame.
            last_time (float): Timestamp of the last received frame.
            last_frame (np.ndarray): Raw frame data from the acquisition.
        """
        # Get current layer number from the ScanImageFrame server
        layer_num = ScanImageFrameReceiverTcpServer.instance().layer_num

        # If layer has changed, reset ROI metadata
        if self.current_layer_num != layer_num:
            self.new_metadata = True
            self.current_layer_num = layer_num

            # Reset all ROI slices for all layers and ROIs
            for idx in self.roi_slice_params.keys():
                self.roi_slice_params[idx] = ROI()

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
            if layer_idx != current_layer_idx or roi.params is None:
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

        # -------------------- Experimental Evaluation --------------------
        if self.eval_active:
            # Determine which layers to evaluate
            layers_to_use = self.eval_layer_indices
            if layers_to_use == "all" or layers_to_use is None:
                layers_to_use = list(self.layer_masks.keys())

            # Compute evaluation measurements for selected layers
            self.latest_measurements = self.calculate_measurements(
                layer_indices=layers_to_use,
                n_frames=self.eval_n_frames,
                measurement_type=self.eval_measurement_type,
                min_pixels=self.eval_min_pixels,
            )


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
            device_id = i % num_gpus
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
        while self.current_auto_segment and self.segmentation_queue and not self.segmentation_queue.empty():
            msg = self.segmentation_queue.get()

            if msg[0] == 'result':
                _, layer_idx, merged_mask, contour_mask = msg
                # Store segmentation result as labled masks
                self.layer_masks[layer_idx] = {
                    'merged_mask': merged_mask,
                    'contour_mask': contour_mask,}

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



    #Experimental:
    def calculate_measurements(self, layer_indices, n_frames, measurement_type="mean", min_pixels=10):
        """
        Calculate measurements for ROIs from segmentation masks.

        Parameters
        ----------
        layer_indices : list[int]
            Which layer indices to process.
        n_frames : int
            Number of last frames to include in the calculation.
        measurement_type : str
            One of ["mean", "std", "median", "sum", "df/dt"].
        min_pixels : int
            Minimum number of pixels required in an ROI to be processed.

        Returns
        -------
        dict
            {
                (layer_idx, label_id): {
                    "trace": np.ndarray,   # 1D time series
                    "coords": list[(y, x)],# pixel coordinates of ROI
                    "n_pixels": int
                },
                ...
            }
        """
        results = {}

        for layer_idx in layer_indices:
            # Check if segmentation exists for this layer
            if layer_idx not in self.layer_masks or "merged_mask" not in self.layer_masks[layer_idx]:
                print(f"[calculate_measurements] No mask for layer {layer_idx}, skipping.")
                continue

            mask = self.layer_masks[layer_idx]["merged_mask"]

            # Read the last n_frames for this layer
            _, _, frames = vxattribute.read_attribute(f"{self.output_frame_name}_{layer_idx}", last=n_frames)
            if frames is None or len(frames) == 0:
                print(f"[calculate_measurements] No frames available for layer {layer_idx}, skipping.")
                continue

            # Ensure float for calculations
            frames = frames.astype(np.float64)

            for label_id in np.unique(mask):
                if label_id == 0:
                    continue  # skip background

                # Pixel coordinates for this ROI
                ys, xs = np.where(mask == label_id)
                pixel_count = len(ys)
                if pixel_count < min_pixels:
                    continue  # skip small ROIs

                # Extract ROI trace: shape (n_frames, n_pixels) -> mean over pixels
                roi_values = frames[:, ys, xs]  # broadcasting: each frame index with all ROI coords
                if measurement_type == "mean":
                    trace = np.mean(roi_values, axis=1)
                elif measurement_type == "std":
                    trace = np.std(roi_values, axis=1)
                elif measurement_type == "median":
                    trace = np.median(roi_values, axis=1)
                elif measurement_type == "sum":
                    trace = np.sum(roi_values, axis=1)
                elif measurement_type == "df/dt":
                    # Compute relative change per frame
                    mean_trace = np.mean(roi_values, axis=1)
                    baseline = np.percentile(mean_trace, 10)  # 10th percentile as baseline
                    trace = (mean_trace - baseline) / (baseline + 1e-9)
                else:
                    raise ValueError(f"Unsupported measurement_type '{measurement_type}'")

                results[(layer_idx, int(label_id))] = {
                    "trace": trace,
                    "coords": list(zip(ys, xs)),
                    "n_pixels": pixel_count
                }
        print(f"[calculate_measurements] Computed {len(results)} ROI traces")

        return results


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
        self.eval_button = QtWidgets.QPushButton('Get Evaluation')
        self.eval_button.clicked.connect(self.get_evaluation)
        button_layout.addWidget(self.eval_button)
        ###

        self.selected_histogram_layer = None
        self.plot_highlight_rect = None

        self.open_window_btn = QtWidgets.QPushButton('Export to SysCon')
        self.open_window_btn.clicked.connect(self.to_holo)
        button_layout.addWidget(self.open_window_btn)

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

    def update_segmentation_params_visibility(self):
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

    def reset_display_settings_to_defaults(self):
        """
        Reset display-related settings (measurement type, averaging window, thresholds)
        back to their default values.
        """
        self.measurement_selector.setCurrentText("mean")
        self.frame_avg_spin.setValue(10)
        self.pixel_threshold.set_value(10)

    def reset_segment_settings_to_defaults(self):
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

    def update_frame(self):
        """
        Pull frames from the routine and update plots, histograms, and UI state.
        Also syncs widget values back to the routine instance.
        """
        routine = NextGenTrackerRoutine.instance()
        layer_num = routine.current_layer_num

        # Ensure segmentation results are checked/updated
        routine.check_segmentation_result()

        # Update progress bar if available
        if hasattr(routine, "current_progress"):
            self.progress_bar.setValue(int(routine.current_progress))

        # Rebuild plots if metadata changed or layer count changed
        if routine.new_metadata or (layer_num != self.current_num_layers):
            self._rebuild_image_plots(layer_num)
            routine.new_metadata = False

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


    def _rebuild_image_plots(self, num_layers: int):
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

    def select_histogram(self, layer_idx: int):
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

    def _highlight_plot_item(self, plot_item):
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

    def _remove_plot_highlight(self):
        """
        Remove any active highlight rectangle from the plots.
        """
        if getattr(self, "plot_highlight_rect", None):
            self.img_plot_widget.scene().removeItem(self.plot_highlight_rect)
            self.plot_highlight_rect = None

    def handle_roi_click(self, layer: int, x: int, y: int, roi_style: str, zoom_factor=None):
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
        mask_data = routine.layer_masks.get(layer, {}).get("merged_mask")

        # Direct ellipse ROI (doesn't require a mask)
        if roi_style == "ellipse":
            self.add_roi(
                layer_idx=layer,
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
                    layer_idx=layer,
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
    ):
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
            )
            image_plot.add_roi_to_plot(roi)
            self.roi_updated(roi, layer_idx, image_plot)

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

    def delete_specific_roi(self, layer_idx: int, roi_idx: int):
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

    def toggle_mask(self, only_contours: bool = True):
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

    def roi_updated(self, roi: Union[EllipseRoi, PolyLineRoi], layer_idx: int, image_plot: ImagePlot):
        """
        Register and update ROI in the routine when it changes parameters.

        Args:
            roi (EllipseRoi | PolyLineRoi): The updated ROI object.
            layer_idx (int): Index of the image layer the ROI belongs to.
            image_plot (ImagePlot): Plot containing the ROI.
        """
        log.debug(f"Update ROI for layer {layer_idx}, ROI idx {roi.idx}")

        if isinstance(roi, PolyLineRoi):
            # Polyline ROI stores its points directly
            points = roi.getState()["points"]
            roi_instance = ROI(mode="polyline_points", params=points, layer_idx=layer_idx)

        elif isinstance(roi, EllipseRoi):
            # Ellipse ROI requires affine slice params
            slice_params = roi.getAffineSliceParams(
                image_plot.image_item.image, image_plot.image_item
            )
            roi_instance = ROI(mode="affine_slice", params=slice_params, layer_idx=layer_idx)

        else:
            raise ValueError(f"Invalid ROI type: {type(roi)}")

        # Compute ROI metadata
        frame_height = ScanImageFrameReceiverTcpServer.instance().frame_height
        frame_width = ScanImageFrameReceiverTcpServer.instance().frame_width
        roi_instance.calculate_center(image_frame=np.zeros((frame_height, frame_width)))
        roi_instance.calculate_z()
        roi_instance.tracked = True

        # Register ROI in the routine
        NextGenTrackerRoutine.instance().roi_slice_params[(layer_idx, roi.idx)] = roi_instance

    def get_next_free_roi_index(self):
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

    def update_button_state(self):
        """Enable or disable automated segmentation button based on ongoing segmentations."""
        routine = NextGenTrackerRoutine.instance()
        self.add_auto_btn.setEnabled(not routine.current_auto_segment)

    def automated_roi_search(self, layer_idx: int | None = None):
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

            routine.button_start_segmentation_clicked(layer_id=layer_idx)
        else:
            print("Automated ROI search already running.")

    def to_holo(self):
        """
        Export current ROIs to SysConRoutine for downstream processing.
        Used to hand off ROIs for stimulation control.
        """
        syscon = SysConRoutine.instance()
        syscon.num_layers = self.current_num_layers
        syscon.rois_to_stimulate.clear()
        syscon.rois_to_stimulate.update(NextGenTrackerRoutine.instance().roi_slice_params)
        syscon.new_rois_set = True



    def get_evaluation(self):
        """
        Open or close the ROI evaluation window.
        Allows manual inspection and correction of ROIs.
        """
        routine = NextGenTrackerRoutine.instance()

        if not getattr(routine, "layer_masks", None) or len(routine.layer_masks) == 0:
            QtWidgets.QMessageBox.warning(
                self, "No ROI Data", "No segmentation masks available for evaluation."
            )
            return

        # Toggle evaluation window
        if hasattr(self, "_eval_window") and self._eval_window.isVisible():
            routine.eval_active = False
            self._eval_window.close()
            del self._eval_window
        else:
            routine.eval_active = True
            self._eval_window = EvalWindow(
                tracker_routine=routine,
                add_roi_callback=self.add_roi,
            )
            self._eval_window.show()

    @staticmethod
    def update_pixel_threshold(value: int):
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

class EvalWindow(QtWidgets.QWidget):
    def __init__(self, tracker_routine, add_roi_callback, parent=None):
        super().__init__(parent)
        self.tracker_routine = tracker_routine
        self.add_roi_callback = add_roi_callback

        self.setWindowTitle("Cell Measurements")
        self.resize(1200, 800)

        main_layout = QtWidgets.QHBoxLayout(self)

        # Left panel - controls
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_widget)

        # Measurement type dropdown
        self.measurement_box = QtWidgets.QComboBox()
        self.measurement_box.addItems(["mean", "std", "median", "sum", "df/dt"])
        control_layout.addWidget(QtWidgets.QLabel("Measurement Type:"))
        control_layout.addWidget(self.measurement_box)

        # Frames spinbox
        self.frames_spin = QtWidgets.QSpinBox()
        self.frames_spin.setRange(1, 10000)
        self.frames_spin.setValue(100)
        control_layout.addWidget(QtWidgets.QLabel("Number of frames:"))
        control_layout.addWidget(self.frames_spin)

        # Min pixels spinbox
        self.min_pixels_spin = QtWidgets.QSpinBox()
        self.min_pixels_spin.setRange(1, 100000)
        self.min_pixels_spin.setValue(20)
        control_layout.addWidget(QtWidgets.QLabel("Min pixels per ROI:"))
        control_layout.addWidget(self.min_pixels_spin)

        # Layer selection with "All" option
        self.layer_list = QtWidgets.QListWidget()
        self.layer_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        # Add "All" option (checkable)
        all_item = QtWidgets.QListWidgetItem("All")
        all_item.setFlags(all_item.flags() | QtCore.Qt.ItemIsUserCheckable)
        all_item.setCheckState(QtCore.Qt.Checked)  # default to checked for convenience
        self.layer_list.addItem(all_item)

        # Add layers as checkable items
        for layer_idx in sorted(self.tracker_routine.layer_masks.keys()):
            item = QtWidgets.QListWidgetItem(str(layer_idx))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)  # default checked
            self.layer_list.addItem(item)

        control_layout.addWidget(QtWidgets.QLabel("Select Layers:"))
        control_layout.addWidget(self.layer_list)

        control_layout.addStretch()
        main_layout.addWidget(control_widget, 0)

        # Right panel - matplotlib canvas
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.mpl_connect("pick_event", self.on_pick)
        main_layout.addWidget(self.canvas, 1)

        self.results = {}

        # Connect controls to update routine params
        self.measurement_box.currentIndexChanged.connect(self.update_routine_params)
        self.frames_spin.valueChanged.connect(self.update_routine_params)
        self.min_pixels_spin.valueChanged.connect(self.update_routine_params)
        self.layer_list.itemChanged.connect(self.on_layer_item_changed)

        # Initialize routine params and activate evaluation mode
        self.update_routine_params()

        self.accumulated_traces = {}  # store full ongoing traces for each ROI
        self.last_trace_lengths = {}  # track last length of trace stored for each ROI

        # timer for live updates, every 500 ms
        self.plot_timer = QtCore.QTimer(self)
        self.plot_timer.timeout.connect(self.update_accumulated_traces_and_plot)
        self.plot_timer.start(500)

    def update_accumulated_traces_and_plot(self):
        new_measurements = self.tracker_routine.latest_measurements
        measurement = self.tracker_routine.eval_measurement_type

        print(f"measurements {new_measurements}")
        # Append new data points for each ROI
        for roi_key, data in new_measurements.items():
            new_trace = data["trace"]

            if roi_key not in self.accumulated_traces:
                # first time seeing this ROI: initialize
                self.accumulated_traces[roi_key] = list(new_trace)
                self.last_trace_lengths[roi_key] = len(new_trace)
            else:
                old_len = self.last_trace_lengths[roi_key]
                # new_trace length might be equal or smaller (rolling window), append only new points
                if len(new_trace) > old_len:
                    append_vals = new_trace[old_len:]
                    self.accumulated_traces[roi_key].extend(append_vals)
                    self.last_trace_lengths[roi_key] = len(new_trace)
                else:
                    # Rolling window scenario, assume new_trace is a sliding window of length n_frames
                    # To handle this, overwrite the last n points in accumulated trace:
                    n = len(new_trace)
                    self.accumulated_traces[roi_key][-n:] = new_trace
                    self.last_trace_lengths[roi_key] = n

        # Now plot all accumulated traces
        self.ax.clear()
        for roi_key, trace_list in self.accumulated_traces.items():
            self.ax.plot(trace_list, picker=5)

        self.ax.set_title(f"Live traces ({measurement})")
        self.ax.set_xlabel("Frame (cumulative)")
        self.ax.set_ylabel(measurement)

        # Optionally expand x-axis to fit all points
        max_len = max(len(t) for t in self.accumulated_traces.values()) if self.accumulated_traces else 100
        self.ax.set_xlim(0, max_len)

        self.canvas.draw()


    def on_layer_item_changed(self, item):
        if item.text() == "All":
            # When "All" toggled, select/deselect all layers accordingly
            check_state = item.checkState()
            for i in range(1, self.layer_list.count()):
                layer_item = self.layer_list.item(i)
                layer_item.setCheckState(check_state)
        else:
            # Update "All" checkbox based on other layers
            all_checked = True
            for i in range(1, self.layer_list.count()):
                if self.layer_list.item(i).checkState() != QtCore.Qt.Checked:
                    all_checked = False
                    break
            all_item = self.layer_list.item(0)
            all_item.setCheckState(QtCore.Qt.Checked if all_checked else QtCore.Qt.Unchecked)

        self.update_routine_params()

    def update_routine_params(self):
        # Update routine parameters from GUI controls
        self.tracker_routine.eval_measurement_type = self.measurement_box.currentText()
        self.tracker_routine.eval_n_frames = self.frames_spin.value()
        self.tracker_routine.eval_min_pixels = self.min_pixels_spin.value()

        all_checked = self.layer_list.item(0).checkState() == QtCore.Qt.Checked
        if all_checked:
            self.tracker_routine.eval_layer_indices = "all"
        else:
            selected_layers = []
            for i in range(1, self.layer_list.count()):
                item = self.layer_list.item(i)
                if item.checkState() == QtCore.Qt.Checked:
                    try:
                        selected_layers.append(int(item.text()))
                    except ValueError:
                        pass
            self.tracker_routine.eval_layer_indices = selected_layers if selected_layers else []

        # Activate eval mode so routine does calculation on incoming frames
        self.tracker_routine.eval_active = True

    def calculate_and_plot(self):
        # Read the latest measurements calculated by the routine

        self.results = self.tracker_routine.latest_measurements
        self.ax.clear()

        if not self.results:
            self.ax.set_title("No measurement data available")
            self.canvas.draw()
            return

        measurement = self.tracker_routine.eval_measurement_type
        for (layer_idx, label_id), data in self.results.items():
            line, = self.ax.plot(data["trace"], picker=5)
            line._roi_key = (layer_idx, label_id)

        self.ax.set_title(f"Traces ({measurement})")
        self.ax.set_xlabel("Frame")
        self.ax.set_ylabel(measurement)
        self.canvas.draw()

    def on_pick(self, event):
        # Handle user clicking a trace
        line = event.artist
        if hasattr(line, "_roi_key"):
            roi_key = line._roi_key
            coords = self.results.get(roi_key, {}).get("coords", None)
            if coords is not None:
                self.add_roi_callback(coords)
                QtWidgets.QMessageBox.information(
                    self,
                    "ROI Added",
                    f"Added ROI from layer {roi_key[0]}, label {roi_key[1]}"
                )


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

        # Show menu and get selected action
        action = menu.exec(ev.screenPos().toPoint())

        # --- Handle actions ---
        # ROI actions
        if action == poly_action and self.parent_plot.on_roi_selected:
            self.parent_plot.on_roi_selected(
                layer=self.parent_plot.layer_idx,
                x=x,
                y=y,
                roi_style="poly_line",
                zoom_factor=zoom_factor,
            )

        elif action == ellipse_action and self.parent_plot.on_roi_selected:
            self.parent_plot.on_roi_selected(
                layer=self.parent_plot.layer_idx,
                x=x,
                y=y,
                roi_style="ellipse",
                zoom_factor=zoom_factor,
            )

        # Other plot actions
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

    def __init__(self, layer_idx, on_roi_selected=None, on_histogram_selected=None, on_segment_layer=None):
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
                self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style="poly_line")

            elif modifiers == QtCore.Qt.AltModifier and self.on_roi_selected:
                self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style="ellipse", zoom_factor=zoom_factor)

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
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot
        self.maxBounds = self.image_plot.image_item.boundingRect()
        self.update_callback = update_callback

        # ROI styling
        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))

        # Add label to the plot
        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.label.setAnchor((0, 1))  # Attach label to top-center of ellipse
        self.image_plot.plot_item.addItem(self.label)
        self.label_visible = True

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
            self.update_callback(self, self.layer_idx, self.image_plot)

    def _update_label_position(self):
        """Reposition the label to match the top center of the ellipse."""
        pos = self.pos()
        size = self.size()
        center_x = pos.x() + size.x() / 2
        center_y = pos.y()
        self.label.setPos(center_x, center_y)

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

    def position_changed(self, roi: "EllipseRoi"):
        """Update label position when ROI is moved."""
        self.label.setPos(roi.pos())

    def update_threshold(self, value: int):
        """Update threshold for this ROI in the tracker routine."""
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value


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
        closed: bool = True,
        **kwargs
    ):
        super().__init__(points, closed=closed, **kwargs)

        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot
        self.maxBounds = self.image_plot.image_item.boundingRect()

        # ROI styling
        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))

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

    def set_label_center(self):
        """Recalculate centroid of polygon and reposition label."""
        pts = self.getState()['points']
        if not pts:
            return
        x_coords, y_coords = zip(*pts)
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        self.label.setPos(centroid_x, centroid_y)

    def update_threshold(self, value: int):
        """Update threshold for this ROI in the tracker routine."""
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value



