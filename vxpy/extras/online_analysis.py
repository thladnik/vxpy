from __future__ import annotations
from functools import partial
import os
from typing import Dict, Tuple, Type, Optional, Any
import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import matplotlib as mpl
import copy
import time
from collections import deque

import vxpy.core.attribute as vxattribute
import vxpy.core.event as vxevent
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.utils import widgets
from vxpy.extras.server import ScanImageFrameReceiverTcpServer
from vxpy.extras.ca_processing_2nd_gen import NextGenTrackerRoutine, BaseROI, GeneralEllipseROI, GeneralPolylineROI



def get_roi_color(index: int) -> tuple[int, int, int]:
    """Return an RGB color tuple (r, g, b) from matplotlib tab10 colormap."""
    color = np.array(mpl.colormaps['tab10'](index % 10)[:3]) * 255
    return tuple(color.astype(np.uint8))

def safe_read_attribute(name, **kwargs):
    data = vxattribute.read_attribute(name, **kwargs)
    if data is None:
        return None, None, None
    return data


#TODO: Ideally make this private attribute of the OnlineAnalysisRoutine class (but not a shared dictionary)
OnlineAnalysisRoutine_engine_instances : dict[str, AnalysisEngine] ={}


class OnlineAnalysisRoutine(vxroutine.WorkerRoutine):

    online_frame_name: str = 'roi_activity_tracker_frame'    # Base name for output frames for attribute file

    new_rois_set = False
    loaded_new_rois = True
    current_layer_num = -1
    new_metadata = False  # ?
    analysis_type = "live"
    roi_label_to_idx = []
    min_pixels = 0
    max_rois_tracked = 10
    roi_idx_assignments = {}
    roi_idx_assignments_selected = []
    rois_to_analyse: dict[tuple[int, int], "BaseROI"] = {}
    rois_to_laser : dict[tuple[int, int], "BaseROI"] = {}
    update_roi_selection = False
    number_of_layers = None



    current_engine_name: str = "Basic Stats"
    engine_switch = False
    update_engine_params = False
    current_engine_parameters = {}





    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Store rolling compute durations for performance monitoring ---
        self._frame_times = deque(maxlen=30)
        self._incoming_frame_intervals = deque(maxlen=30)
        self._last_frame_time = None



        # self.engine_instances : dict[str, AnalysisEngine] ={}
        self.engine_parameters: dict[str, dict] = {}


        print(f'[OnlineAnalysisRoutine] Initializing worker: process ID: {os.getpid()}, dict_type: {type(OnlineAnalysisRoutine_engine_instances)}')
        for name, (engine_cls, _, _) in ANALYSIS_REGISTRY.items():
            engine = engine_cls(max_rois=self.max_rois_tracked)
            OnlineAnalysisRoutine_engine_instances[name] = engine
            print(f"[WORKER] Created engine for {name}: Engine {engine}, id: {id(engine)} in dict: {OnlineAnalysisRoutine_engine_instances[name]} "f"(id={id(OnlineAnalysisRoutine_engine_instances[name])}) "f"PID: {os.getpid()}, PPID: {os.getppid()}")
            # Make a copy of the engine default parameters for tracking/updating
            # self.engine_parameters[name] = dict(self.engine_instances[name].engine_parameters)

        for name in test_engine_instances.keys():
            print(f"[WORKER]1 Stored engine {name}: {test_engine_instances[name]} (id={id(test_engine_instances[name])})")

        for name in test_engine_instances.keys():
            print(f"[WORKER]2 Stored engine {name}: {test_engine_instances[name]} (id={id(test_engine_instances[name])})")

        for name in test_engine_instances.keys():
            print(f"[WORKER]3 Stored engine {name}: {test_engine_instances[name]} (id={id(test_engine_instances[name])})")

        for name in test_engine_instances.keys():
            print(f"[WORKER]4 Stored engine {name}: {test_engine_instances[name]} (id={id(test_engine_instances[name])})")


        # Default engine
        self.current_engine_name = list(ANALYSIS_REGISTRY.keys())[0]
        self.current_engine = OnlineAnalysisRoutine_engine_instances[self.current_engine_name]
        self.current_engine_parameters.update(self.current_engine.engine_parameters)





    def main(self, *args, **kwargs):
        """
        Main routine loop.
        """


        if self.new_rois_set:
            self._pull_data()
            print(
                f"[OnlineAnalysisRoutine] [pull_data_clicked_worker_routine] Routine id: {id(self)} object id: {id(self.rois_to_analyse)}, ROIs: {len(self.rois_to_analyse)}")

            self.new_rois_set = False

        if self.engine_switch:
            print(f"[OnlineAnalysisRoutine] [engine_switch] Old engine parameters {self.current_engine_parameters}")
            self._switch_engine()
            self.engine_switch = False
            print(f"[OnlineAnalysisRoutine] [engine_switch] New engine parameters {self.current_engine_parameters}")

        if self.update_engine_params:
            # Update current engine's parameters
            print(f'[OnlineAnalysisRoutine] Previous engine params: {self.current_engine.engine_parameters}')

            print(f'[OnlineAnalysisRoutine] Updating engine parameters to : {self.current_engine_parameters}')
            self.current_engine.update_engine_parameters(self.current_engine_parameters)
            self.update_engine_params = False

        if self.update_engine_params:
            try:
                # Fetch the engine instance by name
                engine = OnlineAnalysisRoutine_engine_instances.get(self.current_engine_name, None)
                if engine is None:
                    print(f"[ERROR] Unknown engine: {self.current_engine_name}")
                else:
                    # Optional: validate keys exist in engine.engine_parameters
                    invalid_keys = set(self.current_engine_parameters) - set(engine.engine_parameters)
                    if invalid_keys:
                        print(f"[WARN] Invalid engine parameter keys: {invalid_keys}")

                        print(f'[OnlineAnalysisRoutine] Previous engine params: {engine.engine_parameters}')

                    # Update parameters
                    engine.update_engine_parameters(self.current_engine_parameters)
                    print(
                        f"[OnlineAnalysisRoutine] Updated '{self.current_engine_name}' engine parameters: {self.current_engine_parameters}")
            except Exception as e:
                print(f"[ERROR] Failed to update engine parameters: {e}")

            self.update_engine_params = False

        if self.update_roi_selection:
            self._update_laser_rois()
            self.update_roi_selection = False


        pass


    def initialize(self) -> None:
        """
        Set up runtime triggers to start processing incoming frames.
        """


        # engine_names = list(ANALYSIS_REGISTRY.keys())
        # engine_1_class, _ , _ = ANALYSIS_REGISTRY[engine_names[0]]
        # self.engine1 = engine_1_class(max_rois=self.max_rois_tracked)
        # print(f"[WORKER] Created engine for {engine_names[0]}: Engine {self.engine1}, id: {id(self.engine1)} "f"PID: {os.getpid()}, PPID: {os.getppid()}")
        #
        #
        # engine_2_class, _, _ = ANALYSIS_REGISTRY[engine_names[1]]
        # self.engine2 = engine_2_class(max_rois=self.max_rois_tracked)
        # print(f"[WORKER] Created engine for {engine_names[1]}: Engine {self.engine2}, id: {id(self.engine2)} "f"PID: {os.getpid()}, PPID: {os.getppid()}")




        if self.analysis_type == "live":

            # Trigger fires whenever a new scanimage frame is available
            print("[initialize] Setting up live frame trigger")
            self.trigger = vxevent.NewDataTrigger('scanimage_frame', callback=self._process_live_frame)
            self.trigger.set_active()  # Enable trigger immediately

        elif self.analysis_type == "file":
            #TODO: Implement from file
            pass

    def _process_live_frame(self, last_idx, last_time, last_frame) -> None:
        """
        Process the last acquired input frame, update ROI activity, and handle evaluation.

        Args:
            last_idx (int): Index of the last received frame.
            last_time (float): Timestamp of the last received frame.
            last_frame (np.ndarray): Raw frame data from the acquisition.
        """

        if self._last_frame_time is not None:
            self._incoming_frame_intervals.append(last_time - self._last_frame_time)

        self._last_frame_time = last_time
        start = time.perf_counter()




        # Get current layer number from the ScanImageFrame server
        layer_num = ScanImageFrameReceiverTcpServer.instance().layer_num


        if self.current_layer_num != layer_num:
            self.new_metadata = True
            self.current_layer_num = layer_num


        # Retrieve the last frame index from system attributes
        _, _, last_frame_index = vxattribute.get_attribute('scanimage_frame_index')[int(last_idx)]

        # Ensure frame is float64 for consistent processing
        last_frame = last_frame.astype(np.float64)

        # -------------------- Get preprocessed Frame --------------------

        # Read preprocessed frame from the attribute corresponding to the current layer
        current_layer_idx = int(last_frame_index) % ScanImageFrameReceiverTcpServer.instance().layer_num # TODO: Check this

        frame_index , frame_time, preprocessed_frame = vxattribute.read_attribute(f'{self.online_frame_name}_{current_layer_idx}')

        for assigned_idx, (layer_idx, roi_idx) in self.roi_idx_assignments.items():
            roi = self.rois_to_analyse[(layer_idx, roi_idx)]

            # Skip if not the current layer or ROI not defined
            if layer_idx != current_layer_idx or roi.reference_frame_shape is None:
                continue

            if np.sum(roi.pixel_mask) < self.min_pixels:
                continue

            if (assigned_idx, roi.roi_idx) not in self.roi_label_to_idx:
                self.roi_label_to_idx.append((assigned_idx, roi.roi_idx))

            for name in OnlineAnalysisRoutine_engine_instances.keys():
                # print(f"[WORKER] Use engine {name}:  (id= / {test_engine_instances[name]} (id={id(test_engine_instances[name])})")

                OnlineAnalysisRoutine_engine_instances[name].compute(preprocessed_frame.squeeze(), roi, assigned_idx, frame_time, frame_index)


        # =====================================
        # PERFORMANCE CHECK (minimal)
        # =====================================

        elapsed = time.perf_counter() - start
        self._frame_times.append(elapsed)

        avg_compute_time = sum(self._frame_times) / len(self._frame_times)

        if len(self._incoming_frame_intervals) > 0:
            incoming_period = sum(self._incoming_frame_intervals) / len(self._incoming_frame_intervals)

            # # --- SANITY PRINT EVERY FRAME ---
            # print(f"[perf] compute_time={elapsed:.4f}s  avg_compute_time={avg_compute_time:.4f}s  "
            #       f"incoming_period={incoming_period:.4f}s")


            if avg_compute_time > incoming_period:
                print(f"[WARN] Analysis slower ({avg_compute_time:.4f}s > {incoming_period:.4f}s)")



    def require(self) -> None:


        # self.engine.set_up_attribute_tracking()
        pass

    def _pull_data(self):
        """
        Pull ROI snapshot from tracker and send it to this routine.
        """
        self.rois_to_analyse.clear()
        self.rois_to_analyse.update(copy.deepcopy(NextGenTrackerRoutine.instance().rois_to_analyse))
        self.roi_idx_assignments.clear()
        del self.roi_idx_assignments_selected[:]

        assigned_count = 0  # separate counter for valid ROIs

        for (layer_idx, roi_idx) in self.rois_to_analyse.keys():
            if assigned_count >= self.max_rois_tracked:
                print(
                    f"[pull_data] Warning: Maximum number of ROIs ({self.max_rois_tracked}) reached, skipping remaining ROIs"
                )
                break

            if np.sum(self.rois_to_analyse[(layer_idx, roi_idx)].pixel_mask) < self.min_pixels:
                print(f"[pull_data] ROI {layer_idx}_{roi_idx} has less than {self.min_pixels} pixels, skipping")
                continue

            # dict version
            self.roi_idx_assignments[assigned_count] = (layer_idx, roi_idx)
            # list version
            self.roi_idx_assignments_selected.append(True)


            assigned_count += 1

        print(f"[pull_data] {self.roi_idx_assignments} selected: {self.roi_idx_assignments}")

        self.loaded_new_rois=True

        self.number_of_layers = copy.copy(NextGenTrackerRoutine.instance().current_layer_num)

        self.update_roi_selection = True

    def _update_laser_rois(self):
        self.rois_to_laser.clear()

        for i in range(len(self.roi_idx_assignments_selected)):
            if self.roi_idx_assignments_selected[i] == False :
                continue
            elif self.roi_idx_assignments_selected[i] == True:
                (layer_idx, roi_idx) = self.roi_idx_assignments[i]
                self.rois_to_laser[(layer_idx, roi_idx)] = self.rois_to_analyse[(layer_idx, roi_idx)]

    def _switch_engine(self):
        if self.current_engine_name not in test_engine_instances.keys():
            raise ValueError(f"Unknown engine {self.current_engine_name}")
        # self.current_engine_name = engine_name
        self.current_engine = test_engine_instances[self.current_engine_name]
        self.current_engine_parameters.clear()
        self.current_engine_parameters.update(self.current_engine.engine_parameters)

        print(f'[OnlineAnalysisRoutine] Switching engine to : {self.current_engine_name} with parameters: {self.current_engine_parameters}')


