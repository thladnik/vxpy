from __future__ import annotations
from typing import List, Dict, Union, Callable

import matplotlib as mpl
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore
#TODO: dependencies need an upgrade for cellpose (problem if vxpy is installed prior to cellpose --> cellpose dependency clash... solution install cellpose first)
from cellpose.models import CellposeModel
from multiprocessing import Process, Queue
import multiprocessing as mp
from skimage.measure import regionprops
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

log = vxlogger.getLogger(__name__)


def get_roi_color(index: int):
    return (255 * np.array(mpl.colormaps['tab10'](index)[:3])).astype(np.uint8)


# def run_detect_rois(pretrained_model_path, diameter, cellprob_threshold, flow_threshold, mproj, layer_idx, strategy, queue):
#
#     print(f"Running Cellpose on layer {layer_idx}, shape: {mproj.shape}")
#     model = CellposeModel(gpu=True, pretrained_model=pretrained_model_path)
#
#     masks, flows, _ = model.eval(
#         mproj,
#         channels=[0, 0],
#         diameter=diameter,
#         cellprob_threshold=cellprob_threshold,
#         flow_threshold=flow_threshold,
#     )
#
#     # # Normalize structure
#     # if isinstance(masks, np.ndarray):
#     #     mask_list = [masks]
#     #     prob_list = [flows[2]]
#     # else:
#     #     mask_list = masks
#     #     prob_list = [f[2] for f in flows]
#
#     # TODO: maybe implement this for temporal handling but not needed for 2d case
#     # merged_mask = NextGenTrackerRoutine.merge_masks_with_strategy(mask_list, prob_list, strategy)
#
#     contour_mask = NextGenTrackerRoutine.get_contour_mask(masks)
#
#     # print unique cells before and after merging
#     print(f"unique cells before: {len(masks)}, after: {np.unique(masks)}")
#
#     queue.put((layer_idx, masks, contour_mask))

def run_detect_rois(pretrained_model_path, diameter, cellprob_threshold, flow_threshold,
                    mproj, layer_idx, strategy, queue, device_id=0):
    print(f"Running Cellpose on layer {layer_idx}, shape: {mproj.shape} on GPU {device_id}")

    # Set correct GPU device for this process
    torch.cuda.set_device(device_id)

    model = CellposeModel(gpu=True, pretrained_model=pretrained_model_path, device=torch.device(f"cuda:{device_id}"))

    masks, flows, _ = model.eval(
        mproj,
        channels=[0, 0],
        diameter=diameter,
        cellprob_threshold=cellprob_threshold,
        flow_threshold=flow_threshold,
    )

    contour_mask = NextGenTrackerRoutine.get_contour_mask(masks)

    # Put results in the queue
    queue.put((layer_idx, masks, contour_mask))

class NextGenTrackerRoutine(vxroutine.WorkerRoutine):
    # start_roi_segmentation: bool = False
    output_frame_name: str = 'roi_activity_tracker_frame'
    layer_max_num: int = 20
    roi_max_num: int = 5
    # roi_slice_params: Dict[tuple, tuple] = {}
    # roi_slice_params: Dict[tuple, Tuple[str, Any]] = {}
    roi_slice_params: Dict[tuple, ROI] = {}
    roi_thresholds: Dict[tuple, int] = {}
    lower_px_threshold: int = 10
    frame_width: int = 256
    frame_height: int = 256
    frame_dtype: str = 'float64'
    trigger: vxevent.NewDataTrigger = None
    current_layer_num: int = -1
    new_metadata: bool = False
    attrs_written_to_file: List[str] = []

    #Parameters for cellpose roi detection TODO: might need to be adjusted....
    diameter = 10
    cellprob_threshold = 0.0
    flow_threshold = 1.5
    pretrained_model = "cyto3"


    # test_mask = np.zeros((512, 512), dtype=bool)


    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self._f0 = [0] * 20
        self.segmentation_queue = Queue()

        self.layer_masks = {}

        self.current_auto_segment: bool = False
        self.expected_run_results: int = 0
        self.current_run_results: int = 0
        self.is_pool_closed: bool = True


    def require(self) -> bool:

        # Get frame type and shape
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        shape = (self.frame_width, self.frame_height)

        # Set up all layer/ROI attributes
        for layer_idx in range(self.layer_max_num):

            # Create frame attribute
            vxattribute.ArrayAttribute(f'{self.output_frame_name}_{layer_idx}', shape, dtype)

            for roi_idx in range(self.roi_max_num):
                # self.roi_slice_params[(layer_idx, roi_idx)] = (None, ()) #()
                self.roi_slice_params[(layer_idx, roi_idx)] = ROI()
                self.roi_thresholds[(layer_idx, roi_idx)] = 2000

                # Create ROI attribute
                vxattribute.ArrayAttribute(self.roi_name(layer_idx, roi_idx), (1,), vxattribute.ArrayType.float64)
                vxattribute.ArrayAttribute(f'{self.roi_name(layer_idx, roi_idx)}_zscore', (1,),
                                           vxattribute.ArrayType.float64)

            # Create trigger attribute
            vxattribute.ArrayAttribute(self.trigger_name(layer_idx), (1,), vxattribute.ArrayType.uint8)

        return True

    def initialize(self):
        # Create trigger to which routine should react to
        self.trigger = vxevent.NewDataTrigger('scanimage_frame', callback=self._process_frame)
        self.trigger.set_active()

        # self.segmentation_queue = Queue()

    def main(self, *args, **kwargs):
        # Routine only works on trigger callback
        pass

    # def _process_frame(self, last_idx, last_time, last_frame):
    #     """Method gets last written input frame data as arguments"""
    #
    #     layer_num = ScanImageFrameReceiverTcpServer.instance().layer_num
    #
    #     # If current layer number does not match information from server, reset everything
    #     if self.current_layer_num != layer_num:
    #
    #         self.new_metadata = True
    #         self.current_layer_num = layer_num
    #
    #         for idx in self.roi_slice_params.keys():
    #             self.roi_slice_params[idx] = ()
    #
    #     _, _, last_frame_index = vxattribute.get_attribute('scanimage_frame_index')[int(last_idx)]
    #
    #     last_frame = last_frame.astype(np.float64)
    #
    #     # Frame preprocessing
    #     preprocessed_frame = np.where(last_frame < np.histogram(last_frame, bins=2)[1][1], last_frame, 0)
    #     preprocessed_frame = np.where(preprocessed_frame > self.lower_px_threshold, preprocessed_frame, 0)
    #
    #     # Write to corresponding attribute for interleaved layer
    #     current_layer_idx = int(last_frame_index) % ScanImageFrameReceiverTcpServer.instance().layer_num
    #     vxattribute.write_attribute(f'{self.output_frame_name}_{current_layer_idx}', preprocessed_frame)
    #
    #     # Calculate ROI activity and check against threshold
    #     over_thresh = False
    #     for (layer_idx, roi_idx), slice_params in self.roi_slice_params.items():
    #         if layer_idx != current_layer_idx or len(slice_params) == 0:
    #             continue
    #
    #         roi_str = self.roi_name(layer_idx, roi_idx)
    #
    #         # Get ROI data
    #         _slice = pg.affineSlice(preprocessed_frame, slice_params[0], slice_params[2], slice_params[1], (0, 1))
    #
    #         # Calculate activity
    #         activity = (np.std(_slice) * np.mean(_slice)) / 1000  # TODO: ???
    #         # Write activity attribute
    #         vxattribute.write_attribute(roi_str, activity)
    #
    #         # Calculate zscore
    #         #_, _, past_activities = vxattribute.read_attribute(self.roi_name(layer_idx, roi_idx), last=40)
    #         #past_activities = past_activities.flatten()
    #         #current_zscore = scipy.stats.zmap(past_activities[-1], past_activities[:-1])
    #         #vxattribute.write_attribute(f'{roi_str}_zscore', current_zscore)
    #
    #         # Threshold exceeded for this ROI?
    #         # over_thresh = current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
    #         # over_thresh = over_thresh or current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
    #         over_thresh = over_thresh or activity > self.roi_thresholds[(layer_idx, roi_idx)]
    #
    #         # Add attribute to be written to file
    #         if roi_str not in self.attrs_written_to_file:
    #             # Register with plotter
    #             vxattribute.write_to_file(self, roi_str)
    #             self.attrs_written_to_file.append(roi_str)
    #
    #     # Write trigger
    #     trigger_str = self.trigger_name(current_layer_idx)
    #     vxattribute.write_attribute(trigger_str, int(over_thresh))
    #
    #     # Add attribute to be written to file
    #     if trigger_str not in self.attrs_written_to_file:
    #         vxattribute.write_to_file(self, trigger_str)
    #         self.attrs_written_to_file.append(trigger_str)

    def _process_frame(self, last_idx, last_time, last_frame):
        """Method gets last written input frame data as arguments"""

        layer_num = ScanImageFrameReceiverTcpServer.instance().layer_num

        # If current layer number does not match information from server, reset everything
        if self.current_layer_num != layer_num:

            self.new_metadata = True
            self.current_layer_num = layer_num

            for idx in self.roi_slice_params.keys():
                # self.roi_slice_params[idx] = (None, ()) # ()
                self.roi_slice_params[idx] = ROI()

        _, _, last_frame_index = vxattribute.get_attribute('scanimage_frame_index')[int(last_idx)]

        last_frame = last_frame.astype(np.float64)

        # Frame preprocessing
        preprocessed_frame = np.where(last_frame < np.histogram(last_frame, bins=2)[1][1], last_frame, 0)
        preprocessed_frame = np.where(preprocessed_frame > self.lower_px_threshold, preprocessed_frame, 0)

        # Write to corresponding attribute for interleaved layer
        current_layer_idx = int(last_frame_index) % ScanImageFrameReceiverTcpServer.instance().layer_num
        vxattribute.write_attribute(f'{self.output_frame_name}_{current_layer_idx}', preprocessed_frame)

        # Calculate ROI activity and check against threshold
        over_thresh = False
        # for (layer_idx, roi_idx), (mode, params) in self.roi_slice_params.items(): #slice_params
        # for (layer_idx, roi_idx), roi in self.roi_slice_params.items():
        #     if layer_idx != current_layer_idx or len(roi.params) == 0:
        #         continue
        #
        #     roi_str = self.roi_name(layer_idx, roi_idx)
        #
        #     if roi.mode == 'affine_slice':
        #         slice_params = roi.params
        #         _slice, _ = pg.affineSlice(preprocessed_frame, slice_params[0], slice_params[2], slice_params[1], (0, 1), returnCoords=True)
        #         activity_pixels = _slice.flatten()
        #
        #         # if not hasattr(self, 'test_coords') or not np.array_equal(self.test_coords, coords):
        #         #     self.test_coords = coords.copy()  # store the new coords
        #         #
        #         #     print(f'New coords detected. Shape: {coords.shape}')
        #         #
        #         #     x = coords[1]
        #         #     y = coords[0]
        #         #
        #         #     plt.figure(figsize=(6, 6))
        #         #     plt.imshow(preprocessed_frame, cmap='gray')
        #         #     plt.scatter(x.flatten(), y.flatten(), s=1, c='red')
        #         #     plt.title('Sampled ellipse coordinates')
        #         #     plt.show()
        #
        #
        #     ##TODO: 30.06 verify if the mask matches the cellpose mask
        #     elif roi.mode == 'polyline_points':
        #         points = np.array(roi.params)
        #         # print(f"points: {points.dtype}, {points.shape}, {points}")
        #         points_int = np.round(points).astype(np.int32)
        #
        #         contour = points_int.reshape((-1, 1, 2))
        #
        #         contour = contour[..., [1, 0]]# switch x and y
        #
        #         mask = np.zeros(preprocessed_frame.shape, dtype=np.uint8)
        #         cv2.fillPoly(mask, [contour], color=1)
        #         # new_mask = mask.astype(bool)
        #         #
        #         # if not np.array_equal(self.test_mask, new_mask):
        #         #     self.test_mask = new_mask
        #         #     print(f"Updated reconstructed mask: {self.test_mask.shape}, sum: {np.sum(self.test_mask)}")
        #         #
        #         #     # Simple plot for quick visual validation
        #         #     plt.figure(figsize=(5, 5))
        #         #     plt.imshow(new_mask, cmap='gray')
        #         #     plt.imshow(preprocessed_frame, cmap='gray', alpha=0.5)
        #         #     plt.title('New Mask Validation')
        #         #     plt.axis('equal')
        #         #     plt.show()
        #
        #         activity_pixels = preprocessed_frame[mask > 0]
        #
        #     else:
        #         print(f'Error: {roi.mode} is not supported.')
        #
        #     # # Get ROI data
        #     # _slice = pg.affineSlice(preprocessed_frame, slice_params[0], slice_params[2], slice_params[1], (0, 1))
        #     #
        #     # # Calculate activity
        #     # activity = (np.std(_slice) * np.mean(_slice)) / 1000  # TODO: ???
        #     # # Write activity attribute
        #     # vxattribute.write_attribute(roi_str, activity)
        #     if len(activity_pixels) > 0:
        #         activity = np.mean(activity_pixels) # (np.std(activity_pixels) * np.mean(activity_pixels)) / 1000
        #     else:
        #         activity = 0
        #     vxattribute.write_attribute(roi_str, activity)
        #
        #     # Calculate zscore
            #_, _, past_activities = vxattribute.read_attribute(self.roi_name(layer_idx, roi_idx), last=40)
            #past_activities = past_activities.flatten()
            #current_zscore = scipy.stats.zmap(past_activities[-1], past_activities[:-1])
            #vxattribute.write_attribute(f'{roi_str}_zscore', current_zscore)

            # Threshold exceeded for this ROI?
            # over_thresh = current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
            # over_thresh = over_thresh or current_zscore > self.roi_thresholds[(layer_idx, roi_idx)]
            # over_thresh = over_thresh or activity > self.roi_thresholds[(layer_idx, roi_idx)]
            #
            # if roi_str not in self.attrs_written_to_file:
            #     # Register with plotter
            #     vxattribute.write_to_file(self, roi_str)
            #     self.attrs_written_to_file.append(roi_str)

        for (layer_idx, roi_idx), roi in self.roi_slice_params.items():
            if layer_idx != current_layer_idx or roi.params is None:
                continue

            roi_str = self.roi_name(layer_idx, roi_idx)
            activity = roi.calculate_activity(preprocessed_frame)
            vxattribute.write_attribute(roi_str, activity)

            over_thresh = over_thresh or activity > roi.threshold

            # Add attribute to be written to file
            if roi_str not in self.attrs_written_to_file:
                vxattribute.write_to_file(self, roi_str)
                self.attrs_written_to_file.append(roi_str)


        # Write trigger
        trigger_str = self.trigger_name(current_layer_idx)
        vxattribute.write_attribute(trigger_str, int(over_thresh))

        # Add attribute to be written to file
        if trigger_str not in self.attrs_written_to_file:
            vxattribute.write_to_file(self, trigger_str)
            self.attrs_written_to_file.append(trigger_str)

    @staticmethod
    def roi_name(layer_idx: int, roi_idx: int) -> str:
        return f'roi_activity_{layer_idx}_{roi_idx}'

    @staticmethod
    def trigger_name(layer_idx: int) -> str:
        return f'roi_activity_trigger_{layer_idx}'


    def get_projection_for_layer(self, layer_idx: int, n_frames: int = 60, mode: str ='mean') -> np.ndarray:
        """Get an average or max projection of the last `n_frames` for a given layer."""

        _, _, frames = vxattribute.read_attribute(f'{self.output_frame_name}_{layer_idx}', last=n_frames)

        print(f"frames shape: {frames.shape}, frame 0: {frames[0].shape}")

        if frames is None or len(frames) == 0:
            return None

        if mode == 'max':
            return np.max(frames, axis=0)

        elif mode == 'mean':
            return np.mean(frames, axis=0)

        else:
            raise ValueError(f'Invalid mode {mode}. Must be either "max" or "mean".')



    @staticmethod
    def get_contour_mask(label_mask, method='opencv'):
        """
        Extract contours of labeled regions in a mask.

        Parameters:
        - label_mask: 2D numpy array, with 0 as background and positive integers as labels.
        - method: str, one of ['scipy', 'skimage', 'opencv']

        Returns:
        - contour_mask: 2D numpy array of same shape with contours of regions labeled, background 0.
        """
        method = method.lower()

        if method == 'scipy':
            contour = np.zeros_like(label_mask)
            for label in np.unique(label_mask):
                if label == 0:
                    continue
                region = (label_mask == label)
                eroded = binary_erosion(region)
                contour[region & ~eroded] = label
            return contour

        elif method == 'skimage':
            # boundaries = find_boundaries(label_mask, mode='outer')
            # contour = np.zeros_like(label_mask)
            # contour[boundaries] = label_mask[boundaries]
            return find_boundaries(label_mask, mode='outer')

        elif method == 'opencv':
            contour = np.zeros_like(label_mask, dtype=np.uint8)
            for label in np.unique(label_mask):
                if label == 0:
                    continue
                binary_region = np.uint8(label_mask == label) * 255
                contours, _ = cv2.findContours(binary_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) ## CHAIN_APPROX_SIMPLE??
                cv2.drawContours(contour, contours, -1, int(label), thickness=0)
            return contour

        else:
            raise ValueError(f"Unsupported method '{method}'. Choose from 'scipy', 'skimage', or 'opencv'.")

    def merge_masks_with_strategy(mask_list: list, prob_list: list = None, strategy: str = "ignore"):
        """
        Merge masks using a specified strategy:
        - "ignore": overlapping pixels are set to 0.
        - "probability": choose label with highest cell probability at overlapping pixels.

        Args:
            mask_list (list of np.ndarray): List of binary masks (2D).
            prob_list (list of np.ndarray, optional): List of 2D cell probability maps matching masks.
            strategy (str): "ignore" or "probability".

        Returns:
            np.ndarray: Final labeled mask.
        """
        if not mask_list:
            return None

        shape = mask_list[0].shape
        label_mask = np.zeros(shape, dtype=np.int32)
        prob_mask = np.zeros(shape, dtype=np.float32) if strategy == "probability" else None
        coverage_count = np.zeros(shape, dtype=np.uint8)

        for idx, mask in enumerate(mask_list, start=1):
            mask = (mask > 0)

            if strategy == "ignore":
                coverage_count += mask.astype(np.uint8)
                label_mask[(mask) & (label_mask == 0)] = idx

            elif strategy == "probability" and prob_list is not None:
                prob = prob_list[idx - 1]
                update_pixels = (mask) & (prob > prob_mask)
                label_mask[update_pixels] = idx
                prob_mask[update_pixels] = prob[update_pixels]

        if strategy == "ignore":
            label_mask[coverage_count > 1] = 0  # Remove overlapping pixels
            #print sum of coverage_count
            print(f"Overlap count: {coverage_count.sum()}")

        print(f"unique ROI detected: {np.unique(label_mask)}")

        return label_mask


    def button_start_segmentation_clicked(self):
        print("Start segmentation")

        num_layers = ScanImageFrameReceiverTcpServer.instance().layer_num
        layer_indices = list(range(num_layers))


        # self.current_auto_segment = True
        self.is_pool_closed = False
        self.current_run_results = 0
        self.expected_run_results = num_layers

        # Get projections for all layers
        projections = []
        for layer_idx in layer_indices:
            mproj = self.get_projection_for_layer(layer_idx)
            if mproj is None:
                log.warning(f"No data to segment for layer {layer_idx}")
                return
            projections.append(mproj)

        # Setup Manager and Queue
        self.manager = mp.Manager()
        self.segmentation_queue = self.manager.Queue()

        # Determine number of GPUs and processes to spawn
        num_gpus = torch.cuda.device_count()
        processes = min(len(layer_indices), num_gpus)
        print(f"Using {processes} GPU(s) for segmentation")

        self.pool = mp.Pool(processes=processes)

        # Dispatch tasks round-robin assigning GPU device ids
        for i, (layer_idx, mproj) in enumerate(zip(layer_indices, projections)):
            device_id = i % num_gpus
            args = (
                self.pretrained_model,
                self.diameter,
                self.cellprob_threshold,
                self.flow_threshold,
                mproj,
                layer_idx,
                "ignore",
                self.segmentation_queue,
                device_id
            )
            self.pool.apply_async(run_detect_rois, args=args)

        # self.current_auto_segment = True

        # Start your timer or periodic check for queue consumption here
        # self.start_checking_segmentation_queue()

    # def check_segmentation_result(self):
    #     if self.current_auto_segment and self.segmentation_queue and not self.segmentation_queue.empty():
    #         layer_idx, merged_mask, contour_mask = self.segmentation_queue.get()
    #         # self.mask = merged_mask
    #         print(f"Segmentation done for layer {layer_idx}, mask shape: {merged_mask.shape}")
    #
    #         # Update masks dictionary (assume self.layer_masks is dict[int, np.ndarray])
    #         self.layer_masks[layer_idx] = {
    #             'merged_mask': merged_mask,
    #             'contour_mask': contour_mask
    #         }
    #         # print(f"Full_mask shape: {self.merged_mask.shape}, {merged_mask}")
    #         # print(f"Contour_mask shape: {self.contour_mask.shape}, {self.contour_mask}")
    #
    #         # Clean up the process object
    #         self.segmentation_process.join()
    #         self.segmentation_process = None
    #         self.current_auto_segment = False
    def check_segmentation_result(self):
        while self.current_auto_segment and self.segmentation_queue and not self.segmentation_queue.empty():
            layer_idx, merged_mask, contour_mask = self.segmentation_queue.get()
            print(f"Segmentation done for layer {layer_idx}, mask shape: {merged_mask.shape}")

            self.layer_masks[layer_idx] = {
                'merged_mask': merged_mask,
                'contour_mask': contour_mask
            }
            self.current_run_results += 1

        # If all layers finished
        # if self.current_auto_segment and len(self.layer_masks) == ScanImageFrameReceiverTcpServer.instance().layer_num:

        if self.expected_run_results == self.current_run_results and not self.is_pool_closed and self.current_auto_segment:
            print("All segmentations complete.")
            self.current_auto_segment = False

            self.pool.close()
            self.pool.join()
            self.manager.shutdown()
            self.is_pool_closed = True

    # def calculate_elipse_parameters(mask_data, label_id):
    #     binary_mask = (mask_data == label_id).astype(np.uint8)
    #     props = regionprops(binary_mask)
    #
    #     if not props:
    #         return None  # No ROI
    #
    #     prop = props[0]
    #
    #     cy, cx = prop.centroid  # N
    #     major = prop.major_axis_length
    #     minor = prop.minor_axis_length
    #     angle_rad = prop.orientation
    #     angle_deg = np.degrees(angle_rad)
    #
    #     # EllipseROI needs the top-left corner and size (width, height)
    #     width, height = major, minor
    #
    #     def rotated_top_left(cx, cy, width, height, angle_deg):
    #         angle_rad = np.deg2rad(angle_deg)
    #
    #         # Center to corner vector before rotation (in local ellipse space)
    #         dx = -width / 2
    #         dy = -height / 2
    #
    #         # Rotate vector to get offset in global coordinates
    #         rotated_dx = dx * np.cos(angle_rad) - dy * np.sin(angle_rad)
    #         rotated_dy = dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
    #
    #         # Apply offset to centroid
    #         top_left_x = cx + rotated_dx
    #         top_left_y = cy + rotated_dy
    #
    #         return top_left_x, top_left_y
    #
    #     top_left_x, top_left_y = rotated_top_left(cx, cy, width, height, angle_deg)
    #
    #     pos = (top_left_y, top_left_x)
    #     size = (height, width) ###
    #
    #     return pos, size, angle_deg
    @staticmethod
    def calculate_ellipse_parameters(mask_data, label_id):
        binary_mask = (mask_data == label_id).astype(np.uint8)
        props = regionprops(binary_mask)

        if not props:
            return None  # No ROI

        prop = props[0]

        cx, cy = prop.centroid  #
        major = prop.major_axis_length
        minor = prop.minor_axis_length

        angle_rad = prop.orientation
        angle_deg = np.degrees(angle_rad)

        print(f"angle_deg: {angle_deg}")

        width, height = major, minor
        # bottom_left_x = cx - width / 2
        # bottom_left_y = cy + height / 2
        # size = (height,width)

        ys, xs = np.where(binary_mask == 1)

        # Find min and max
        min_x, max_x = xs.min(), xs.max()
        min_y, max_y = ys.min(), ys.max()


        #check if the angle is between
        pos = (min_y, min_x)



        size = (max_y - min_y, max_x - min_x)

        # print(f"pos (y,x): {pos}, size (hight,width): {size}")

        return pos, size, angle_deg

    #TODO: think about other implementations eg. KDtree ?
    @staticmethod
    def find_nearest_label(y, x, mask_data):
        roi_coords = np.argwhere(mask_data > 0)
        if roi_coords.size == 0:
            return None

        distances = np.sum((roi_coords - [y, x]) ** 2, axis=1)
        nearest_idx = np.argmin(distances)
        nearest_coord = roi_coords[nearest_idx]
        nearest_label = mask_data[tuple(nearest_coord)]
        return nearest_label

    @staticmethod
    def get_contour_outline(mask_data, label_id):
        mask = mask_data.copy()
        mask[mask != label_id] = 0
        mask = mask.astype(np.uint8)

        # num_pixels = np.sum(mask_data == label_id)
        # print(f"OG mask shape: {mask.shape}, Number of pixels with label_id {label_id}: {num_pixels}")

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return None

        # Return the largest (outer) contour as (x, y) tuples
        # return [tuple(pt[0]) for pt in max(contours, key=cv2.contourArea)]
        return [(pt[0][1], pt[0][0]) for pt in max(contours, key=cv2.contourArea)]