# ---------------------------------------------------------------------
# Base class for per-ROI analysis widgets
# ---------------------------------------------------------------------
# class BaseAnalysisWidget(QtWidgets.QWidget):
#     """
#     Widget to create plots for a single ROI.
#     Subclassed to create specific analysis plots for the corresponding Engine.
#     """
#
#     _analysis_engine: AnalysisEngine = None
#     _settings_widget: BaseSettingsWidget = None
#
#     def __init__(
#         self,
#         roi_key: ROIKey,
#         parent: Optional[QtWidgets.QWidget] = None,
#         color: Optional[tuple[int, int, int]] = None,
#     ):
#         super().__init__(parent)
#         self.roi_key = roi_key
#         self.index: Optional[int] = None
#         self.color = tuple(int(c) for c in (color or (0, 0, 255)))  # default blue
#         self.widget_parameters = {}  # Parameters controlled by settings widget
#
#         # Default pens for active/inactive display
#         self._pen_active = pg.mkPen(color=self.color, width=2)
#         self._pen_inactive = pg.mkPen(color=(180, 180, 180, 150), width=1)  # semi-transparent grey
#
#         # # Maintain a list of all plot items in this widget
#         # self.plot_items: list = []
#
#         self.plot_widgets: list[pg.PlotWidget] = []
#         self.plot_layout = QtWidgets.QVBoxLayout(self)
#         self._build_plots()
#
#
#         self._last_updated_index = None
#
#         self._build_ui()
#
#     def _build_ui(self) -> None:
#         self.main_layout = QtWidgets.QHBoxLayout(self)
#
#         # # Label
#         # self.label = QtWidgets.QLabel(f"ROI {self.roi_key}")
#         # self.main_layout.addWidget(self.label)
#
#         # Plot container
#         self.plot_container = QtWidgets.QWidget()
#         self.plot_layout = QtWidgets.QVBoxLayout(self.plot_container)
#         self.plot_layout.setContentsMargins(0, 0, 0, 0)
#         self.main_layout.addWidget(self.plot_container, 1)
#
#         # Let subclass populate plots
#         self._build_plot()
#
#     def _build_plot(self):
#         """Subclasses must implement this to populate plot_container and add plots to self.plot_items"""
#         raise NotImplementedError
#
#     def set_active(self, active: bool):
#         """Change color/appearance of all plot items in this widget"""
#         for plot_item in self.plot_items:
#             print(f"set_active: {plot_item.name} active: {active}, pen: {self._pen_active if active else self._pen_inactive}")
#             plot_item.setPen(self._pen_active if active else self._pen_inactive)
#
#     def update_settings(self, settings_parameter_dict: dict):
#         self.widget_parameters = settings_parameter_dict
#
#
#     def update_from_data(self) -> None:
#         #TODO: couple this to the output of the corresponding AnalysisEngine data shaped that is provided
#         raise NotImplementedError()
#
#     def attribute_name_for(self, index: int, mode: str) -> str:
#         """
#         """
#         return f"roi_{index}_{mode}"
#
#
# # ---------------------------------------------------------------------
# # Concrete implementation: BasicStatsWidget
# # ---------------------------------------------------------------------
# ROIKey = Tuple[int, int]  # (layer_idx, roi_idx)
#
# class BasicStatsWidget(BaseAnalysisWidget):
#     '''Subclass used for basic statistics that can be used with only flourescent image streams'''
#
#     _analysis_engine : Type[BasicStatsEngine]
#     _settings_widget : BasicStatsSettingsWidget
#
#     def _build_plot(self):
#         self.plot_widget = pg.PlotWidget()
#         self.plot_widget.setBackground("w")
#         self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
#
#         # Pen colors
#         self._pen_active = pg.mkPen(color=self.color, width=2)
#         self._pen_inactive = pg.mkPen(color=(180, 180, 180), width=1)
#
#         # Plot item
#         self.plot_item = self.plot_widget.plot(pen=self._pen_active)
#         self.plot_items.append(self.plot_item)  # <-- add to list for Base class handling
#
#         self.plot_layout.addWidget(self.plot_widget)
#
#
#
#     def update_from_data(self) -> None:
#         """Always update the data, regardless of active state."""
#
#         attr_name = self.attribute_name_for(self.index, self.widget_parameters["mode"])
#         try:
#             data = vxattribute.read_attribute(attr_name, last=self.widget_parameters["timeframe"])
#         except Exception:
#             data = None
#
#         indices, times, values = data
#         times = np.array(times, dtype=float)
#         values = np.array(values, dtype=float).flatten()
#
#         self.plot_item.setData(times, values)
#         self.plot_widget.setTitle(f"{self.roi_key}_{self.widget_parameters['mode']}")
#
# class TuningCurveWidget(BaseAnalysisWidget):
#     """Widget for plotting eye-position tuning curves (df/f vs left/right eye angle)."""
#
#     _analysis_engine: Type[EyeTuningCurveEngine]
#     _settings_widget: Type[TuningCurveSettingsWidget]
#
#     widget_parameters = {
#         "timeframe": 100,  # fallback, if needed
#         "use_regression": False,  # whether to fit a regression line
#         "df_f_threshold": 0.02,  # exclude df/f points below this value
#         "piecewise": False  # whether to use piecewise linear regression
#     }
#
#     test_old_idx = -1
#
#     def _build_plot(self):
#         self.plot_widget = pg.PlotWidget()
#         self.plot_widget.setBackground("w")
#         self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
#         self.plot_widget.setLabel('bottom', 'Eye Position', units='deg')
#         self.plot_widget.setLabel('left', 'ΔF/F')
#
#         # Scatter plot items (one per eye)
#         self.scatter_left = pg.ScatterPlotItem(
#             pen=pg.mkPen(self.color),
#             brush=pg.mkBrush(*self.color, 120),
#             size=8,
#             name='Left Eye'
#         )
#         self.scatter_right = pg.ScatterPlotItem(
#             pen=pg.mkPen(self.color),
#             brush=pg.mkBrush(*self.color, 120),
#             size=8,
#             name='Right Eye'
#         )
#         self.plot_widget.addItem(self.scatter_left)
#         self.plot_widget.addItem(self.scatter_right)
#         self.plot_items.extend([self.scatter_left, self.scatter_right])
#
#         # Regression lines
#         self.line_left = pg.PlotDataItem(pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
#         self.line_right = pg.PlotDataItem(pen=pg.mkPen('b', width=2, style=QtCore.Qt.DashLine))
#         # Optional second lines for piecewise regression
#         self.line_left2 = pg.PlotDataItem(pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))
#         self.line_right2 = pg.PlotDataItem(pen=pg.mkPen('b', width=2, style=QtCore.Qt.DashLine))
#
#         self.plot_widget.addItem(self.line_left)
#         self.plot_widget.addItem(self.line_right)
#         self.plot_widget.addItem(self.line_left2)
#         self.plot_widget.addItem(self.line_right2)
#         self.plot_items.extend([self.line_left, self.line_right, self.line_left2, self.line_right2])
#
#         # Threshold line
#         self.threshold_line = pg.InfiniteLine(
#             pos=0.0,
#             angle=0,
#             pen=pg.mkPen(color=(180, 180, 180), style=QtCore.Qt.DashLine)
#         )
#         self.plot_widget.addItem(self.threshold_line)
#         self.plot_items.append(self.threshold_line)
#
#         # Add the plot widget to the layout
#         self.plot_layout.addWidget(self.plot_widget)
#
#     def update_from_data(self) -> None:
#         """Update the tuning curve plot from the engine's output data."""
#
#         tracking_index = self.index
#         threshold = self.widget_parameters.get("df_f_threshold", 0.0)
#         use_regression = self.widget_parameters.get("linear_regression", True)
#         piecewise = self.widget_parameters.get("piecewise_regression", False)
#
#         try:
#             # Retrieve object attribute containing epoch-based data
#             attr_name_epoch = f"roi_{tracking_index}_f0_epoch"
#             epoch_indices, _, epoch_data = safe_read_attribute(attr_name_epoch, last=1)
#
#             if epoch_indices and hasattr(epoch_indices, '__getitem__'):
#                 if epoch_indices[0] != self.test_old_idx:
#                     print(
#                         f'[Tuning Curve Widget]: datalist for {attr_name_epoch}: idx: {epoch_indices}, Data: {epoch_data}')
#                     self.test_old_idx = epoch_indices[0]
#
#                     print(f"[Tuning Curve Widget]: We should read indexes from: {epoch_data[-1]['index']}")
#                 else:
#                     print(f'[Tuning Curve Widget]: datalist for {attr_name_epoch}:idx: {epoch_indices}')
#
#             if not len(epoch_indices):
#                 return
#
#             from_idx = epoch_data[-1]['index']
#
#             attr_name_df = f"roi_{tracking_index}_df/f"
#             df_indices, df_times, df_data_list = safe_read_attribute(attr_name_df, from_idx = from_idx)
#             df_f = df_data_list
#
#             attr_name_left_eye = f"roi_{tracking_index}_left_eye"
#             left_eye_indices, left_eye_times, left_eye_data_list = safe_read_attribute(attr_name_left_eye, from_idx = from_idx)
#             left_eye = left_eye_data_list
#
#             attr_name_right_eye = f"roi_{tracking_index}_right_eye"
#             right_eye_indices, right_eye_times, right_eye_data_list = safe_read_attribute(attr_name_right_eye, from_idx = from_idx)
#             right_eye = right_eye_data_list
#
#             df_f = np.array(df_f).squeeze()
#             left_eye = np.array(left_eye).squeeze()
#             right_eye = np.array(right_eye).squeeze()
#
#
#             if len(left_eye) == 0:
#                 return
#
#             # Determine colors based on threshold
#             colors_left = [
#                 self.color if val >= threshold else (180, 180, 180)
#                 for val in df_f
#             ]
#             colors_right = [
#                 self.color if val >= threshold else (180, 180, 180)
#                 for val in df_f
#             ]
#
#             # Update scatter plots
#             self.scatter_left.setData(left_eye, df_f, brush=colors_left, pen=self._pen_active)
#             self.scatter_right.setData(right_eye, df_f, brush=colors_right, pen=self._pen_active)
#
#             # Draw threshold line
#             self.threshold_line.setValue(threshold)
#
#             # Optional regression on points above threshold
#             if use_regression:
#                 mask = df_f >= threshold
#
#                 if piecewise:
#                     #TODO: make piecewise regression better
#                     # Piecewise linear regression (2 segments)
#                     mid_idx = len(df_f[mask]) // 2
#                     if mid_idx > 1:
#                         coeffs_l1 = np.polyfit(left_eye[mask][:mid_idx], df_f[mask][:mid_idx], 1)
#                         coeffs_l2 = np.polyfit(left_eye[mask][mid_idx:], df_f[mask][mid_idx:], 1)
#                         x_l = np.linspace(np.min(left_eye[mask]), np.max(left_eye[mask]), 100)
#                         self.line_left.setData(
#                             x_l[:50], np.polyval(coeffs_l1, x_l[:50])
#                         )
#                         self.line_left2.setData(
#                             x_l[50:], np.polyval(coeffs_l2, x_l[50:])
#                         )
#
#                         coeffs_r1 = np.polyfit(right_eye[mask][:mid_idx], df_f[mask][:mid_idx], 1)
#                         coeffs_r2 = np.polyfit(right_eye[mask][mid_idx:], df_f[mask][mid_idx:], 1)
#                         x_r = np.linspace(np.min(right_eye[mask]), np.max(right_eye[mask]), 100)
#                         self.line_right.setData(x_r[:50], np.polyval(coeffs_r1, x_r[:50]))
#                         self.line_right2.setData(x_r[50:], np.polyval(coeffs_r2, x_r[50:]))
#                 else:
#                     if np.sum(mask) > 1:
#                         coeffs_l = np.polyfit(left_eye[mask], df_f[mask], 1)
#                         x_l = np.linspace(np.min(left_eye[mask]), np.max(left_eye[mask]), 100)
#                         self.line_left.setData(x_l, np.polyval(coeffs_l, x_l))
#
#                         coeffs_r = np.polyfit(right_eye[mask], df_f[mask], 1)
#                         x_r = np.linspace(np.min(right_eye[mask]), np.max(right_eye[mask]), 100)
#                         self.line_right.setData(x_r, np.polyval(coeffs_r, x_r))
#
#             self.plot_widget.setTitle(f"ROI {tracking_index} ({self.roi_key}) - Eye Tuning Curve")
#
#         except Exception as e:
#             print(f"[TuningCurveWidget] Failed to update: {e}")