class NextGenTrackerWidget(vxui.WorkerAddonWidget):
    display_name = 'Imaging stream'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize tracking state
        self.current_num_layers = -1
        self.image_plots = {}  # layer_idx -> ImagePlot instance
        self.rois = {}         # (layer_idx, roi_idx) -> ROI instance
        self.threshold_widgets = {}
        self.histograms = {}
        self.init_histograms = []


        # === Layout Setup ===
        self.central_widget.setLayout(QtWidgets.QVBoxLayout())

        # --- Warning label ---
        warning_label = QtWidgets.QLabel(
            '!!! WARNING: disconnect imaging client BEFORE closing vxpy !!!')
        warning_label.setStyleSheet('font-weight:bold; color: #FF0000; text-align: center; '
                                    'border: 1px solid #FF0000; padding: 5px;')
        self.central_widget.layout().addWidget(warning_label)

        # --- Pixel threshold slider ---
        self.pixel_threshold = widgets.IntSliderWidget(
            self.central_widget,
            label='Lower pixel threshold',
            default=NextGenTrackerRoutine.instance().lower_px_threshold,
            limits=(1, 2 ** 16), step_size=10)
        self.pixel_threshold.connect_callback(self.update_pixel_threshold)
        self.central_widget.layout().addWidget(self.pixel_threshold)

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
        self.scroll_layout = QtWidgets.QGridLayout()  # Use QGridLayout here
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        # Add the group box to the right side layout
        right_layout.addWidget(self.selected_roi_container)

        # --- Action buttons ---
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QVBoxLayout(button_container)

        self.add_auto_btn = QtWidgets.QPushButton('Automated ROI Search')
        self.add_auto_btn.clicked.connect(self.automated_roi_search)
        button_layout.addWidget(self.add_auto_btn)

        # Toggle mask button
        self.toggle_mask_btn = QtWidgets.QPushButton('Show ROI mask')
        button_layout.addWidget(self.toggle_mask_btn)
        # Left click shows full mask
        self.toggle_mask_btn.clicked.connect(lambda: self.toggle_mask(only_contours=False))

        # Right click shows contour mask
        self.toggle_mask_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.toggle_mask_btn.customContextMenuRequested.connect(lambda _: self.toggle_mask(only_contours=True))


        self.selected_histogram_layer = None
        self.plot_highlight_rect = None


        self.open_window_btn = QtWidgets.QPushButton('Export to SysCon')
        self.open_window_btn.clicked.connect(self.to_holo)
        button_layout.addWidget(self.open_window_btn)


        right_layout.addWidget(button_container)
        right_layout.addStretch()

        # --- Frame routine integration ---
        self.frame_name = NextGenTrackerRoutine.instance().output_frame_name
        self.connect_to_timer(self.update_frame)

    @staticmethod
    def update_pixel_threshold(value: int):
        """Update threshold in the core processing routine."""
        NextGenTrackerRoutine.instance().lower_px_threshold = value

    # def toggle_histograms(self):
    #     if self.visible_histogram:
    #         self.img_plot_widget.removeItem(self.selected_histogram)
    #         self.visible_histogram = False
    #     else:
    #         self.img_plot_widget.addItem(self.selected_histogram, col= self.cols + 1, row=0, rowspan=self.cols)
    #         self.visible_histogram = True


    def update_frame(self):
        """Pull frames and update all plots."""
        routine = NextGenTrackerRoutine.instance()
        layer_num = routine.current_layer_num
        routine.check_segmentation_result()

        if routine.new_metadata or (layer_num != self.current_num_layers):
            self._rebuild_image_plots(layer_num)
            routine.new_metadata = False

        for layer_idx, image_plot in self.image_plots.items():
            idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}', last=10)
            if len(idx) == 0:
                continue
            frame_avg = np.mean(frame, axis=0)
            image_plot.update_frame(frame_avg)

            if self.init_histograms[layer_idx] == True:
                immin, immax = np.min(frame), np.max(frame)
                self.histograms[layer_idx].setHistogramRange(immin, immax)
                self.histograms[layer_idx].setLevels(immin, immax)
                self.init_histograms[layer_idx] = False


        self.update_button_state()

        if self.plot_highlight_rect and self.selected_histogram_layer is not None:
            plot_item = self.image_plots[self.selected_histogram_layer].get_plot_item()
            new_rect = plot_item.sceneBoundingRect()
            if new_rect != self.plot_highlight_rect.rect():
                self.plot_highlight_rect.setRect(new_rect)
        # for layer_idx, image_plot in self.image_plots.items():
        #     idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}', last=10)
        #     if len(idx) == 0:
        #         continue
        #     frame_avg = np.mean(frame, axis=0)
        #
        #     # Use histogram's level range
        #     histogram = self.histograms[layer_idx]
        #     levels = histogram.getLevels()
        #     if levels is not None:
        #         image_plot.image_item.setImage(frame_avg, autoLevels=False, levels=levels)
        #     else:
        #         image_plot.image_item.setImage(frame_avg, autoLevels=False)
        # self.update_button_state()

    # def _rebuild_image_plots(self, num_layers):
    #     """Clear and rebuild plots for all layers."""
    #     self.img_plot_widget.clear()
    #     self.image_plots.clear()
    #
    #     cols = math.ceil(math.sqrt(num_layers))
    #
    #     for i in range(num_layers):
    #         image_plot = ImagePlot(i, on_roi_selected=self.handle_roi_click)
    #         self.image_plots[i] = image_plot
    #         plot_item = image_plot.plot_item
    #         self.img_plot_widget.addItem(plot_item, row=i // cols, col=i % cols)
    #
    #     self.current_num_layers = num_layers

    def _rebuild_image_plots(self, num_layers):
        self.img_plot_widget.clear()
        self.image_plots.clear()
        self.histograms.clear()

        self.cols = math.ceil(math.sqrt(num_layers))
        self.rows = math.ceil(math.sqrt(num_layers))

        self.init_histograms = [True]*num_layers

        for i in range(num_layers):
            image_plot = ImagePlot(i, on_roi_selected=self.handle_roi_click, on_histogram_selected=self.select_histogram)
            self.image_plots[i] = image_plot
            self.histograms[i] = pg.HistogramLUTItem(image_plot.image_item)
            # self.histograms[i].disableAutoHistogramRange()

            # Use img_plot_widget (GraphicsLayout) directly, row layout
            self.img_plot_widget.addItem(image_plot.plot_item, row=i // self.cols, col=i % self.cols)
            # self.img_plot_widget.addItem(histogram, row=i // cols * 2 + 1, col=i % cols)

        # self.select_histogram(0)
        self.current_num_layers = num_layers

    # def select_histogram(self, layer_idx):
    #     """Called by ImagePlot on double-click to toggle histogram."""
    #     # Remove currently shown histogram if one is visible
    #     print(f"select_histogram called for layer {layer_idx}")
    #     if self.visible_histogram:
    #         # Same layer clicked again → hide
    #         if self.selected_histogram_layer == layer_idx:
    #             self.img_plot_widget.removeItem(self.selected_histogram)
    #             # self.highlighted_plot.remove_highlight()
    #             if self.plot_highlight_rect:
    #                 self.img_plot_widget.scene().removeItem(self.plot_highlight_rect)
    #                 self.plot_highlight_rect = None
    #
    #             self.selected_histogram_layer = None
    #             self.visible_histogram = False
    #             self.highlighted_plot = None
    #             return
    #         else:
    #             # Remove old histogram and highlight
    #             self.img_plot_widget.removeItem(self.selected_histogram)
    #             if self.highlighted_plot:
    #                 self.highlighted_plot.remove_highlight()
    #     self.img_plot_widget.remove_highlight()
    #     # Show new histogram
    #     self.selected_histogram = self.histograms[layer_idx]
    #     self.img_plot_widget.addItem(
    #         self.selected_histogram, col=self.cols + 1, row=0, rowspan=self.rows)
    #     self.selected_histogram_layer = layer_idx
    #     self.visible_histogram = True
    #
    #     self.highlighted_plot = self.image_plots[layer_idx]
    #     # self.highlighted_plot.highlight()
    #
    #     self.highlight_plot_item(self.image_plots[layer_idx].get_plot_item())
    def select_histogram(self, layer_idx: int):
        """Toggle histogram and highlight for a selected image layer."""
        print(f"select_histogram called for layer {layer_idx}")

        # Case 1: Same layer clicked again → hide
        if self.selected_histogram_layer == layer_idx:
            self.img_plot_widget.removeItem(self.histograms[layer_idx])
            self._remove_plot_highlight()
            self.selected_histogram_layer = None
            return

        # Case 2: Different layer clicked
        if self.selected_histogram_layer is not None:
            self.img_plot_widget.removeItem(self.histograms[self.selected_histogram_layer])
            self._remove_plot_highlight()

        # Show new histogram and highlight
        self.selected_histogram_layer = layer_idx
        self.img_plot_widget.addItem(
            self.histograms[layer_idx], col=self.cols + 1, row=0, rowspan=self.rows
        )
        self._highlight_plot_item(self.image_plots[layer_idx].get_plot_item())

    def _highlight_plot_item(self, plot_item):
        """Add yellow border around the selected plot."""
        self._remove_plot_highlight()

        rect = plot_item.sceneBoundingRect()
        highlight_rect = QtWidgets.QGraphicsRectItem(rect)
        highlight_rect.setPen(pg.mkPen('y', width=4))
        highlight_rect.setZValue(1000)
        self.img_plot_widget.scene().addItem(highlight_rect)
        self.plot_highlight_rect = highlight_rect

    def _remove_plot_highlight(self):
        """Remove the highlight border if it exists."""
        if hasattr(self, 'plot_highlight_rect') and self.plot_highlight_rect:
            self.img_plot_widget.scene().removeItem(self.plot_highlight_rect)
            self.plot_highlight_rect = None

    # def highlight_plot_item(self, plot_item):
    #     """Draw a yellow border around the given PlotItem inside the layout."""
    #     if hasattr(self, 'plot_highlight_rect') and self.plot_highlight_rect:
    #         self.img_plot_widget.scene().removeItem(self.plot_highlight_rect)
    #         self.plot_highlight_rect = None
    #
    #     # Get bounding rectangle in scene coordinates
    #     rect = plot_item.sceneBoundingRect()
    #
    #     # Create and add new highlight rect
    #     highlight_rect = QtWidgets.QGraphicsRectItem(rect)
    #     highlight_rect.setPen(pg.mkPen('y', width=4))
    #     highlight_rect.setZValue(1000)
    #
    #     self.img_plot_widget.scene().addItem(highlight_rect)
    #     self.plot_highlight_rect = highlight_rect

    def handle_roi_click(self, layer, x, y, roi_style):
        """Callback for interactive ROI selection via mouse."""
        routine = NextGenTrackerRoutine.instance()
        mask_data = routine.layer_masks.get(layer, {}).get('merged_mask')

        if roi_style == "ellipse":
            self.add_roi(layer_idx=layer, roi_style=roi_style)

        if mask_data is None or not (0 <= x < mask_data.shape[1] and 0 <= y < mask_data.shape[0]):
            print("No valid mask")
            return

        label_id = mask_data[y, x]
        if label_id == 0:
            label_id = routine.find_nearest_label(y, x, mask_data)

        if not label_id:
            print("No ROI found")
            return



        elif roi_style == "poly_line":
            outline = routine.get_contour_outline(mask_data, label_id)
            if outline:
                self.add_roi(layer_idx=layer, roi_style=roi_style, contours=outline)

    def add_roi(self, layer_idx: int, position=None, size=None, angle_degree=None,
                roi_style="ellipse", contours=None):
        """Add a new ROI to the specified layer."""
        image_plot = self.image_plots.get(layer_idx)
        if image_plot is None:
            print(f"No ImagePlot found for layer {layer_idx}")
            return

        roi_idx = self.get_next_free_roi_index()
        if roi_idx is None:
            log.warning('Failed to add ROI. Maximum number of ROIs exceeded')
            return

        # if roi_idx >= NextGenTrackerRoutine.instance().roi_max_num:
        #     log.warning('Failed to add ROI. Maximum number of ROIs exceeded')
        #     return

        # if roi_idx == 0:
        if len(self.rois) == 0:
                vxui.register_with_plotter(NextGenTrackerRoutine.trigger_name(layer_idx),
                                       name=f'Activity trigger for layer {layer_idx}',
                                       axis='Trigger')

        vxui.register_with_plotter(NextGenTrackerRoutine.roi_name(layer_idx, roi_idx),
                                   name=f'ROI {roi_idx}', axis=f'Layer {layer_idx}',
                                   color=get_roi_color(roi_idx))
        vxui.register_with_plotter(f'{NextGenTrackerRoutine.roi_name(layer_idx, roi_idx)}_zscore',
                                   name=f'ROI {roi_idx}', axis=f'Layer {layer_idx} zscore',
                                   color=get_roi_color(roi_idx))


        if roi_style == "ellipse":
            if all(v is None for v in (position, size)):
                width = NextGenTrackerRoutine.instance().frame_width
                diameter = width // 4
                center = (width // 2, width // 2)
                position = (center[0] - diameter / 2, center[1] - diameter / 2) # (0,0) #
                size = (diameter, diameter) #(30,60) #
                angle_degree = 0



            # roi = EllipseRoi(layer_idx, roi_idx, image_plot, (0, 0), (1, 1))
            roi = EllipseRoi(
                layer_idx=layer_idx,
                idx=roi_idx,
                image_plot=image_plot,
                update_callback=self.roi_updated,  # <--- hook it up here
                pos=(0, 0),
                size=(1, 1)
            )
            # TODO: 24.06 --> fix here for correct layout in pyqt image
            image_plot.add_roi_to_plot(roi)

            print(f"position in yx: {position[1], position[0]}")
            roi.setPos((position[1], position[0]))
            roi.setSize((size[1], size[0]))
            roi.setAngle(angle_degree)

        elif roi_style == "poly_line":

            # print(f"contours: {contours}")
            roi = PolyLineRoi(layer_idx, roi_idx, image_plot, points = contours)
            image_plot.add_roi_to_plot(roi)
            self.roi_updated(roi, layer_idx, image_plot)


        self.rois[(layer_idx, roi_idx)] = roi

        # Create label
        label_button = QtWidgets.QPushButton(f'ROI {roi_idx} [{layer_idx}]')
        label_button.setFlat(True)
        label_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        def context_menu_handler(_):
            self.delete_specific_roi(roi_idx= roi_idx, layer_idx= layer_idx)

        label_button.customContextMenuRequested.connect(context_menu_handler)

        # Add to scroll layout
        self.scroll_layout.addWidget(label_button, roi_idx, 0)

        # Create threshold slider
        thresh = widgets.DoubleSliderWidget(self.scroll_widget,
                                            default=NextGenTrackerRoutine.instance().roi_thresholds.get(
                                                (layer_idx, roi_idx), 1.0),
                                            limits=(0, 50), step_size=0.1)
        thresh.connect_callback(roi.update_threshold)

        # Add to scroll layout
        self.scroll_layout.addWidget(thresh, roi_idx, 1)

        # Track references
        self.threshold_widgets[roi_idx] = thresh
        roi.label_button = label_button



    def delete_specific_roi(self, layer_idx: int, roi_idx: int):
        """Delete a specific ROI from both data and UI."""
        roi = self.rois.pop((layer_idx, roi_idx), None)
        if roi is None:
            log.warning(f"ROI {roi_idx} not found on layer {layer_idx}")
            return

        plot = self.image_plots[layer_idx]
        plot.plot_item.getViewBox().removeItem(roi)
        if hasattr(roi, "label"):
            plot.plot_item.removeItem(roi.label)

        thresh_widget = self.threshold_widgets.pop(roi_idx, None)
        if thresh_widget:
            self.scroll_widget.layout().removeWidget(thresh_widget)
            thresh_widget.deleteLater()

        if hasattr(roi, "label_button"):
            self.scroll_widget.layout().removeWidget(roi.label_button)
            roi.label_button.deleteLater()

        # Remove from processing and plotting systems
        routine = NextGenTrackerRoutine.instance()
        del routine.roi_slice_params[(layer_idx, roi_idx)]
        routine.roi_thresholds[(layer_idx, roi_idx)] = 2000

        vxui.remove_from_plotter(NextGenTrackerRoutine.roi_name(layer_idx, roi_idx), axis=f'Layer {layer_idx}')
        vxui.remove_from_plotter(f'{NextGenTrackerRoutine.roi_name(layer_idx, roi_idx)}_zscore', axis=f'Layer {layer_idx} zscore')

        log.info(f"Deleted ROI {roi_idx} from layer {layer_idx}")

    def toggle_mask(self, only_contours: bool = True):
        mask_dict = NextGenTrackerRoutine.instance().layer_masks

        # Safer way to access first key
        mask_keys = list(mask_dict.keys())
        if not mask_keys:
            QtWidgets.QMessageBox.information(self, "No Masks", "No segmentation masks found.")
            return
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
                    mask_array = masks.get('contour_mask')
                    if mask_array is not None:
                        red_mask = np.zeros((mask_array.shape[0], mask_array.shape[1], 3), dtype=np.uint8)
                        red_mask[mask_array > 0, 0] = 255  # Red channel
                        image_plot.mask_item.setImage(red_mask)
                    else:
                        image_plot.mask_item.setImage(mask_array)
                else:
                    mask_array = masks.get('merged_mask')
                    image_plot.mask_item.setImage((mask_array > 0))

        self.toggle_mask_btn.setText("Hide ROI mask" if target_visibility else "Show ROI mask")

    def roi_updated(self, roi: Union[EllipseRoi, PolyLineRoi], layer_idx: int, image_plot: ImagePlot):
        log.debug(f'Update ROI for layer {layer_idx}, ROI idx {roi.idx}')

        if isinstance(roi, PolyLineRoi):
            points = roi.getState()['points']
            roi_instance = ROI(mode='polyline_points', params=points, layer_idx=layer_idx)

        elif isinstance(roi, EllipseRoi):
            # Pass current image from ImagePlot to EllipseRoi method
            # slice_params = roi.getAffineSliceParams(image_plot.image_item.image, image_plot)
            slice_params = roi.getAffineSliceParams(image_plot.image_item.image, image_plot.image_item)
            roi_instance = ROI(mode='affine_slice', params=slice_params, layer_idx=layer_idx)

        else:
            raise ValueError(f"Invalid ROI type: {type(roi)}")

        roi_instance.calculate_center(image_frame=np.zeros((ScanImageFrameReceiverTcpServer.instance().frame_height, ScanImageFrameReceiverTcpServer.instance().frame_width)))
        roi_instance.calculate_z()
        roi_instance.tracked = True

        NextGenTrackerRoutine.instance().roi_slice_params[(layer_idx, roi.idx)] = roi_instance



    def get_next_free_roi_index(self):
        used_indices = {roi_idx for (_, roi_idx) in self.rois.keys()}
        for i in range(NextGenTrackerRoutine.instance().roi_max_num):
            if i not in used_indices:
                return i
        return None

    def update_button_state(self):
        """Enable or disable automated segmentation button."""
        routine = NextGenTrackerRoutine.instance()
        self.add_auto_btn.setEnabled(not routine.current_auto_segment)

    def automated_roi_search(self):
        """Trigger ROI detection routine."""
        routine = NextGenTrackerRoutine.instance()
        if not routine.current_auto_segment:
            routine.current_auto_segment = True
            routine.button_start_segmentation_clicked()
        else:
            print("Automated ROI search already running.")

    def to_holo(self):
        """Export current ROIs to SysConRoutine for downstream processing."""
        syscon = SysConRoutine.instance()
        syscon.num_layers = self.current_num_layers
        syscon.rois_to_stimulate.clear()
        syscon.rois_to_stimulate.update(NextGenTrackerRoutine.instance().roi_slice_params)
        syscon.new_rois_set = True



class ImagePlot:
    def __init__(self, layer_idx, on_roi_selected=None, on_histogram_selected=None):
        self.layer_idx = layer_idx
        self.on_roi_selected = on_roi_selected
        self.on_histogram_selected = on_histogram_selected
        self.no_init = True

        self.plot_item = pg.PlotItem()
        # self.vb = CustomViewBox(parent=self)
        # self.plot_item = pg.PlotItem(viewBox=self.vb)
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        self.plot_item.invertY(True)
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.plot_item.setAspectLocked(True)

        # ROI mask image overlay (initially hidden)
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)  # semi-transparent
        self.mask_item.setVisible(False)
        self.plot_item.addItem(self.mask_item)
        self.mask_visible = False

        # Delay connection to avoid NoneType scene error
        QtCore.QTimer.singleShot(0, self.connect_scene_click)

        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.plot_item.addItem(self.text)
        self.text.setPos(0, 0)



    # def handle_mouse_click(self, event):
    #     if event.button() != QtCore.Qt.LeftButton:
    #         return
    #
    #     pos = event.scenePos()
    #     mouse_point = self.plot_item.vb.mapSceneToView(pos)
    #     y, x = int(mouse_point.x()), int(mouse_point.y())
    #
    #     if event.double():
    #         # Double-click: Histogram selection
    #         if self.on_histogram_selected:
    #             self.on_histogram_selected(layer_idx=self.layer_idx)
    #     else:
    #         # Single-click with modifiers
    #         modifiers = QtWidgets.QApplication.keyboardModifiers()
    #
    #         if modifiers == QtCore.Qt.ControlModifier:
    #             # Ctrl + Click: Poly ROI
    #             if self.on_roi_selected:
    #                 self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style='poly_line')
    #
    #         elif modifiers == QtCore.Qt.AltModifier:
    #             # Alt + Click: Ellipse ROI
    #             if self.on_roi_selected:
    #                 self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style='ellipse') # here x and y are not necessarily needed....
    def handle_mouse_click(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return

        # Only respond if this plot was actually clicked
        if not self.plot_item.sceneBoundingRect().contains(event.scenePos()):
            return

        pos = event.scenePos()
        mouse_point = self.plot_item.vb.mapSceneToView(pos)
        y, x = int(mouse_point.x()), int(mouse_point.y())

        if event.double():
            if self.on_histogram_selected:
                self.on_histogram_selected(layer_idx=self.layer_idx)
        else:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                if self.on_roi_selected:
                    self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style='poly_line')
            elif modifiers == QtCore.Qt.AltModifier:
                if self.on_roi_selected:
                    self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style='ellipse')

    def connect_scene_click(self):
        scene = self.plot_item.scene()
        if scene:
            scene.sigMouseClicked.connect(self.handle_mouse_click)
        else:
            print(f"[Layer {self.layer_idx}] Scene not ready yet.")

    def get_plot_item(self):
        return self.plot_item

    # def update_frame(self, frame: np.ndarray):
    #     """Display a new image frame."""
    #     self.image_item.setImage(frame, autoLevels=False, levels=(np.min(frame), np.max(frame)))

    def update_frame(self, frame: np.ndarray):
        if self.no_init:
            immin, immax = np.min(frame), np.max(frame)
            # self.histogram.setHistogramRange(immin, immax)
            # self.histogram.setLevels(immin, immax)
            self.image_item.setImage(frame, autoLevels=False,levels= (np.min(frame), np.max(frame)))
            self.no_init = False

        self.image_item.setImage(frame, autoLevels=False)

    def interactive_roi_selection(self, event):
        """Handle Ctrl + Left click on image for ROI selection."""
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if event.button() == QtCore.Qt.LeftButton and modifiers == QtCore.Qt.ControlModifier:
            pos = event.scenePos()
            mouse_point = self.plot_item.vb.mapSceneToView(pos)
            y, x = int(mouse_point.x()), int(mouse_point.y())
            if self.on_roi_selected:
                self.on_roi_selected(layer=self.layer_idx, x=x, y=y, roi_style='poly_line')


    def add_roi_to_plot(self, roi):
        self.plot_item.getViewBox().addItem(roi)
        # self.plot_item.addItem(roi.label)




class ImageWidget(QtWidgets.QGroupBox):    #

    def __init__(self, layer_idx: int, **kwargs):
        super().__init__(**kwargs)
        self.layer_idx = layer_idx
        self.setLayout(QtWidgets.QVBoxLayout())

        # Image display area
        self.graphics_widget = pg.GraphicsLayoutWidget(parent=self)
        self.layout().addWidget(self.graphics_widget)

        # Plot setup
        self.image_plot = self.graphics_widget.addPlot(0, 0)
        self.image_item = pg.ImageItem()
        self.image_plot.addItem(self.image_item)
        self.image_plot.invertY(True)
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)

        #make the image interactable to detect roi
        self.image_plot.scene().sigMouseClicked.connect(self.interactive_roi_selection)

        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.image_plot.addItem(self.text)
        self.text.setPos(0, 0)

        # ROI mask image overlay (initially hidden)
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)  # semi-transparent
        self.mask_item.setVisible(False)
        self.image_plot.addItem(self.mask_item)

        self.mask_visible = False

        # Histogram
        self.histogram = pg.HistogramLUTItem()
        self.histogram.setImageItem(self.image_item)
        self.graphics_widget.addItem(self.histogram, 0, 1)

        self.no_init = True
        # self.rois: List[Roi] = []
        # self.threshold_widgets: List[widgets.DoubleSliderWidget] = []
        self.rois = {}
        self.threshold_widgets = {}

        # Toggle mask button
        self.toggle_mask_btn = QtWidgets.QPushButton('Show ROI mask')
        self.layout().addWidget(self.toggle_mask_btn)
        # Left click shows full mask
        self.toggle_mask_btn.clicked.connect(lambda: self.toggle_mask(only_contours=False))

        # Right click shows contour mask
        self.toggle_mask_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.toggle_mask_btn.customContextMenuRequested.connect(lambda _: self.toggle_mask(only_contours=True))

        # --- Tabbed Controls ---
        self.tabs = QtWidgets.QTabWidget(parent=self)
        self.layout().addWidget(self.tabs)

        # ROI Controls tab
        self.roi_controls_widget = QtWidgets.QWidget()
        self.roi_controls_layout = QtWidgets.QVBoxLayout()
        self.roi_controls_widget.setLayout(self.roi_controls_layout)
        self.tabs.addTab(self.roi_controls_widget, "ROI Controls")

        # Scroll area for ROI sliders
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QGridLayout()
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.roi_controls_layout.addWidget(self.scroll_area)

        # Button row
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.roi_controls_layout.addLayout(self.btn_layout)

        # self.add_auto_btn = QtWidgets.QPushButton('Automated ROI Search')
        # self.add_auto_btn.clicked.connect(self.automated_roi_search)
        # self.btn_layout.addWidget(self.add_auto_btn)

        # Prepare a progress bar but keep it hidden #TODO
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)  # Will update dynamically
        self.progress_bar.setVisible(False)
        self.btn_layout.addWidget(self.progress_bar)

        self.add_roi_btn = QtWidgets.QPushButton('Add ROI')
        self.add_roi_btn.clicked.connect(self.add_roi)
        self.btn_layout.addWidget(self.add_roi_btn)

        #Add a button to export to syscon
        # self.open_window_btn = QtWidgets.QPushButton('Export to SysCon')
        # self.layout().addWidget(self.open_window_btn)
        # self.open_window_btn.clicked.connect(self.to_holo)
        # self.syscon_window = None

        # Optional: future settings tab
        self.settings_widget = QtWidgets.QWidget()
        self.settings_layout = QtWidgets.QFormLayout()
        self.settings_widget.setLayout(self.settings_layout)
        self.tabs.addTab(self.settings_widget, "Settings")

        # For consistency with other methods
        self.controls = self.scroll_widget



        # self.last_x, self.last_y = 0, 0

    # def to_holo(self):
    #     for idx in list(SysConRoutine.instance().rois_to_stimulate.keys()):
    #         del SysConRoutine.instance().rois_to_stimulate[idx]
    #
    #     for idx, roi in NextGenTrackerRoutine.instance().roi_slice_params.items():
    #         SysConRoutine.instance().rois_to_stimulate[idx] = roi
    #
    #     SysConRoutine.instance().new_rois_set = True
        # if self.syscon_window is None:
        #     self.syscon_window = SysConControlWindow()
        #     self.syscon_window.show()
        # else:
        #     if self.syscon_window.isVisible():
        #         self.syscon_window.close()
        #     else:
        #         self.syscon_window.show()

    def update_frame(self, frame: np.ndarray):
        if self.no_init:
            immin, immax = np.min(frame), np.max(frame)
            self.histogram.setHistogramRange(immin, immax)
            self.histogram.setLevels(immin, immax)
            self.no_init = False

        self.image_item.setImage(frame, autoLevels=False)

    def get_plot_item(self):
        return self.image_plot

    def interactive_roi_selection(self, event, roi_style: str = 'poly_line'):
        '''
        :param event:
        :param roi_style: poly_line, ellipse
        :return:
        '''
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if event.button() == QtCore.Qt.LeftButton and modifiers == QtCore.Qt.ControlModifier:
            pos = event.scenePos()
            print(f'Click pos (x,y/inverted): {pos}')
            mouse_point = self.image_plot.vb.mapSceneToView(pos)
            y, x = int(mouse_point.x()), int(mouse_point.y()) # switch x and y to handle in np ###<---- here was flipped again....
            print(f"Clicked (x={x}, y={y})")
            # self.last_x, self.last_y = x, y
            # Access mask data
            mask_dict = NextGenTrackerRoutine.instance().layer_masks
            mask_data = mask_dict.get(self.layer_idx, {}).get('merged_mask')  # or 'contour_mask'


            if mask_data is None:
                print("No mask available")
                return

            if not (0 <= x < mask_data.shape[1] and 0 <= y < mask_data.shape[0]):
                print("Click out of bounds")
                return

            label_id = mask_data[y, x]
            if label_id == 0:
                label_id = NextGenTrackerRoutine.instance().find_nearest_label(y=y, x=x, mask_data=mask_data)

            # test_mask = mask_data
            # test_mask[test_mask != label_id] = 0
            # self.mask_item.setImage(test_mask)

            if label_id is None or label_id == 0:
                print("No ROI label found nearby.")
                return

            if roi_style == "ellipse":
                position, size, angle_deg = NextGenTrackerRoutine.instance().calculate_ellipse_parameters(mask_data, label_id)

                if position is not None:
                    self.add_roi(position=position, size=size, angle_degree = angle_deg, roi_style = roi_style)

            elif roi_style == "poly_line":

                outline = NextGenTrackerRoutine.instance().get_contour_outline(mask_data, label_id)
                if outline is not None:

                    self.add_roi(roi_style = roi_style, contours= outline)

            else:
                print("Unknown ROI style")

            #
            #
            # print(f"Position (cy={position[0]}, cx={position[1]}), diameter={size}, angle={angle_deg})")
            # roi = self.rois[max(self.rois.keys())]  # Just added ROI
            # print(f"Set ROI at pos (x,y)={roi.pos()}, size (width,heigth)={roi.size()}, angle={roi.angle()}")

    ###


    # def automated_roi_search(self):
    #     """Automatically add ROIs to the current layer"""
    #
    #     NextGenTrackerRoutine.instance().start_roi_segmentation = True
    #     NextGenTrackerRoutine.instance().button_start_segmentation_clicked(self.layer_idx)


        # log.info(f'Start automated ROI search for layer {self.layer_idx}')
        # detected_rois = NextGenTrackerRoutine.instance().detect_rois(self.layer_idx)
        # print("Done: number of ROI: ", len(detected_rois))
        #
        # if detected_rois is None:
        #     return
        #
        # top_roi = sorted(detected_rois, key=lambda x: x['mean_intensity'], reverse=True)[:NextGenTrackerRoutine.instance().roi_max_num]
        #
        # for roi in top_roi:
        #     self.add_roi(center=roi['center'], diameter=roi['diameter'])

    def get_next_free_roi_index(self):
        used_indices = set(self.rois.keys())
        for i in range(NextGenTrackerRoutine.instance().roi_max_num):
            if i not in used_indices:
                return i
        return None  # All slots full

    # def toggle_mask(self, only_contours: bool = True):
    #     # Get mask for this layer, if it exists
    #     mask_dict = NextGenTrackerRoutine.instance().layer_masks
    #     masks = mask_dict.get(self.layer_idx, None)
    #
    #     if masks is not None:
    #         self.mask_visible = not self.mask_visible  # toggle state
    #         self.mask_item.setVisible(self.mask_visible)
    #
    #         if self.mask_visible:
    #             if only_contours:
    #                 mask_array = masks.get('contour_mask')
    #             else:
    #                 mask_array = masks.get('merged_mask')
    #
    #             self.mask_item.setImage(mask_array)
    #             self.toggle_mask_btn.setText("Hide ROI mask")
    #         else:
    #             self.toggle_mask_btn.setText("Show ROI mask")
    #
    #     else:
    #         QtWidgets.QMessageBox.information(
    #             self, "No Mask Found", f"No segmentation mask found for layer {self.layer_idx}."
    #         )
    def toggle_mask(self, only_contours: bool = True):
        mask_dict = NextGenTrackerRoutine.instance().layer_masks
        masks = mask_dict.get(self.layer_idx, None)


        if masks is not None:
            self.mask_visible = not self.mask_visible  # toggle visibility
            self.mask_item.setVisible(self.mask_visible)

            if self.mask_visible:
                if only_contours:
                    mask_array = masks.get('contour_mask')
                    if mask_array is not None:
                        # Convert 2D mask to red RGB image
                        red_mask = np.zeros((mask_array.shape[0], mask_array.shape[1], 3), dtype=np.uint8)
                        red_mask[mask_array > 0, 0] = 255  # Red channel

                        self.mask_item.setImage(red_mask)
                    else:
                        self.mask_item.setImage(mask_array)  # fallback if None
                else:
                    mask_array = masks.get('merged_mask')
                    self.mask_item.setImage((mask_array > 0))

                self.toggle_mask_btn.setText("Hide ROI mask")
            else:
                self.toggle_mask_btn.setText("Show ROI mask")
        else:
            QtWidgets.QMessageBox.information(
                self, "No Mask Found", f"No segmentation mask found for layer {self.layer_idx}."
            )
    def add_roi(self, position = None, size = None, angle_degree = None, roi_style = "ellipse", contours = None):
        # Get next index
        # roi_idx = len(self.rois)

        roi_idx = self.get_next_free_roi_index()
        if roi_idx is None:
            log.warning('Failed to add ROI. Maximum number of ROIs exceeded')
            return

        # if roi_idx >= NextGenTrackerRoutine.instance().roi_max_num:
        #     log.warning('Failed to add ROI. Maximum number of ROIs exceeded')
        #     return

        # if roi_idx == 0:
        if len(self.rois) == 0:
                vxui.register_with_plotter(NextGenTrackerRoutine.trigger_name(self.layer_idx),
                                       name=f'Activity trigger for layer {self.layer_idx}',
                                       axis='Trigger')

        vxui.register_with_plotter(NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx),
                                   name=f'ROI {roi_idx}', axis=f'Layer {self.layer_idx}',
                                   color=get_roi_color(roi_idx))
        vxui.register_with_plotter(f'{NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx)}_zscore',
                                   name=f'ROI {roi_idx}', axis=f'Layer {self.layer_idx} zscore',
                                   color=get_roi_color(roi_idx))

        # Add ROI
        # if position is None and size is None:
        #     pass  # valid case
        # else:
        #     assert (
        #             isinstance(position, (tuple, list)) and len(position) == 2 and
        #             all(isinstance(v, (int, float)) and 0 <= v < NextGenTrackerRoutine.instance().frame_width for v in
        #                 position) and
        #             isinstance(size, (tuple, list)) and len(size) == 2 and
        #             angle_degree is not None and isinstance(angle_degree, (int, float))
        #     ), "center must be a tuple (x, y) and diameter a number, all within image bounds"

        if roi_style == "ellipse":
            if all(v is None for v in (position, size)):
                width = NextGenTrackerRoutine.instance().frame_width
                diameter = width // 4
                center = (width // 2, width // 2)
                position = (center[0] - diameter / 2, center[1] - diameter / 2) # (0,0) #
                size = (diameter, diameter) #(30,60) #
                angle_degree = 0



            roi = EllipseRoi(self.layer_idx, roi_idx, self, (0, 0), (1, 1))
            # TODO: 24.06 --> fix here for correct layout in pyqt image
            self.image_plot.getViewBox().addItem(roi)

            print(f"position in yx: {position[1], position[0]}")
            roi.setPos((position[1], position[0]))
            roi.setSize((size[1], size[0]))
            roi.setAngle(angle_degree)

        elif roi_style == "poly_line":

            # print(f"contours: {contours}")
            roi = PolyLineRoi(self.layer_idx, roi_idx, self, points = contours)
            self.image_plot.getViewBox().addItem(roi)
            self.roi_updated(roi)

            # self.roi_updated(roi)
            # roi.setPoints()
            #roi.sigRegionChangeFinished.emit(roi)


        #TODO 27.06: to call roi_updated the self.image_plot.getViewBox().addItem(roi) needs to be added to the image first. roi_updated is initialized by the class self.sigRegionChangeFinished.connect(self.image_widget.roi_updated) --> leads to problems

        self.rois[roi_idx] = roi

        # # initialize roi_thresholds
        # thresholds = NextGenTrackerRoutine.instance().roi_thresholds
        # thresholds.setdefault((self.layer_idx, roi_idx), 1.0)  # Set default if not already set
        #
        # # initialize roi_slice_params
        # roi_slice_params = NextGenTrackerRoutine.instance().roi_slice_params
        # roi_slice_params.setdefault((self.layer_idx, roi_idx), {'slice': (0, 1)})  # Adjust default if needed

        # Add ROI threshold widget
        # thresh = widgets.DoubleSliderWidget(self.controls,
        #                                     label=f'ROI {roi_idx}',
        #                                     default=NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, roi_idx)],
        #                                     limits=(0, 50), step_size=0.1)


        #Experimental:
        label_button = QtWidgets.QPushButton(f'ROI {roi_idx}')
        label_button.setFlat(True)  # Make it look like a label
        label_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        def context_menu_handler(_):
            self.delete_specific_roi(roi_idx)

        label_button.customContextMenuRequested.connect(context_menu_handler)

        self.controls.layout().addWidget(label_button, roi_idx, 0)

        # Add threshold slider (now at column 1)
        thresh = widgets.DoubleSliderWidget(self.controls,
                                            default=NextGenTrackerRoutine.instance().roi_thresholds[
                                                (self.layer_idx, roi_idx)],
                                            limits=(0, 50), step_size=0.1)
        thresh.connect_callback(roi.update_threshold)
        self.controls.layout().addWidget(thresh, roi_idx, 1)
        thresh.connect_callback(roi.update_threshold)

        # self.rois.append(roi)
        # self.threshold_widgets.append(thresh)

        self.threshold_widgets[roi_idx] = thresh

        roi.label_button = label_button

        # self.controls.layout().addWidget(thresh, roi_idx, 0)
        # self.scroll_layout.addWidget(thresh, roi_idx, 0) #<-- changed for new layout

    #Experimental:
    def delete_specific_roi(self, roi_idx: int):
        # Find ROI by index
        # roi = next((r for r in self.rois if r.idx == roi_idx), None)
        # roi = self.rois.get(roi_idx, None)
        roi = self.rois.pop(roi_idx, None)

        if roi is None:
            log.warning(f"ROI {roi_idx} not found")
            return

        self.image_plot.getViewBox().removeItem(roi)
        self.image_plot.removeItem(roi.label)

        # Remove threshold widget

        thresh_widget = self.threshold_widgets.pop(roi_idx, None)
        if thresh_widget:
            self.controls.layout().removeWidget(thresh_widget)
            thresh_widget.deleteLater()

        # if roi_idx < len(self.threshold_widgets):
        #     thresh_widget = self.threshold_widgets[roi_idx]
        #     self.controls.layout().removeWidget(thresh_widget)
        #     thresh_widget.deleteLater()
        #     self.threshold_widgets[roi_idx] = None

        # Remove button
        if hasattr(roi, "label_button"):
            self.controls.layout().removeWidget(roi.label_button)
            roi.label_button.deleteLater()

        # Clean up internal state
        # self.rois = [r for r in self.rois if r.idx != roi_idx]

        # NextGenTrackerRoutine.instance().roi_slice_params.pop((self.layer_idx, roi_idx), None)
        # NextGenTrackerRoutine.instance().roi_thresholds.pop((self.layer_idx, roi_idx), None)
        # NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi_idx)] = (None, ()) #()
        del NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi_idx)]

        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, roi_idx)] = 2000 ## TODO: check why this value is initialized in Nextgentrackerroutine.require ...

        vxui.remove_from_plotter(NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx),
                                 axis=f'Layer {self.layer_idx}')
        vxui.remove_from_plotter(f'{NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx)}_zscore',
                                 axis=f'Layer {self.layer_idx} zscore')

        log.info(f"Deleted ROI {roi_idx} from layer {self.layer_idx}")



    # def roi_updated(self, roi: Union[Roi, PolyLineRoi]): #Union[Roi, PolyLineRoi]
    #     log.debug(f'Update ROI for layer {self.layer_idx}')
    #     slice_params = roi.getAffineSliceParams(self.image_item.image, self.image_item) #, fromBoundingRect=True
    #     print(f"slice_params: {slice_params}, self.layer_idx: {self.layer_idx}, roi.idx: {roi.idx}")
    #     NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi.idx)] = slice_params
    #     print(f"all slice_params: {NextGenTrackerRoutine.instance().roi_slice_params}")

    # def roi_updated(self, roi: Union[Roi, PolyLineRoi]):
    #     log.debug(f'Update ROI for layer {self.layer_idx}')
    #
    #     if isinstance(roi, PolyLineRoi):
    #         points = roi.getState()['points']
    #         NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi.idx)] = ('polyline_points', points)
    #     else:
    #         slice_params = roi.getAffineSliceParams(self.image_item.image, self.image_item)
    #         NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi.idx)] = ('affine_slice',
    #                                                                                         slice_params)

    #TODO: double check if this works for changed ROI (not new roi)
    def roi_updated(self, roi: Union[EllipseRoi, PolyLineRoi]):
        log.debug(f'Update ROI for layer {self.layer_idx}')

        if isinstance(roi, PolyLineRoi):
            points = roi.getState()['points']
            roi_instance = ROI(mode='polyline_points', params=points,layer_idx = self.layer_idx)
        elif isinstance(roi, EllipseRoi):
            slice_params = roi.getAffineSliceParams(self.image_item.image, self.image_item)
            roi_instance = ROI(mode='affine_slice', params=slice_params,layer_idx = self.layer_idx)
        else:
            raise ValueError(f"Invalid roi type: {type(roi)}")

        roi_instance.calculate_center(image_frame=np.zeros((ScanImageFrameReceiverTcpServer.instance().frame_height, ScanImageFrameReceiverTcpServer.instance().frame_width)))
        roi_instance.calculate_z()
        roi_instance.tracked = True

        NextGenTrackerRoutine.instance().roi_slice_params[(self.layer_idx, roi.idx)] = roi_instance


    def reset(self):

        # for roi_idx in range(len(self.rois)):
        for roi_idx in list(self.rois.keys()):
            vxui.remove_from_plotter(NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx),
                                     axis=f'Layer {self.layer_idx}')
            vxui.remove_from_plotter(f'{NextGenTrackerRoutine.roi_name(self.layer_idx, roi_idx)}_zscore',
                                     axis=f'Layer {self.layer_idx} zscore')