ROIKey = Tuple[int, int]  # (layer_idx, roi_idx)

# ---------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------
class BaseAnalysisWidget(QtWidgets.QWidget):
    """
    Widget to create plots for a single ROI.
    Subclassed to create specific analysis plots for the corresponding Engine.
    Supports multiple independent PlotWidgets.
    """

    # _analysis_engine: AnalysisEngine = None
    # _settings_widget: BaseSettingsWidget = None

    def __init__(
        self,
        roi_key: ROIKey,
        parent: Optional[QtWidgets.QWidget] = None,
        color: Optional[tuple[int, int, int]] = None,
    ):
        super().__init__(parent)
        self.roi_key = roi_key
        self.index: Optional[int] = None
        self.color = tuple(int(c) for c in (color or (0, 0, 255)))
        self.widget_parameters: dict = {}

        # Default pens for active/inactive display
        self._pen_active = pg.mkPen(color=self.color, width=2)
        self._pen_inactive = pg.mkPen(color=(180, 180, 180, 150), width=1)

        # Containers for plots
        self.plot_widgets: list[pg.PlotWidget] = []
        self.plot_items: list[list] = []

        # One main layout for this widget
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Container widget for plots
        self.plot_container = QtWidgets.QWidget()
        self.plot_layout = QtWidgets.QHBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.plot_container)

        # Let subclass populate plots
        self._build_plot()

        self._last_updated_index = None

        # Set a uniform initial height
        self.set_fixed_height(120)

    def set_fixed_height(self, height: int):
        """Sets the normal height and applies it."""
        self._normal_height = height
        self.setFixedHeight(height)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """Toggle widget height on double-click"""
        if self._normal_height is None:
            return super().mouseDoubleClickEvent(event)

        if self._expanded:
            self.setFixedHeight(self._normal_height)
        else:
            self.setFixedHeight(self._normal_height * 2)
        self._expanded = not self._expanded
        event.accept()

    def _build_ui(self):
        self.main_layout = QtWidgets.QHBoxLayout(self)

        # Plot container
        self.plot_container = QtWidgets.QWidget()
        self.plot_layout = QtWidgets.QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.plot_container, 1)

        # Subclass populates plots
        self._build_plot()

    def _build_plot(self):
        """Subclasses must implement this to populate self.plot_widgets and self.plot_items"""
        raise NotImplementedError

    def set_active(self, active: bool):
        """Change appearance of all plot items"""
        for items in self.plot_items:
            for item in items:
                if hasattr(item, "setPen"):
                    item.setPen(self._pen_active if active else self._pen_inactive)

    def update_settings(self, settings_parameter_dict: dict):
        self.widget_parameters = settings_parameter_dict

    def update_from_data(self) -> None:
        """Subclasses must implement data update logic"""
        raise NotImplementedError()

    def attribute_name_for(self, index: int, mode: str) -> str:
        return f"roi_{index}_{mode}"


# ---------------------------------------------------------------------
# BasicStatsWidget
# ---------------------------------------------------------------------
class BasicStatsWidget(BaseAnalysisWidget):
    """Single-plot widget for basic statistics"""

    # _analysis_engine: Type[BasicStatsEngine]
    # _settings_widget: Type[BasicStatsSettingsWidget]

    def _build_plot(self):
        pw = pg.PlotWidget()
        pw.setBackground("w")
        pw.showGrid(x=True, y=True, alpha=0.3)

        plot_item = pw.plot(pen=self._pen_active)
        self.plot_widgets.append(pw)
        self.plot_items.append([plot_item])

        self.plot_layout.addWidget(pw)

    def update_from_data(self) -> None:
        attr_name = self.attribute_name_for(self.index, self.widget_parameters["mode"])
        try:
            data = vxattribute.read_attribute(attr_name, last=self.widget_parameters["timeframe"])
        except Exception:
            return

        indices, times, values = data
        times = np.array(times, dtype=float)
        values = np.array(values, dtype=float).flatten()

        self.plot_items[0][0].setData(times, values)
        self.plot_widgets[0].setTitle(f"{self.roi_key}_{self.widget_parameters['mode']}")


# ---------------------------------------------------------------------
# TuningCurveWidget
# ---------------------------------------------------------------------
class TuningCurveWidget(BaseAnalysisWidget):
    """Two-plot widget: left/right eye tuning curves"""

    # _analysis_engine: Type[EyeTuningCurveEngine]
    # _settings_widget: Type[TuningCurveSettingsWidget]

    widget_parameters = {
        "regression_type": 'None',
        "df_f_threshold": 0.2
    }

    test_old_idx = -1

    def _build_plot(self):
        # Left and right eye plots side by side
        for eye_name in ["Left Eye", "Right Eye"]:
            pw = pg.PlotWidget()
            pw.setBackground("w")
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel("bottom", "Eye Position", units="deg")
            pw.setLabel("left", "ΔF/F")
            pw.setTitle(eye_name)

            # Use self.color for both eyes
            scatter = pg.ScatterPlotItem(size=8, pen=pg.mkPen(self.color), brush=pg.mkBrush(*self.color, 120))
            pw.addItem(scatter)

            # Regression lines in the same color
            line1 = pg.PlotDataItem(pen=pg.mkPen(self.color, width=2, style=QtCore.Qt.DashLine))
            line2 = pg.PlotDataItem(pen=pg.mkPen(self.color, width=2, style=QtCore.Qt.DashLine))
            pw.addItem(line1)
            pw.addItem(line2)

            # Threshold line
            threshold_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen((180, 180, 180), style=QtCore.Qt.DashLine))
            pw.addItem(threshold_line)

            # Track plot widgets and their items
            self.plot_widgets.append(pw)
            self.plot_items.append([scatter, line1, line2, threshold_line])

            # Add plot widget side by side
            self.plot_layout.addWidget(pw)

    def update_from_data(self) -> None:
        threshold = self.widget_parameters.get("df_f_threshold", 0.2)
        use_regression = self.widget_parameters.get("regression_type", 'None')
        # piecewise = self.widget_parameters.get("piecewise", False)

        try:
            # Epoch data
            attr_epoch = f"roi_{self.index}_f0_epoch"
            epoch_indices, _, epoch_data = safe_read_attribute(attr_epoch, last=1)
            if not len(epoch_indices):
                return
            from_idx_l = epoch_data[-1]["left_eye_index"]
            from_idx_r = epoch_data[-1]["right_eye_index"]

            test = safe_read_attribute(f"roi_{self.index}_left_eye")
            # df/f and eye positions
            df_f = np.array(safe_read_attribute(f"roi_{self.index}_df/f", from_idx=from_idx_r)[2]).squeeze()
            left_eye = np.array(safe_read_attribute(f"roi_{self.index}_left_eye", from_idx=from_idx_r)[2]).squeeze()
            right_eye = np.array(safe_read_attribute(f"roi_{self.index}_right_eye", from_idx=from_idx_r)[2]).squeeze()

            print(f"[Tuning Curve Widget]: last index: {test[0]}, last time: {test[1]}, last value: {test[2]}, len of values since last init: {len(left_eye)}, from_index: {from_idx_r}")

            if len(left_eye) == 0:
                return

            eye_data = [(left_eye, self.plot_items[0]), (right_eye, self.plot_items[1])]

            for eye_vals, items in eye_data:
                scatter, line1, line2, threshold_line = items
                mask = df_f >= threshold

                # Update scatter
                colors = [self.color if val >= threshold else (180, 180, 180) for val in df_f]
                scatter.setData(eye_vals, df_f, brush=colors, pen=pg.mkPen(self.color))

                # Update threshold line
                threshold_line.setValue(threshold)

                #TODO Implement correct regression models
                # Regression
                if use_regression == 'Linear' and np.sum(mask) > 1:
                    coeffs = np.polyfit(eye_vals[mask], df_f[mask], 1)
                    x_vals = np.linspace(np.min(eye_vals[mask]), np.max(eye_vals[mask]), 100)
                    line1.setData(x_vals, np.polyval(coeffs, x_vals))
                    line2.setData([], [])
                elif use_regression == 'Piecewise' and np.sum(mask) > 2:
                    mid_idx = len(df_f[mask]) // 2
                    coeffs1 = np.polyfit(eye_vals[mask][:mid_idx], df_f[mask][:mid_idx], 1)
                    coeffs2 = np.polyfit(eye_vals[mask][mid_idx:], df_f[mask][mid_idx:], 1)
                    x_vals = np.linspace(np.min(eye_vals[mask]), np.max(eye_vals[mask]), 100)
                    line1.setData(x_vals[:50], np.polyval(coeffs1, x_vals[:50]))
                    line2.setData(x_vals[50:], np.polyval(coeffs2, x_vals[50:]))

        except Exception as e:
            print(f"[TuningCurveWidget] Failed to update: {e}")

    def set_active(self, active: bool):
        """Change appearance of scatter + regression lines only."""
        # Active/inactive styles
        active_pen = self._pen_active
        inactive_pen = self._pen_inactive

        active_brush = pg.mkBrush(*self.color, 120)
        inactive_brush = pg.mkBrush(150, 150, 150, 80)

        for items in self.plot_items:
            scatter, line1, line2, threshold_line = items

            # Scatter: change brush + pen
            scatter.setBrush(active_brush if active else inactive_brush)
            scatter.setPen(active_pen if active else inactive_pen)

            # Regression lines: pen only
            line1.setPen(active_pen if active else inactive_pen)
            line2.setPen(active_pen if active else inactive_pen)

            # Do NOT touch threshold_line
            # threshold_line stays visually stable


# class BaseSettingsWidget(QtWidgets.QWidget):
#     """
#     Base class for modular settings panels.
#     Provides self-contained layout, parameter sections, and reset-to-default behavior.
#     Subclasses only need to implement `_build_settings()` to define their widgets.
#     """
#
#     settings_changed = QtCore.Signal(dict, dict)  # (engine_params, widget_params)
#
#     def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
#         super().__init__(parent)
#
#         self.engine_parameter_dict: dict[str, QtWidgets.QWidget] = {}
#         self.widget_parameter_dict: dict[str, QtWidgets.QWidget] = {}
#         self.default_engine_params: dict[str, any] = {}
#         self.default_widget_params: dict[str, any] = {}
#
#         self.layout = QtWidgets.QVBoxLayout(self)
#         self.layout.setContentsMargins(8, 8, 8, 8)
#         self.layout.setSpacing(10)
#
#         # --- Engine parameters section ---
#         self.engine_group = QtWidgets.QGroupBox("Engine Parameters")
#         self.engine_form = QtWidgets.QFormLayout(self.engine_group)
#         self.layout.addWidget(self.engine_group)
#
#         # --- Widget parameters section ---
#         self.widget_group = QtWidgets.QGroupBox("Widget Parameters")
#         self.widget_form = QtWidgets.QFormLayout(self.widget_group)
#         self.layout.addWidget(self.widget_group)
#
#         # --- Reset button ---
#         self.reset_button = QtWidgets.QPushButton("Reset to Defaults")
#         self.reset_button.clicked.connect(self.reset_to_defaults)
#         self.layout.addWidget(self.reset_button)
#
#         self.layout.addStretch()
#
#         # Let subclasses define specific widgets
#         self._build_settings()
#
#         # Populate both sections
#         self._populate_parameter_forms()
#
#         # Wire signals for auto-update
#         self._connect_change_signals()
#
#     # -----------------------------------------------------
#     # Abstract: must be implemented by subclasses
#     # -----------------------------------------------------
#     def _build_settings(self):
#         """
#         Subclasses define and populate:
#             self.engine_parameter_dict[name] = widget
#             self.widget_parameter_dict[name] = widget
#         """
#         raise NotImplementedError
#
#     # -----------------------------------------------------
#     # Form construction helpers
#     # -----------------------------------------------------
#     def _populate_parameter_forms(self):
#         for name, widget in self.engine_parameter_dict.items():
#             label = QtWidgets.QLabel(name.capitalize())
#             self.engine_form.addRow(label, widget)
#
#         for name, widget in self.widget_parameter_dict.items():
#             label = QtWidgets.QLabel(name.capitalize())
#             self.widget_form.addRow(label, widget)
#
#     def _connect_change_signals(self):
#         """Connects widget change events to settings_changed signal."""
#         def connect_widget(widget):
#             if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
#                 widget.valueChanged.connect(self._emit_settings_changed)
#             elif isinstance(widget, QtWidgets.QComboBox):
#                 widget.currentTextChanged.connect(self._emit_settings_changed)
#             elif isinstance(widget, QtWidgets.QCheckBox):
#                 widget.stateChanged.connect(self._emit_settings_changed)
#
#         for widget in list(self.engine_parameter_dict.values()) + list(self.widget_parameter_dict.values()):
#             connect_widget(widget)
#
#     def _emit_settings_changed(self):
#         engine_values, widget_values = self.get_parameter_values()
#         self.settings_changed.emit(engine_values, widget_values)
#
#     # -----------------------------------------------------
#     # Parameter retrieval
#     # -----------------------------------------------------
#     def get_parameter_values(self) -> tuple[dict[str, any], dict[str, any]]:
#         engine_values = {}
#         widget_values = {}
#
#         for name, widget in self.engine_parameter_dict.items():
#             engine_values[name] = self._get_value(widget)
#         for name, widget in self.widget_parameter_dict.items():
#             widget_values[name] = self._get_value(widget)
#
#         return engine_values, widget_values
#
#     @staticmethod
#     def _get_value(widget):
#         if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
#             return widget.value()
#         if isinstance(widget, QtWidgets.QComboBox):
#             return widget.currentText()
#         if isinstance(widget, QtWidgets.QCheckBox):
#             return widget.isChecked()
#         return None
#
#     def get_engine_parameters(self) -> dict[str, any]:
#         return self.get_parameter_values()[0]
#
#     def get_widget_parameters(self) -> dict[str, any]:
#         return self.get_parameter_values()[1]
#
#     # -----------------------------------------------------
#     # Reset functionality
#     # -----------------------------------------------------
#     def reset_to_defaults(self):
#         """Reset all widgets to default values, then emit update."""
#         for name, widget in {**self.engine_parameter_dict, **self.widget_parameter_dict}.items():
#             combined_defaults = {**self.default_engine_params, **self.default_widget_params}
#             default = combined_defaults.get(name)
#             if default is not None:
#                 self._set_widget_value(widget, default)
#
#         self._emit_settings_changed()
#
#     def get_default_dicts(self) -> tuple(dict[str, any],dict[str, any]):
#         """
#         Returns a dictionary of all default parameter values,
#         combining both engine and widget parameters.
#         """
#         return self.default_engine_params, self.default_widget_params
#
#
#     @staticmethod
#     def _set_widget_value(widget, value):
#         if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
#             widget.setValue(value)
#         elif isinstance(widget, QtWidgets.QComboBox):
#             idx = widget.findText(str(value))
#             if idx >= 0:
#                 widget.setCurrentIndex(idx)
#         elif isinstance(widget, QtWidgets.QCheckBox):
#             widget.setChecked(bool(value))