# class EllipseRoi(pg.EllipseROI):
#
#     def __init__(self, layer_idx: int, idx: int, image_plot: ImagePlot, *args, **kwargs):
#         # pg.RectROI.__init__(self, *args, sideScalers=True, **kwargs)
#         pg.EllipseROI.__init__(self, *args, **kwargs)
#         self.layer_idx = layer_idx
#         self.idx = idx
#         self.image_plot = image_plot
#
#         self.sigRegionChangeFinished.connect(self.image_plot.roi_updated)
#         self.setPen(pg.mkPen(color=get_roi_color(self.idx)))
#         self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
#         self.label.setAnchor((0, 1))
#         self.image_widget.image_plot.addItem(self.label)
#
#         self.sigRegionChanged.connect(self.position_changed)
class EllipseRoi(pg.EllipseROI):
    def __init__(self, layer_idx: int, idx: int, image_plot: ImagePlot, update_callback: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot
        self.update_callback = update_callback  # ✅ Store the callback

        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))

        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.label.setAnchor((0, 1))
        self.image_plot.plot_item.addItem(self.label)

        self.label_visible = True

        # 🔁 Call the central callback when ROI is done changing
        self.sigRegionChangeFinished.connect(self._notify_parent)
        self.sigRegionChanged.connect(self._update_label_position)
        self._update_label_position()  # Set initial position


    def _notify_parent(self):
        if self.update_callback:
            self.update_callback(self, self.layer_idx, self.image_plot)

    def _update_label_position(self):
        """Reposition the label to match the top center of the ellipse."""
        pos = self.pos()
        size = self.size()
        center_x = pos.x() + size.x() / 2
        center_y = pos.y()  # Top of the ellipse
        self.label.setPos(center_x, center_y)

    def set_visible(self):
        self.label.setVisible(True)
        self.setVisible(True)

    def set_invisible(self):
        self.label.setVisible(False)
        self.setVisible(False)

    def position_changed(self, roi: EllipseRoi):
        self.label.setPos(roi.pos())

    def update_threshold(self, value: int):
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value