class BaseSettingsWidget(QtWidgets.QWidget):
    """
    Base class for modular settings panels.
    Provides self-contained layout, parameter sections, and reset-to-default behavior.
    Subclasses only need to implement `_build_settings()` to define their widgets.
    """

    # Separate signals for decoupling
    engine_settings_changed = QtCore.Signal(dict)
    widget_settings_changed = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self.engine_parameter_dict: dict[str, QtWidgets.QWidget] = {}
        self.widget_parameter_dict: dict[str, QtWidgets.QWidget] = {}
        self.default_engine_params: dict[str, any] = {}
        self.default_widget_params: dict[str, any] = {}

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(10)

        # -----------------------------
        # Engine parameters section
        # -----------------------------
        self.engine_group = QtWidgets.QGroupBox("Engine Parameters")
        self.engine_layout = QtWidgets.QVBoxLayout(self.engine_group)

        # Form layout for parameters
        self.engine_form = QtWidgets.QFormLayout()
        self.engine_layout.addLayout(self.engine_form)

        # Engine reset button inside the engine group
        self.engine_reset_button = QtWidgets.QPushButton("Reset Engine Defaults")
        self.engine_reset_button.clicked.connect(self.reset_engine_defaults)
        self.engine_layout.addWidget(self.engine_reset_button)

        self.layout.addWidget(self.engine_group)

        # -----------------------------
        # Widget parameters section
        # -----------------------------
        self.widget_group = QtWidgets.QGroupBox("Widget Parameters")
        self.widget_layout = QtWidgets.QVBoxLayout(self.widget_group)

        # Form layout for parameters
        self.widget_form = QtWidgets.QFormLayout()
        self.widget_layout.addLayout(self.widget_form)

        # Widget reset button inside the widget group
        self.widget_reset_button = QtWidgets.QPushButton("Reset Widget Defaults")
        self.widget_reset_button.clicked.connect(self.reset_widget_defaults)
        self.widget_layout.addWidget(self.widget_reset_button)

        self.layout.addWidget(self.widget_group)

        self.layout.addStretch()

        # Let subclasses define specific widgets
        self._build_settings()

        # Populate both sections
        self._populate_parameter_forms()

        # Wire signals for auto-update
        self._connect_change_signals()


    # -----------------------------------------------------
    # Abstract: must be implemented by subclasses
    # -----------------------------------------------------
    def _build_settings(self):
        raise NotImplementedError

    # -----------------------------------------------------
    # Form construction helpers
    # -----------------------------------------------------
    def _populate_parameter_forms(self):
        for name, widget in self.engine_parameter_dict.items():
            label = QtWidgets.QLabel(name.capitalize())
            self.engine_form.addRow(label, widget)

        for name, widget in self.widget_parameter_dict.items():
            label = QtWidgets.QLabel(name.capitalize())
            self.widget_form.addRow(label, widget)

    def _connect_change_signals(self):
        """Connects widget change events to the proper signal."""
        def connect_widget(widget, category: str):
            if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
                widget.valueChanged.connect(lambda _: self._emit_settings_changed(category))
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.currentTextChanged.connect(lambda _: self._emit_settings_changed(category))
            elif isinstance(widget, QtWidgets.QCheckBox):
                widget.stateChanged.connect(lambda _: self._emit_settings_changed(category))

        for widget in self.engine_parameter_dict.values():
            connect_widget(widget, "engine")
        for widget in self.widget_parameter_dict.values():
            connect_widget(widget, "widget")

    # -----------------------------------------------------
    # Emit settings changed
    # -----------------------------------------------------
    def _emit_settings_changed(self, category: str):
        if category == "engine":
            engine_params = self.get_engine_parameters()
            self.engine_settings_changed.emit(engine_params)
        elif category == "widget":
            widget_params = self.get_widget_parameters()
            self.widget_settings_changed.emit(widget_params)

    # -----------------------------------------------------
    # Parameter retrieval
    # -----------------------------------------------------
    def get_parameter_values(self) -> tuple[dict[str, any], dict[str, any]]:
        engine_values = {name: self._get_value(w) for name, w in self.engine_parameter_dict.items()}
        widget_values = {name: self._get_value(w) for name, w in self.widget_parameter_dict.items()}
        return engine_values, widget_values

    @staticmethod
    def _get_value(widget):
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            return widget.value()
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        return None

    def get_engine_parameters(self) -> dict[str, any]:
        return self.get_parameter_values()[0]

    def get_widget_parameters(self) -> dict[str, any]:
        return self.get_parameter_values()[1]

    # -----------------------------------------------------
    # Reset functionality (emits separate signals)
    # -----------------------------------------------------
    # def reset_to_defaults(self):
    #     """Reset all widgets to default values and emit signals."""
    #     for name, widget in self.engine_parameter_dict.items():
    #         default = self.default_engine_params.get(name)
    #         if default is not None:
    #             self._set_widget_value(widget, default)
    #
    #     for name, widget in self.widget_parameter_dict.items():
    #         default = self.default_widget_params.get(name)
    #         if default is not None:
    #             self._set_widget_value(widget, default)
    #
    #     # Emit signals separately
    #     self.engine_settings_changed.emit(self.get_engine_parameters())
    #     self.widget_settings_changed.emit(self.get_widget_parameters())
    def reset_engine_defaults(self):
        for name, widget in self.engine_parameter_dict.items():
            default = self.default_engine_params.get(name)
            if default is not None:
                self._set_widget_value(widget, default)
        self.engine_settings_changed.emit(self.get_engine_parameters())

    def reset_widget_defaults(self):
        for name, widget in self.widget_parameter_dict.items():
            default = self.default_widget_params.get(name)
            if default is not None:
                self._set_widget_value(widget, default)
        self.widget_settings_changed.emit(self.get_widget_parameters())

    @staticmethod
    def _set_widget_value(widget, value):
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QComboBox):
            idx = widget.findText(str(value))
            if idx >= 0:
                widget.setCurrentIndex(idx)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))


# ---------------------------------------------------------------------
# Example: Basic Stats Settings Widget
# ---------------------------------------------------------------------
class BasicStatsSettingsWidget(BaseSettingsWidget):
    def _build_settings(self):
        # Widget parameters
        spin = QtWidgets.QSpinBox()
        spin.setRange(10, 5000)
        spin.setValue(100)
        self.widget_parameter_dict["timeframe"] = spin
        self.default_widget_params["timeframe"] = 100

        combo = QtWidgets.QComboBox()
        combo.addItems(["mean", "median", "std"])
        combo.setCurrentText("mean")
        self.widget_parameter_dict["mode"] = combo
        self.default_widget_params["mode"] = "mean"

        # Engine parameters (example placeholder)

class TuningCurveSettingsWidget(BaseSettingsWidget):
    """Settings panel for Eye Tuning Curve analysis and plotting."""

    def _build_settings(self):
        # -----------------------
        # Widget Parameters
        # -----------------------
        regression_combo = QtWidgets.QComboBox()
        regression_combo.addItems(["None", "Linear", "Piecewise"])
        regression_combo.setCurrentText("None")
        self.widget_parameter_dict["regression_type"] = regression_combo
        self.default_widget_params["regression_type"] = "None"

        df_f_thresh_spin = QtWidgets.QDoubleSpinBox()
        df_f_thresh_spin.setDecimals(4)
        df_f_thresh_spin.setSingleStep(0.01)
        df_f_thresh_spin.setRange(0.0, 4.0)
        df_f_thresh_spin.setValue(0.2)
        self.widget_parameter_dict["df_f_threshold"] = df_f_thresh_spin
        self.default_widget_params["df_f_threshold"] = 0.2

        # -----------------------
        # Engine Parameters
        # -----------------------
        f0_strategy_combo = QtWidgets.QComboBox()
        f0_strategy_combo.addItems(["fixed", "decay"])
        f0_strategy_combo.setCurrentText("fixed")
        self.engine_parameter_dict["f0_strategy"] = f0_strategy_combo
        self.default_engine_params["f0_strategy"] = "fixed"

        f0_mode_combo = QtWidgets.QComboBox()
        f0_mode_combo.addItems(["mean", "median", "std"])
        f0_mode_combo.setCurrentText("mean")
        self.engine_parameter_dict["f0_mode"] = f0_mode_combo
        self.default_engine_params["f0_mode"] = "mean"

        f0_decay_spin = QtWidgets.QDoubleSpinBox()
        f0_decay_spin.setDecimals(3)
        f0_decay_spin.setSingleStep(0.01)
        f0_decay_spin.setRange(0.0, 1.0)
        f0_decay_spin.setValue(0.05)
        self.engine_parameter_dict["f0_decay_rate"] = f0_decay_spin
        self.default_engine_params["f0_decay_rate"] = 0.05
        f0_decay_spin.setEnabled(f0_strategy_combo.currentText() == "decay")

        f0_strategy_combo.currentTextChanged.connect(
            lambda txt: f0_decay_spin.setEnabled(txt == "decay")
        )

        f0_time_points_spin = QtWidgets.QSpinBox()
        f0_time_points_spin.setRange(1, 1000)
        f0_time_points_spin.setValue(20)
        self.engine_parameter_dict["f0_time_points"] = f0_time_points_spin
        self.default_engine_params["f0_time_points"] = 20

        # -----------------------
        # Reinitialize F0 button
        # -----------------------
        self.reinit_btn = QtWidgets.QPushButton("Reinitialize F0")
        self.reinit_btn.clicked.connect(self._force_reinitialize)
        self.engine_form.addRow(self.reinit_btn)
        self._update_reinit_button_state()

        # Connect engine widget changes to update the reinit button state
        f0_strategy_combo.currentTextChanged.connect(lambda _: self._update_reinit_button_state())
        f0_decay_spin.valueChanged.connect(lambda _: self._update_reinit_button_state())
        f0_time_points_spin.valueChanged.connect(lambda _: self._update_reinit_button_state())

    # -----------------------------------------------------
    # Enable/disable Reinit button depending on F0 state
    # -----------------------------------------------------
    def _update_reinit_button_state(self):
        initialized = self.get_engine_parameters().get('initialized_f0', True)
        self.reinit_btn.setEnabled(initialized)

    # -----------------------------------------------------
    # Reinitialize engine parameter (emit engine signal only)
    # -----------------------------------------------------
    def _force_reinitialize(self):
        # Update engine parameter dictionary (not widget values)
        engine_params = {**self.get_engine_parameters(), 'initialized_f0': False}
        self.engine_settings_changed.emit(engine_params)


    # def _build_settings(self):
    #     # -----------------------
    #     # Widget Parameters
    #     # -----------------------
    #
    #     # Regression type: No / Linear / Piecewise
    #     regression_combo = QtWidgets.QComboBox()
    #     regression_combo.addItems(["None", "Linear", "Piecewise"])
    #     regression_combo.setCurrentText("None")
    #     self.widget_parameter_dict["regression_type"] = regression_combo
    #     self.default_widget_params["regression_type"] = "None"
    #
    #     # df/f threshold
    #     df_f_thresh_spin = QtWidgets.QDoubleSpinBox()
    #     df_f_thresh_spin.setDecimals(4)
    #     df_f_thresh_spin.setSingleStep(0.01)
    #     df_f_thresh_spin.setRange(0.0, 1.0)
    #     df_f_thresh_spin.setValue(0.02)
    #     self.widget_parameter_dict["df_f_threshold"] = df_f_thresh_spin
    #     self.default_widget_params["df_f_threshold"] = 0.02
    #
    #
    #     # -----------------------
    #     # Engine Parameters
    #     # -----------------------
    #     # F0 strategy: fixed or decay
    #     f0_strategy_combo = QtWidgets.QComboBox()
    #     f0_strategy_combo.addItems(["fixed", "decay"])
    #     f0_strategy_combo.setCurrentText("fixed")
    #     self.engine_parameter_dict["f0_strategy"] = f0_strategy_combo
    #     self.default_engine_params["f0_strategy"] = "fixed"
    #
    #     #F0 mode
    #     f0_mode_combo = QtWidgets.QComboBox()
    #     f0_mode_combo.addItems(["mean", "median", "std"])
    #     f0_mode_combo.setCurrentText("mean")
    #     self.engine_parameter_dict["f0_mode"] = f0_mode_combo
    #     self.default_engine_params["f0_mode"] = "mean"
    #
    #     # F0 decay rate
    #     f0_decay_spin = QtWidgets.QDoubleSpinBox()
    #     f0_decay_spin.setDecimals(3)
    #     f0_decay_spin.setSingleStep(0.01)
    #     f0_decay_spin.setRange(0.0, 1.0)
    #     f0_decay_spin.setValue(0.05)
    #     self.engine_parameter_dict["f0_decay_rate"] = f0_decay_spin
    #     self.default_engine_params["f0_decay_rate"] = 0.05
    #     # Initially disabled unless decay strategy
    #     f0_decay_spin.setEnabled(f0_strategy_combo.currentText() == "decay")
    #
    #     # Connect strategy change to enable/disable decay spinbox
    #     f0_strategy_combo.currentTextChanged.connect(
    #         lambda txt: f0_decay_spin.setEnabled(txt == "decay")
    #     )
    #
    #     # F0 time points
    #     f0_time_points_spin = QtWidgets.QSpinBox()
    #     f0_time_points_spin.setRange(1, 1000)
    #     f0_time_points_spin.setValue(100)
    #     self.engine_parameter_dict["f0_time_points"] = f0_time_points_spin
    #     self.default_engine_params["f0_time_points"] = 100
    #
    #     f0_strategy_combo.currentTextChanged.connect(lambda _: self._update_reinit_button_state())
    #     f0_decay_spin.valueChanged.connect(lambda _: self._update_reinit_button_state())
    #     f0_time_points_spin.valueChanged.connect(lambda _: self._update_reinit_button_state())
    #
    #     # -----------------------
    #     # Reinitialize button
    #     # ----------------------
    #     self.reinit_btn = QtWidgets.QPushButton("Reinitialize F0")
    #     self.reinit_btn.clicked.connect(self._force_reinitialize)
    #     self.engine_form.addRow(self.reinit_btn)
    #
    #     # Initialize button state
    #     self._update_reinit_button_state()
    #
    #     # Also connect to engine strategy changes if needed
    #     f0_strategy_combo.currentTextChanged.connect(lambda _: self._update_reinit_button_state())
    #
    # def _update_reinit_button_state(self):
    #     initialized = self.get_engine_parameters().get('initialized_f0', True)
    #     self.reinit_btn.setEnabled(initialized)
    #
    # def _force_reinitialize(self):
    #     # Directly update engine parameter dictionary (not a widget)
    #     engine_params = {**self.get_engine_parameters()}
    #     engine_params['initialized_f0'] = False
    #     self.settings_changed.emit(engine_params, self.get_widget_parameters())


class AnalysisEngine:
    """Base class for all analysis engines (math only)."""

    analysis_attributes_default = []
    engine_parameters_default = {}
    # engine_parameters = {}
    # widget_type : BaseAnalysisWidget = None
    # settings_type: BaseSettingsWidget = None


    def __init__(self, max_rois = None):
        print("set up required attributes")

        self.analysis_attributes = copy.deepcopy(self.__class__.analysis_attributes_default)
        self.engine_parameters = copy.deepcopy(self.__class__.engine_parameters_default)
        self.max_rois = max_rois
        self._set_up_attribute_tracking()
        # self.max_rois = OnlineAnalysisRoutine.instance().max_rois_tracked
        print(f"NEW ENGINE CREATED: {self} id={id(self)} Engine process ID: {os.getpid()},  PPID: {os.getppid()}")
        self.test_coutner = 0

        self.test_coutner1 = 0

    def _set_up_attribute_tracking(self):


        for i in range(self.max_rois):
            for attr in self.analysis_attributes:
                full_name = f'roi_{i}_{attr["name"]}'
                if attr['type'] == 'array':
                    # print(f'Set up {full_name} as array attribute')
                    vxattribute.ArrayAttribute(full_name, (1,), vxattribute.ArrayType.float64)
                elif attr['type'] == 'object':
                    # print(f'Set up {full_name} as object attribute')
                    vxattribute.ObjectAttribute(full_name)
                else:
                    raise ValueError(f'Unknown attribute type {attr["type"]} for {full_name}')


    def compute(self):
        """Override in subclasses with specific logic."""
        raise NotImplementedError

    def compute_basic_stats(self, frame: np.array, roi : "BaseROI", roi_idx: int = 0):
        """Reusable helper: mean, std per ROI."""

        # print(f'I want to compute basic stats for {roi.layer_idx} {roi.roi_idx} {roi_idx}')
        _temp_result_dict = {}
        pixel_mask = roi.pixel_mask
        roiactivity_pixels = frame[pixel_mask]

        mean = np.mean(roiactivity_pixels)
        std = np.std(roiactivity_pixels)
        med = np.median(roiactivity_pixels)

        _temp_result_dict['mean'] = mean
        _temp_result_dict['std'] = std
        _temp_result_dict['median'] = med


        self._write_result_to_attribute(roi_idx, _temp_result_dict)

    def update_engine_parameters(self, engine_params: dict[str, any]) -> None:
        # Find keys in engine_params that are not in self.engine_parameters
        # new_keys = set(engine_params) - set(self.engine_parameters)
        #
        # if new_keys:
        #     print(f"Warning unrecognised engine parameters: {new_keys}")
        #
        # # Update existing dictionary without replacing it
        self.engine_parameters.update(engine_params)
        print(f"[Engine:{type(self)}] Updated engine parameters: {self.engine_parameters}")

    def _write_result_to_attribute(self, roi_idx, result):
        """Write a dictionary of results to the attribute writer."""

        # print(f'I want to save {len(result)} roi attributes for {roi_name}')
        for key, value in result.items():

            # if self.test_coutner < 3:
            #     print(f' {self.test_coutner}: roi_{roi_idx}_{key} attribute set up with value: {value}')
            vxattribute.write_attribute(
                f'roi_{roi_idx}_{key}', value
            )

        self.test_coutner += 1



class BasicStatsEngine(AnalysisEngine):


    analysis_attributes_default = [
        {'name': 'mean', 'type': 'array'},
        {'name': 'std', 'type': 'array'},
        {'name': 'median', 'type': 'array'}
    ]

    # widget_type :Type[BasicStatsWidget]
    # settings_type : Type[BasicStatsSettingsWidget]

    def __init__(self, *args, **kwargs):
        super(BasicStatsEngine, self).__init__(*args, **kwargs)

    def compute(self, frame: np.array, roi : "BaseROI", roi_idx: int = 0, time = None, frame_index=None):

        # print(f'I compute for the {self.test_coutner1} time here')
        # self.test_coutner1 += 1
        return self.compute_basic_stats(frame, roi, roi_idx)