class PolyLineRoi(pg.PolyLineROI):

    def __init__(self, layer_idx: int, idx: int, image_plot: ImagePlot, points: list, closed: bool =True, **kwargs):
        super().__init__(points, closed=closed, **kwargs)
        self.layer_idx = layer_idx
        self.idx = idx
        self.image_plot = image_plot

        # self.sigRegionChangeFinished.connect(self.image_widget.roi_updated) ### ??? makes sense here ?
        self.setPen(pg.mkPen(color=get_roi_color(self.idx), width=2))


        self.label = pg.TextItem(f'ROI {self.idx}', color=get_roi_color(self.idx))
        self.image_plot.plot_item.addItem(self.label)
        self.set_label_center()

        # Show/hide toggle support
        self.label_visible = True

    def set_visible(self):
        self.setVisible(True)
        if self.label_visible:
            self.label.setVisible(True)

    def set_invisible(self):
        self.setVisible(False)
        self.label.setVisible(False)

    def toggle_label(self, visible: bool = None):
        """Toggle label visibility. If `visible` is None, toggle current state."""
        if visible is None:
            self.label_visible = not self.label_visible
        else:
            self.label_visible = visible
        self.label.setVisible(self.label_visible and self.isVisible())

    def set_label_center(self):
        """Place the label at the centroid of the polygon."""
        pts = self.getState()['points']
        if not pts:
            return
        x_coords, y_coords = zip(*pts)
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        self.label.setPos(centroid_x, centroid_y)

    def set_visible(self):
        self.label.setVisible(True)
        self.setVisible(True)

    def set_invisible(self):
        self.label.setVisible(False)
        self.setVisible(False)

    # def position_changed(self):
    #     self.label.setPos(self.pos())

    def update_threshold(self, value: int):
        NextGenTrackerRoutine.instance().roi_thresholds[(self.layer_idx, self.idx)] = value

#TODO: overall Problems and ideas:
# Problem:
# -- roi seem to be slightly shifted in their position
# -- freezing of everything during automatic cell segmentation ....
# -- look at threshold initialization and scaling
# -- Check if polyline and ellipse activity is calculated the same way + if poly line roi is moved not change in signal (not updated positions ?) --> error in polyline activity tracking .... (01.07)
# Ideas:
# -- More customizable widget with more refine options (mean vs max stack (+number of frames), number of ROI to detect, ROI selection criterion (max intensity vs dynamical properties)...)
# -- Fix and overwork some of the quality meassurements (eg. normalized roi threshold slider)
# -- Add tuning curves later on in the maybe to stimuli
# -- better widget layout (removable ROI/ remove all roi)
# -- Automatic intensity threshold selection (maybe even an local/ adaptive threshold?)
# -- Increase addon window size for better image visualization (where is this created??)
# -- check handling of combining automated search and manual adding roi
# -- make roi detectable via elipses (--> holographic stimulation) and pyqtgraph line roi detection (PolyLineROI)



#Comment from 26.06 : I changed the x,y click coordinates back to the original (now the image is flipped again)
#New traceback error appeared in ellipse handling (        self.image_plot.getViewBox().addItem(roi) was moved ? maybe need to be done before setting size etc. )