class EyeTuningCurveEngine(AnalysisEngine):
    """Engine for computing eye-position tuning curves from ROI fluorescence data."""

    analysis_attributes_default = [
        {'name': 'left_eye', 'type': 'array'},
        {'name': 'right_eye', 'type': 'array'},
        {'name': 'df/f', 'type': 'array'},
        {'name': 'f0_epoch', 'type': 'object'}
    ]

    # widget_type: Type[TuningCurveWidget]
    # settings_type: Type[TuningCurveSettingsWidget]

    engine_parameters_default = {
        'f0_mode': 'mean',           # method to compute intensity
        'f0_time_points': 20,         # number of frames for baseline estimation
        'f0_strategy': 'fixed',      # 'fixed' or 'decay'
        'f0_decay_rate': 0.05,       # exponential decay rate for adaptive F0
        'initialized_f0': False
    }

    _init_time = False
    _initial_time = 0.0

    _f0_temp_save = {}
    _f0 = {}
    _f0_initialized = {}
    _f0_last_update = {}
    _f0_epoch_start = {}  # roi_idx -> {'index': int, 'time': float, 'strategy': str}
    _f0_last_strategy = {}  # roi_idx -> last used strategy


    def __init__(self, *args, **kwargs):
        super(EyeTuningCurveEngine, self).__init__(*args, **kwargs)


    def compute(self, frame: np.ndarray, roi: "BaseROI", roi_idx: int = 0, time=None, frame_index=None):
        """Compute ΔF/F for a given ROI and associate it with eye position data."""
        current_strategy = self.engine_parameters['f0_strategy']
        last_strategy = self._f0_last_strategy.get(roi_idx, current_strategy)

        #TODO: Fix general indexing issue (maybe run all engines)
        # Detect external reinitialization or strategy change
        if (not self.engine_parameters['initialized_f0']) or (current_strategy != last_strategy):
            self._f0_initialized[roi_idx] = False
            self._f0_last_strategy[roi_idx] = current_strategy

        # Initialize if not ready
        if not self._f0_initialized.get(roi_idx, False):
            self._initialize_f0(frame, roi, roi_idx, time, frame_index)
            return

        # Compute mean fluorescence
        pixel_mask = roi.pixel_mask
        roi_activity = frame[pixel_mask]
        f_t = np.nanmean(roi_activity)

        f0_value = self._f0.get(roi_idx)
        if f0_value is None or np.isnan(f0_value):
            print(f"ROI {roi_idx} has no valid baseline F0. Skipping computation.")
            return

        # Update F₀ if decay mode active
        if current_strategy == 'decay':
            rate = self.engine_parameters['f0_decay_rate']
            self._f0[roi_idx] = (1 - rate) * f0_value + rate * f_t
            self._f0_last_update[roi_idx] = time

        df_f = (f_t - self._f0[roi_idx]) / self._f0[roi_idx]

        # --- Eye position retrieval ---
        _, times_l, eyepos_l = vxattribute.read_attribute('eyepos_ang_le_pos_0', from_idx=0) #TODO: make it not just work for 1 fish (0)
        _, times_r, eyepos_r = vxattribute.read_attribute('eyepos_ang_re_pos_0', from_idx=0)

        i_l = np.argmin(np.abs(times_l - time))
        i_r = np.argmin(np.abs(times_r - time))

        left_eye_pos = eyepos_l[i_l]
        right_eye_pos = eyepos_r[i_r]

        # --- Write outputs ---
        result = {'df/f': df_f, 'left_eye': left_eye_pos, 'right_eye': right_eye_pos}
        self._write_result_to_attribute(roi_idx, result)

    def _initialize_f0(self, frame: np.ndarray, roi: "BaseROI", roi_idx: int, time: float, frame_index: int):
        """Accumulate baseline F₀ for each ROI until enough frames are collected."""
        if roi_idx not in self._f0_temp_save:
            self._f0_temp_save[roi_idx] = []
            print(f"Starting F₀ initialization for ROI {roi_idx}")

        roi_activity = frame[roi.pixel_mask]
        if self.engine_parameters['f0_mode'] == 'mean':
            f0_measure = np.nanmean(roi_activity)
        elif self.engine_parameters['f0_mode'] == 'median':
            f0_measure = np.nanmedian(roi_activity)
        elif self.engine_parameters['f0_mode'] == 'std':
            f0_measure = np.nanstd(roi_activity)
        else:
            raise ValueError(f"Unknown f0 mode {self.engine_parameters['f0_mode']}")

        self._f0_temp_save[roi_idx].append(f0_measure)

        # Enough frames collected → finalize baseline
        if len(self._f0_temp_save[roi_idx]) >= self.engine_parameters['f0_time_points']:
            f0_value = np.nanmean(self._f0_temp_save[roi_idx])
            self._f0[roi_idx] = f0_value
            self._f0_initialized[roi_idx] = True
            self._f0_last_update[roi_idx] = time
            self.engine_parameters['initialized_f0'] = True
            self._f0_temp_save[roi_idx].clear()

            # --- NEW: Find corresponding eye indices at this epoch start ---
            _, times_l, _ = vxattribute.read_attribute('eyepos_ang_le_pos_0', from_idx=0)
            _, times_r, _ = vxattribute.read_attribute('eyepos_ang_re_pos_0', from_idx=0)

            left_eye_idx = int(np.argmin(np.abs(times_l - time)))
            right_eye_idx = int(np.argmin(np.abs(times_r - time)))
            # --------------------------------------------------------------

            df_f = np.array(safe_read_attribute(f"roi_{roi_idx}_df/f")[0]).squeeze()

            self._f0_epoch_start[roi_idx] = {
                'index': frame_index.flat[0],
                'time': float(time.flat[0]),
                'strategy': self.engine_parameters['f0_strategy'],
                'left_eye_index': df_f.flat[0],  # <--- stored for later alignment
                'right_eye_index': df_f.flat[0]  # <--- stored for later alignment
            }

            result = {'f0_epoch': self._f0_epoch_start[roi_idx]}
            self._write_result_to_attribute(roi_idx, result)

            print(
                f"Baseline F₀ established for ROI {roi_idx} "
                f"at frame {self._f0_epoch_start[roi_idx]['index']}, time {self._f0_epoch_start[roi_idx]['time']}, "
                f"mode {self._f0_epoch_start[roi_idx]['strategy']}, "
                f"eye indices (L: {left_eye_idx}, R: {right_eye_idx})"
            )

        else:
            # TODO: Make this not rely on nan ?
            # --- Write outputs ---
            result = {'df/f': np.NAN, 'left_eye': np.NAN, 'right_eye': np.NAN}
            self._write_result_to_attribute(roi_idx, result)
        # ---------------------------------------------------------------------


# Registry for analysis types (extendable)
# ---------------------------------------------------------------------
ANALYSIS_REGISTRY: Dict[str, Tuple[Type[AnalysisEngine], Type[BaseSettingsWidget], Type[BaseAnalysisWidget]]] = {
    "Basic Stats": (BasicStatsEngine, BasicStatsSettingsWidget, BasicStatsWidget),
    "Tuning Curves": (EyeTuningCurveEngine, TuningCurveSettingsWidget, TuningCurveWidget)
}

# ---------------------------------------------------------------------
# Manager widget: OnlineAnalysisWidget
# ---------------------------------------------------------------------
class OnlineAnalysisWidget(vxui.WorkerAddonWidget):
    """Universal orchestrator between analysis engine, settings, and ROI widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._routine = OnlineAnalysisRoutine.instance()


        self._roi_data: dict[ROIKey, dict] = {}

        # Default analysis selection
        self._current_analysis_name = "Basic Stats"
        _, self._current_settings_cls, self._current_analysis_cls = ANALYSIS_REGISTRY[self._current_analysis_name]

        self.settings_widget: BaseSettingsWidget | None = None

        self._build_ui()
        self._wire_signals()

        self.connect_to_timer(self.refresh_gui)

    # ----------------------------
    # UI Construction
    # ----------------------------
    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # --- Top bar ---
        top_bar = QtWidgets.QHBoxLayout()
        main_layout.addLayout(top_bar)

        self.data_source_combo = QtWidgets.QComboBox()
        self.data_source_combo.addItems(["from tracker", "from file"])
        top_bar.addWidget(self.data_source_combo)

        self.analysis_type_combo = QtWidgets.QComboBox()
        self.analysis_type_combo.addItems(list(ANALYSIS_REGISTRY.keys()))
        top_bar.addWidget(self.analysis_type_combo)

        self.pull_data_btn = QtWidgets.QPushButton("Pull Data")
        top_bar.addWidget(self.pull_data_btn)
        top_bar.addStretch()

        # --- Splitters ---
        outer_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        main_layout.addWidget(outer_splitter, stretch=1)

        inner_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        outer_splitter.addWidget(inner_splitter)

        # --- Left: Global Settings ---
        self.global_settings_group = QtWidgets.QGroupBox("Global Settings")
        self.global_settings_layout = QtWidgets.QVBoxLayout(self.global_settings_group)
        inner_splitter.addWidget(self.global_settings_group)

        # --- Right: Scrollable ROI area ---
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_container = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_container)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_container)
        inner_splitter.addWidget(self.scroll_area)

        # Default layout ratios
        inner_splitter.setStretchFactor(0, 0)
        inner_splitter.setStretchFactor(1, 1)
        inner_splitter.setSizes([250, 800])

        # --- Bottom Panel: Hidden and Active ROIs ---
        bottom_panel = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QHBoxLayout(bottom_panel)

        # Hidden ROIs
        hidden_container = QtWidgets.QWidget()
        hidden_layout = QtWidgets.QVBoxLayout(hidden_container)
        hidden_layout.addWidget(QtWidgets.QLabel("Hidden ROIs:"))
        self.hidden_box = QtWidgets.QWidget()
        self.hidden_box_layout = QtWidgets.QVBoxLayout(self.hidden_box)
        self.hidden_box_layout.addStretch()
        hidden_layout.addWidget(self.hidden_box)
        self.hidden_scroll = QtWidgets.QScrollArea()
        self.hidden_scroll.setWidgetResizable(True)
        self.hidden_scroll.setWidget(hidden_container)
        bottom_layout.addWidget(self.hidden_scroll, stretch=1)

        # Active ROIs
        active_container = QtWidgets.QWidget()
        active_layout = QtWidgets.QVBoxLayout(active_container)
        active_layout.addWidget(QtWidgets.QLabel("Active ROIs:"))
        self.active_list = QtWidgets.QListWidget()
        active_layout.addWidget(self.active_list)
        self.active_scroll = QtWidgets.QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setWidget(active_container)
        bottom_layout.addWidget(self.active_scroll, stretch=1)

        outer_splitter.addWidget(bottom_panel)
        outer_splitter.setStretchFactor(0, 4)
        outer_splitter.setStretchFactor(1, 1)
        outer_splitter.setSizes([800, 150])

        # Initialize first settings panel
        self._rebuild_settings_panel()

    # ----------------------------
    # Wiring
    # ----------------------------
    def _wire_signals(self):
        self.pull_data_btn.clicked.connect(self.on_pull_clicked)
        self.analysis_type_combo.currentTextChanged.connect(self.on_analysis_type_changed)

    # ----------------------------
    # Settings Handling
    # ----------------------------
    def _clear_settings_panel(self):
        for i in reversed(range(self.global_settings_layout.count())):
            item = self.global_settings_layout.takeAt(i)
            if (w := item.widget()) is not None:
                w.deleteLater()

    def _rebuild_settings_panel(self):
        """Clear the current settings panel and rebuild it with the selected settings class."""
        self._clear_settings_panel()

        # Instantiate the settings widget
        self.settings_widget = self._current_settings_cls(parent=self.global_settings_group)

        # Connect decoupled signals
        self.settings_widget.widget_settings_changed.connect(self._on_widget_settings_changed)
        self.settings_widget.engine_settings_changed.connect(self._on_engine_settings_changed)

        # Add the new widget to the layout
        self.global_settings_layout.addWidget(self.settings_widget)


    def _on_widget_settings_changed(self, widget_params: dict):
        """
        Update all ROI analysis widgets with the new widget parameters.
        Engine parameters are unaffected.
        """
        for roi_key, roi in self._roi_data.items():
            roi_widget = roi["widget"]
            roi_widget.update_settings(widget_params)

    def _on_engine_settings_changed(self, engine_params: dict):
        """
        Update engine parameters in the routine.
        Widget parameters are unaffected.
        """

        self._routine.current_engine_parameters.update(engine_params)
        # Flag routine to update engine
        self._routine.update_engine_params = True

        print(f"[OnlineAnalysisWidget]: Engine parameters after update: {self._routine.current_engine_parameters}")


    def on_analysis_type_changed(self, text: str):
        if text == self._current_analysis_name:
            return

        self._current_analysis_name = text
        _ , self._current_settings_cls, self._current_analysis_cls = ANALYSIS_REGISTRY[text]
        self._routine.current_engine_name = text
        self._routine.engine_switch = True
        self._rebuild_settings_panel()
        self._recreate_all_roi_widgets()

    # ----------------------------
    # ROI Widget Lifecycle
    # ----------------------------
    def _recreate_all_roi_widgets(self):
        """Clear all existing ROI entries and rebuild them from the routine."""
        for roi_key, roi in list(self._roi_data.items()):
            # Clean up each widget and its container
            widget = roi["widget"]
            container = roi["container"]

            # Make sure the container is detached before deletion
            container.setParent(None)
            container.deleteLater()
            widget.deleteLater()

            # If there’s a restore button (hidden state), remove it too
            if "restore_button" in roi:
                roi["restore_button"].setParent(None)
                roi["restore_button"].deleteLater()

        # Clear the master dict
        self._roi_data.clear()

        # Recreate everything from the routine
        self._populate_roi_widgets_from_routine()

    def _populate_roi_widgets_from_routine(self) -> None:
        """Populate ROI widgets once the routine has loaded its ROIs."""

        def _try_populate():
            if not getattr(self._routine, "loaded_new_rois", False):
                QtCore.QTimer.singleShot(100, _try_populate)
                return

            assignments = self._routine.roi_idx_assignments
            print(f"Populating {len(assignments)} ROI widgets: {assignments}")

            # --- Step 1: remove obsolete ROIs ---
            for roi_key in list(self._roi_data.keys()):
                roi = self._roi_data.pop(roi_key)
                roi["container"].setParent(None)
                roi["container"].deleteLater()
                roi["widget"].deleteLater()
                if "restore_button" in roi:
                    roi["restore_button"].setParent(None)
                    roi["restore_button"].deleteLater()

            # --- Step 2: create fresh widgets for new assignments ---
            for index, roi_key in assignments.items():
                if roi_key in self._roi_data:
                    continue  # already exists

                color = get_roi_color(roi_key[1])
                analysis_widget = self._current_analysis_cls(
                    roi_key, parent=self.scroll_container, color=color
                )
                analysis_widget.index = index
                analysis_widget.update_settings(self.settings_widget.default_widget_params)

                # --- Container for full ROI block ---
                container = QtWidgets.QWidget(self.scroll_container)
                container_layout = QtWidgets.QHBoxLayout(container)
                container_layout.setContentsMargins(2, 2, 2, 2)
                container_layout.setSpacing(6)

                # --- Control panel (left) ---
                control_panel = QtWidgets.QWidget(container)
                control_layout = QtWidgets.QVBoxLayout(control_panel)
                control_layout.setContentsMargins(0, 0, 0, 0)
                control_layout.setSpacing(4)

                roi_label = QtWidgets.QLabel(f"ROI {index}")
                font = roi_label.font()
                font.setPointSize(9)
                roi_label.setFont(font)
                roi_label.setAlignment(QtCore.Qt.AlignHCenter)

                active_box = QtWidgets.QCheckBox("Active")
                active_box.setChecked(True)

                hide_btn = QtWidgets.QPushButton("Hide")

                control_layout.addWidget(roi_label)
                control_layout.addWidget(active_box)
                control_layout.addWidget(hide_btn)
                control_layout.addStretch()

                control_panel.setFixedWidth(80)

                container_layout.addWidget(control_panel)
                container_layout.addWidget(analysis_widget, 1)

                # # --- Connect signals ---
                hide_btn.clicked.connect(partial(self._hide_roi, roi_key))
                active_box.toggled.connect(partial(self._on_roi_active_state_changed, roi_key))
                active_box.toggled.connect(partial(analysis_widget.set_active))

                # hide_btn.clicked.connect(lambda _, k=roi_key: self._hide_roi(k))
                # active_box.toggled.connect(
                #     lambda checked, k=roi_key: self._on_roi_active_state_changed(k, checked)
                # )
                # active_box.toggled.connect(lambda checked, w=analysis_widget: w.set_active(checked))

                # --- Insert into scroll layout ---
                self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, container)

                # --- Track ROI in master dictionary ---
                self._roi_data[roi_key] = {
                    "widget": analysis_widget,
                    "container": container,
                    "checkbox": active_box,
                    "hide_button": hide_btn,
                    "label": roi_label,
                    "visible": True,
                }

                print(f"Created ROI widget for {roi_key}")

            self._refresh_active_list()

        _try_populate()

    def _hide_roi(self, roi_key: ROIKey):
        roi = self._roi_data[roi_key]
        roi["container"].setParent(None)
        roi["visible"] = False

        # create restore button in hidden box
        restore_btn = QtWidgets.QPushButton(f"Restore {roi_key}")
        # restore_btn.clicked.connect(lambda _, k=roi_key: self._restore_roi(k))
        restore_btn.clicked.connect(partial(self._restore_roi, roi_key))
        self.hidden_box_layout.insertWidget(self.hidden_box_layout.count() - 1, restore_btn)
        roi["restore_button"] = restore_btn

    def _restore_roi(self, roi_key: ROIKey):
        roi = self._roi_data[roi_key]
        container = roi["container"]

        # reparent and reinsert into layout
        container.setParent(self.scroll_container)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, container)
        roi["visible"] = True

        # remove restore button cleanly
        if "restore_button" in roi:
            btn = roi.pop("restore_button")
            btn.setParent(None)
            btn.deleteLater()

    def _on_roi_active_state_changed(self, roi_key: ROIKey, active: bool):
        """Update the routine's selected flags for active ROIs and refresh UI."""
        for idx, key in self._routine.roi_idx_assignments.items():
            if key == roi_key:
                self._routine.roi_idx_assignments_selected[idx] = active
                self._routine.update_roi_selection = True
        self._refresh_active_list()

    def _refresh_active_list(self):
        self.active_list.clear()
        for roi_key, roi in self._roi_data.items():
            state = "active" if roi["checkbox"].isChecked() else "inactive"
            self.active_list.addItem(f"{roi_key}: {state}")

        #TODO: Add updated to the routine-


    # ----------------------------
    # Refresh Loop
    # ----------------------------
    def on_pull_clicked(self):
        print("Pulling data")
        self._routine.new_rois_set = True
        self._routine.loaded_new_rois = False
        self._populate_roi_widgets_from_routine()
        self.refresh_gui()

    def refresh_gui(self):
        # Update each visible analysis widget
        for roi in self._roi_data.values():
            if roi["visible"]:
                roi["widget"].update_from_data()

        # Refresh the active list
        self._refresh_active_list()




#TODO: Make Data evaluation from Files
#TODO: Combine all selected ROI in this
#TODO: Make Multi ROI selection more intuitive


#TODO: Update Syscon File Format (-> E-Mail)


#TODO: Fix general ROI selection in tracker (+ellipse and polylines, maybe make dragable ??)
#TODO: Make Online Analysis roi widgets correct size (+zoom on click maybe)
#TODO: Create hide all active non active button maybe
#TODO fix color and regression in the eye tuning curve widget... --> regression computation maybe in engines ?
#TODO: Check engine parameter update again
#TODO Move registery to config file
#TODO: Install NVIDIA drivers again for cellpose
#TODO: From file for tracker and online analyse


#TODO: Nice to have Drag selection of ROI, Sorting for graphs (eg. via active non active or some criteria), general sorting of the graphs
