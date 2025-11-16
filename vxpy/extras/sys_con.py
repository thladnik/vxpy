from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Queue
from functools import partial
import copy

import math
import cv2
import numpy as np
import pyqtgraph as pg

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QBrush, QPen, QColor

import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
import vxpy.core.attribute as vxattribute
from vxpy.extras.ca_processing_2nd_gen import NextGenTrackerRoutine, BaseROI
from vxpy.extras.online_analysis import OnlineAnalysisRoutine
from vxpy.extras.server import ScanImageFrameReceiverTcpServer



class SysConRoutine(vxroutine.WorkerRoutine):
    """
    System Controller Routine responsible for handling ROIs received
    from the NextGenTrackerWidget and triggering downstream processing.

    Attributes:
        rois_to_stimulate (dict): Mapping of layer/ROI indices to ROI data.
        new_rois_set (bool): Flag indicating that new ROIs were received.
        num_layers (int): Current number of layers being tracked.
        ui_update_rois (bool): Flag to indicate the UI should refresh ROIs.
    """

    rois_to_stimulate: dict[tuple[int, int], BaseROI] = {}   #key: layer_idx, roi_idx; value: BaseROI instance
    new_rois_set: bool = False
    num_layers: int = 0
    ui_update_rois: bool = False

    source = "from tracker"

    def __init__(self, *args, **kwargs):
        """
        Initialize SysConRoutine.
        """
        super().__init__(*args, **kwargs)

    def main(self, *args, **kwargs):
        """
        Main routine loop.

        Checks for new ROIs to stimulate, updates internal flags,
        and performs processing.
        """

        if self.new_rois_set:
            # Print received ROIs (for debug/logging purposes)
            self._pull_data()
            print(self.rois_to_stimulate)
            # Reset flags after processing
            # self.new_rois_set = False
            # self.ui_update_rois = True

        else:
            # Placeholder for other routine processing if needed
            pass

    def _pull_data(self):

        if self.source == "from tracker":
            tracker = NextGenTrackerRoutine.instance()
            self.num_layers = copy.copy(tracker.current_layer_num)
            self.rois_to_stimulate.clear()
            self.rois_to_stimulate.update(copy.deepcopy(tracker.rois_to_process))
            self.new_rois_set = False
            self.ui_update_rois = True

            print(f"[pull_data] Routine id: {id(self)} object id: {id(self.rois_to_stimulate)}, ROIs: {len(self.rois_to_stimulate)}")

            print(f"[pull_data] ROIs: {self.rois_to_stimulate} for the routine")

        if self.source == "from analysis": #TODO: implement this correctly
            analysis = OnlineAnalysisRoutine.instance()
            self.num_layers = copy.copy(analysis.current_layer_num)
            self.rois_to_stimulate.clear()
            self.rois_to_stimulate.update(copy.deepcopy(analysis.rois_to_laser))
            self.new_rois_set = False
            self.ui_update_rois = True



class SysConControlWindow(vxui.WorkerAddonWidget):
    """
    Control window for SysCon export and laser stimulation settings.

    Features:
        - Display image tiles per layer.
        - ROI selection and toggling for laser stimulation.
        - Global and per-ROI laser intensity settings.
        - Duration, scanning mode, and diameter controls.
        - Export ROIs to SysCon files and upload for triggering.
    """

    frame_name: str = 'roi_activity_tracker_frame'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # -----------------------
        # State variables
        # -----------------------
        self.mode = "mean"
        self.image_plots: dict[int, ImagePlot] = {}
        self.layer_num = SysConRoutine.instance().num_layers
        self.global_laser_intensity: float = 10.0
        self.global_roi_diameter: float = 20.0
        self.laser_prep_list: list = []
        self.roi_widgets: list[tuple] = []  # Tuples: (checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx)

        # -----------------------
        # Main Layout
        # -----------------------
        main_layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(main_layout)

        # --- Top control bar
        top_bar = QtWidgets.QHBoxLayout()
        main_layout.addLayout(top_bar)

        # Dropdown menu
        self.data_source_combo = QtWidgets.QComboBox()
        self.data_source_combo.addItems(["from tracker", "from analysis"])
        top_bar.addWidget(self.data_source_combo)

        # Pull Data button
        self.pull_data_btn = QtWidgets.QPushButton("Pull Data")
        self.pull_data_btn.clicked.connect(self.on_pull_data_clicked)
        top_bar.addWidget(self.pull_data_btn)

        # Add stretch so button + combo stay left
        top_bar.addStretch()

        # -----------------------
        # Layout: Horizontal splitter
        # -----------------------
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.central_widget.setLayout(QtWidgets.QVBoxLayout())
        self.central_widget.layout().addWidget(splitter)

        # --- Left side: Image tiles
        self.image_tiles = pg.GraphicsLayoutWidget()
        splitter.addWidget(self.image_tiles)

        # --- Right side: Control panel
        right_container = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        splitter.addWidget(right_container)

        splitter.setSizes([400, 500])  # left width = 300px, right width = 500px


        # -----------------------
        # Top right: ROI Controls
        # -----------------------
        self.roi_group_box = QtWidgets.QGroupBox("ROI Controls")
        self.roi_group_box.setLayout(QtWidgets.QVBoxLayout())

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_widget.setMinimumWidth(270)  # Prevent label wrapping
        self.scroll_layout = QtWidgets.QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.roi_group_box.layout().addWidget(self.scroll_area)

        # -----------------------
        # Bottom right: Controls and settings
        # -----------------------
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 10)
        button_layout.setSpacing(8)

        # --- Label
        button_layout.addWidget(QtWidgets.QLabel("SysCon export and controls."))

        # --- Toggle all ROIs
        self.toggle_all_button = QtWidgets.QPushButton("Toggle all ROIs for laser")
        self.toggle_all_button.clicked.connect(self.toggle_all_roi_for_laser)
        button_layout.addWidget(self.toggle_all_button)


        # --- Laser Intensity
        intensity_layout = QtWidgets.QHBoxLayout()
        intensity_layout.addWidget(QtWidgets.QLabel("Laser Intensity:"))
        intensity_layout.addStretch(1)
        self.intensity_field = QtWidgets.QLineEdit()
        self.intensity_field.setPlaceholderText("%")
        intensity_layout.addWidget(self.intensity_field)
        intensity_layout.addWidget(QtWidgets.QLabel("%"))
        button_layout.addLayout(intensity_layout)
        self.intensity_field.editingFinished.connect(self.set_all_laser_intensity)

        # --- Duration
        duration_layout = QtWidgets.QHBoxLayout()
        duration_layout.addWidget(QtWidgets.QLabel("Duration:"))
        duration_layout.addStretch(1)
        self.duration_field = QtWidgets.QLineEdit()
        self.duration_field.setPlaceholderText("ms")
        duration_layout.addWidget(self.duration_field)
        duration_layout.addWidget(QtWidgets.QLabel("ms"))
        button_layout.addLayout(duration_layout)

        # --- Scanning mode
        scanning_layout = QtWidgets.QHBoxLayout()
        scanning_layout.addWidget(QtWidgets.QLabel("Scanning mode:"))
        scanning_layout.addStretch(1)
        self.scanning_combo = QtWidgets.QComboBox()
        self.scanning_combo.addItems(["spiral scanning", "parallel scanning"])
        scanning_layout.addWidget(self.scanning_combo)
        button_layout.addLayout(scanning_layout)

        # --- Diameter (optional, visible based on scanning mode)
        self.diameter_widget = QtWidgets.QWidget()
        diameter_layout = QtWidgets.QHBoxLayout(self.diameter_widget)
        diameter_layout.addWidget(QtWidgets.QLabel("Diameter:"))
        diameter_layout.addStretch(1)
        self.diameter_field = QtWidgets.QLineEdit()
        self.diameter_field.setPlaceholderText("pixel")
        diameter_layout.addWidget(self.diameter_field)
        diameter_layout.addWidget(QtWidgets.QLabel("pixel"))
        button_layout.addWidget(self.diameter_widget)
        self.diameter_field.editingFinished.connect(self.update_all_circle_diameters)
        self.update_diameter_visibility()
        self.scanning_combo.currentTextChanged.connect(self.update_diameter_visibility)

        # --- File operations
        self.write_button = QtWidgets.QPushButton("Write SysCon File")
        self.write_button.clicked.connect(self.write_SysCon_file)
        button_layout.addWidget(self.write_button)

        self.upload_button = QtWidgets.QPushButton("Upload/Wait for Trigger")
        self.upload_button.clicked.connect(self.upload_and_wait)
        button_layout.addWidget(self.upload_button)

        # -----------------------
        # Combine top/bottom right
        # -----------------------
        vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_splitter.addWidget(self.roi_group_box)
        vertical_splitter.addWidget(button_container)
        vertical_splitter.setStretchFactor(0, 3)
        vertical_splitter.setStretchFactor(1, 1)
        right_layout.addWidget(vertical_splitter)

        # -----------------------
        # Timer hook for periodic updates
        # -----------------------
        self.connect_to_timer(self.check_state)


    def on_pull_data_clicked(self):
        source = self.data_source_combo.currentText()
        print(f"Pulling data from {source}")
        print(f"[pull_data_clicked] Routine id: {id(SysConRoutine.instance())} object id: {id(SysConRoutine.instance().rois_to_stimulate)}, ROIs: {len(SysConRoutine.instance().rois_to_stimulate)}")
        # SysConRoutine.instance().pull_data(source)
        SysConRoutine.instance().source = source
        SysConRoutine.instance().new_rois_set = True

    def update_diameter_visibility(self):
        """Show diameter input only for spiral scanning mode."""
        self.diameter_widget.setVisible(self.scanning_combo.currentText() == "spiral scanning")

    def check_state(self):
        """
        Periodically called via timer.

        Updates image frames and rebuilds ROI controls if SysConRoutine signals new ROIs.
        """
        syscon = SysConRoutine.instance()
        self.update_frame()

        if syscon.ui_update_rois:
            syscon.ui_update_rois = False
            num_layers = syscon.num_layers
            self.build_image_plots(num_layers)
            self.populate_roi_rows()

    def clear_layout(self, layout: QtWidgets.QLayout):
        """Remove all widgets from a layout safely."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_roi_rows(self):
        """
        Populate scroll area with ROI controls:
            - Label: ROI index + layer + coordinates
            - Checkbox: Prep laser
            - Intensity field: editable if prep enabled
        """
        roi_dict = SysConRoutine.instance().rois_to_stimulate

        # Clear old widgets & internal tracking lists
        self.clear_layout(self.scroll_layout)
        self.roi_widgets.clear()
        self.laser_prep_list.clear()

        # -----------------------
        # Header row
        # -----------------------
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(10)

        header_labels = ["ROI", "Laser", "Intensity", "Diameter"]
        for title in header_labels:
            lbl = QtWidgets.QLabel(f"<b>{title}</b>")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            header_layout.addWidget(lbl, stretch=1)

        self.scroll_layout.addWidget(header_widget)


        for row_idx, ((layer_idx, roi_idx), roi) in enumerate(roi_dict.items()):
            # -----------------------
            # ROI label
            # -----------------------
            roi_label = QtWidgets.QLabel(
                f"ROI {roi_idx} [{layer_idx}]<br>"
                f"<span style='font-size:10px;'>x: {round(roi.x_center)}, "
                f"y: {round(roi.y_center)}, z: {round(roi.z_center)}</span>"
            )
            roi_label.setTextFormat(QtCore.Qt.RichText)
            roi_label.setWordWrap(True)

            # -----------------------
            # Prep checkbox
            # -----------------------
            prep_checkbox = QtWidgets.QCheckBox() #"Prep Laser"
            prep_checkbox.setChecked(roi.prep_laser)

            # -----------------------
            # Intensity field
            # -----------------------
            # Create a spin box for laser intensity (float input between 0.0 and 1.0)
            intensity_spin = QtWidgets.QDoubleSpinBox()
            intensity_spin.setRange(0.0, 1.0)  # Minimum and maximum allowed intensity
            intensity_spin.setSingleStep(0.01)  # Increment when using arrows
            intensity_spin.setValue(self.global_laser_intensity)  # Set initial value
            intensity_spin.setFixedWidth(80)  # Optional fixed width for layout

            # -----------------------
            # Diameter field
            # -----------------------
            # Create a spin box for ROI diameter (float input between 0.0 and 500.0)
            diameter_spin = QtWidgets.QDoubleSpinBox()
            diameter_spin.setRange(0.0, 500.0)  # Minimum and maximum diameter
            diameter_spin.setSingleStep(0.5)  # Increment when using arrows
            diameter_spin.setValue(self.global_roi_diameter)  # Set initial value
            diameter_spin.setFixedWidth(80)  # Optional fixed width for layout

            # -----------------------
            # Enable or disable fields based on ROI laser preparation
            # -----------------------
            if roi.prep_laser:
                # Enable the spin boxes and set initial values
                intensity_spin.setValue(self.global_laser_intensity)
                intensity_spin.setEnabled(True)

                diameter_spin.setValue(self.global_roi_diameter)
                diameter_spin.setEnabled(True)

                # Add to laser preparation list for later processing
                self.laser_prep_list.append(
                    (layer_idx, roi_idx, self.global_laser_intensity, self.global_roi_diameter)
                )
            else:
                # Disable the spin boxes if ROI is not prepared
                intensity_spin.setEnabled(False)
                diameter_spin.setEnabled(False)


            # Track widgets for later updates (include diameter widget)
            self.roi_widgets.append((prep_checkbox, intensity_spin, diameter_spin, layer_idx, roi_idx))



            #Connect widgets for live updating:
            prep_checkbox.stateChanged.connect(
                partial(self.on_checkbox_toggled, layer_idx=layer_idx, roi_idx=roi_idx,
                        intensity_spin=intensity_spin, diameter_spin=diameter_spin))

            intensity_spin.editingFinished.connect(
                partial(self.on_intensity_changed, intensity_spin, layer_idx, roi_idx))

            diameter_spin.editingFinished.connect(
                partial(self.on_diameter_changed, diameter_spin, layer_idx, roi_idx))

            # -----------------------
            # Combine widgets in a horizontal row
            # -----------------------
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(10)
            row_layout.addWidget(roi_label, stretch=3)
            row_layout.addWidget(prep_checkbox, stretch=1)
            row_layout.addWidget(intensity_spin, stretch=1)
            row_layout.addWidget(diameter_spin, stretch=1)

            self.scroll_layout.addWidget(row_widget)

        # Ensure checkbox states are consistent with laser_prep_list
        for checkbox, intensity_spin, diameter_spin, layer_idx, roi_idx in self.roi_widgets:
            checkbox.stateChanged.connect(
                partial(
                    self.on_checkbox_toggled,
                    layer_idx=layer_idx,
                    roi_idx=roi_idx,
                    intensity_spin=intensity_spin,
                    diameter_spin=diameter_spin
                )
            )
            self.on_checkbox_toggled(checkbox.isChecked(), layer_idx, roi_idx, intensity_spin, diameter_spin)

    def on_checkbox_toggled(
            self,
            state: int,
            layer_idx: int,
            roi_idx: int,
            intensity_spin: QtWidgets.QDoubleSpinBox,
            diameter_spin: QtWidgets.QDoubleSpinBox
    ) -> None:
        """
        Handle toggling of a checkbox for a ROI.
        Enables/disables the spin boxes, updates the visualization,
        and manages the laser preparation list.
        """

        # Get the ROI object
        roi = SysConRoutine.instance().rois_to_stimulate.get((layer_idx, roi_idx))
        if not roi:
            return

        # Get the corresponding image plot
        image_plot = self.image_plots.get(layer_idx)
        if not image_plot:
            return

        # Determine if checkbox is checked
        is_checked = bool(state)
        intensity_spin.setEnabled(is_checked)
        diameter_spin.setEnabled(is_checked)

        # Get current values from spin boxes
        intensity_val = intensity_spin.value()
        diameter_val = diameter_spin.value()

        # Update visualization for this ROI
        image_plot.create_or_update_circle(
            roi_idx=roi_idx,
            center=(roi.x_center, roi.y_center),
            alpha=intensity_val,
            diameter=diameter_val,
            label=f"ROI {roi_idx}"
        )
        image_plot.set_circle_visible(roi_idx, is_checked)

        # Remove any previous entry for this ROI in the preparation list
        self.laser_prep_list = [
            entry for entry in self.laser_prep_list
            if not (entry[0] == layer_idx and entry[1] == roi_idx)
        ]

        # If checked, add updated entry
        if is_checked:
            self.laser_prep_list.append((layer_idx, roi_idx, intensity_val, diameter_val))

    def update_laser_prep_entry(self, layer_idx, roi_idx, intensity=None, diameter=None):
        for i, entry in enumerate(self.laser_prep_list):
            if entry[0] == layer_idx and entry[1] == roi_idx:
                old_l, old_r, old_int, old_diam = entry
                new_int = intensity if intensity is not None else old_int
                new_diam = diameter if diameter is not None else old_diam
                self.laser_prep_list[i] = (old_l, old_r, new_int, new_diam)
                return

        # If no existing entry and both values specified, create one
        if intensity is not None and diameter is not None:
            self.laser_prep_list.append((layer_idx, roi_idx, intensity, diameter))

    def on_intensity_changed(self, intensity_spin: QtWidgets.QDoubleSpinBox, layer_idx: int, roi_idx: int):
        """
        Handle changes to the intensity spin box.
        Updates the laser prep list and immediately updates visualization.
        """
        intensity_value = intensity_spin.value()  # Already a valid float within range

        # Update the laser prep list (add or modify entry)
        self.update_laser_prep_entry(layer_idx, roi_idx, intensity=intensity_value)

        # Update visualization
        roi = SysConRoutine.instance().rois_to_stimulate.get((layer_idx, roi_idx))
        image_plot = self.image_plots.get(layer_idx)
        if roi and image_plot:
            # Get current diameter from prep list
            _, _, _, diameter = next(
                ((l, r, inten, diam) for l, r, inten, diam in self.laser_prep_list if l == layer_idx and r == roi_idx),
                (layer_idx, roi_idx, intensity_value, self.global_roi_diameter)
            )
            image_plot.create_or_update_circle(
                roi_idx=roi_idx,
                center=(roi.x_center, roi.y_center),
                alpha=intensity_value,
                diameter=diameter,
                label=f"ROI {roi_idx}"
            )

    def on_diameter_changed(self, diameter_spin: QtWidgets.QDoubleSpinBox, layer_idx: int, roi_idx: int):
        """
        Handle changes to the diameter spin box.
        Updates the laser prep list and immediately updates visualization.
        """
        diameter_value = diameter_spin.value()  # Already a valid float within range

        # Update the laser prep list (add or modify entry)
        self.update_laser_prep_entry(layer_idx, roi_idx, diameter=diameter_value)

        # Update visualization
        roi = SysConRoutine.instance().rois_to_stimulate.get((layer_idx, roi_idx))
        image_plot = self.image_plots.get(layer_idx)
        if roi and image_plot:
            # Get current intensity from prep list
            _, _, intensity_value, _ = next(
                ((l, r, inten, diam) for l, r, inten, diam in self.laser_prep_list if l == layer_idx and r == roi_idx),
                (layer_idx, roi_idx, self.global_laser_intensity, diameter_value)
            )
            image_plot.create_or_update_circle(
                roi_idx=roi_idx,
                center=(roi.x_center, roi.y_center),
                alpha=intensity_value,
                diameter=diameter_value,
                label=f"ROI {roi_idx}"
            )

    # def on_intensity_changed(self, intensity_edit: QtWidgets.QLineEdit, layer_idx: int, roi_idx: int) -> None:
    #     """
    #     Handle editing finished for intensity field.
    #
    #     Args:
    #         intensity_edit: QLineEdit widget
    #         layer_idx: Layer index
    #         roi_idx: ROI index
    #     """
    #     text = intensity_edit.text()
    #     try:
    #         intensity_value = float(text)
    #         intensity_value = max(0.0, min(intensity_value, 100.0))
    #         intensity_edit.setText(str(intensity_value))
    #     except ValueError:
    #         intensity_value = self.global_laser_intensity
    #         intensity_edit.setText(str(intensity_value))
    #
    #     # Update laser prep list
    #     for idx, entry in enumerate(self.laser_prep_list):
    #         if entry[0] == layer_idx and entry[1] == roi_idx:
    #             self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value)

    # -------------------------
    # Global controls
    # -------------------------
    # def set_all_laser_intensity(self) -> None:
    #     """
    #     Apply global laser intensity to all ROI intensity spin boxes and update internal list.
    #     """
    #     # Get the value from the global intensity spin box (or fallback)
    #     intensity_value = self.intensity_field.value() if hasattr(self.intensity_field,
    #                                                               "value") else self.global_laser_intensity
    #     self.global_laser_intensity = intensity_value
    #
    #     # Update the laser prep list
    #     for idx, (layer_idx, roi_idx, _, diameter) in enumerate(self.laser_prep_list):
    #         self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value, diameter)
    #
    #     # Update all circles in the image plots
    #     for image_plot in self.image_plots.values():
    #         image_plot.update_all_circle_intensity(intensity_value)
    #
    #     # Update all enabled intensity spin boxes
    #     for checkbox, intensity_spin, diameter_spin, layer_idx, roi_idx in self.roi_widgets:
    #         if intensity_spin.isEnabled():
    #             intensity_spin.setValue(intensity_value)
    #
    #     # Clear the global intensity field if needed (optional)
    #     if hasattr(self.intensity_field, "clear"):
    #         self.intensity_field.clear()
    def set_all_laser_intensity(self) -> None:
        """
        Apply the global laser intensity to all ROI intensity fields and update the internal laser_prep_list.
        Triggered when the user modifies the global intensity input field.
        """

        # -----------------------
        # 1. Read and validate global intensity
        # -----------------------
        try:
            # Attempt to read the value from the intensity QLineEdit
            intensity_value = float(self.intensity_field.text())/100
            # Clamp the value to a valid range (0.0 to 1.0)
            intensity_value = max(0.0, min(intensity_value, 1))
        except ValueError:
            # Invalid input (empty or non-numeric) → fallback to the current global intensity
            intensity_value = self.global_laser_intensity

        # Update the stored global laser intensity
        self.global_laser_intensity = intensity_value

        # -----------------------
        # 2. Update all entries in the laser_prep_list
        # -----------------------
        # Each entry is a tuple: (layer_idx, roi_idx, intensity, diameter)
        for idx, (layer_idx, roi_idx, _, diameter) in enumerate(self.laser_prep_list):
            # Replace the intensity with the new global intensity while keeping the diameter
            self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value, diameter)

        # -----------------------
        # 3. Update all circles in all image plots
        # -----------------------
        for image_plot in self.image_plots.values():
            # Update the intensity of all ROI circles to match the new global intensity
            image_plot.update_all_circle_intensity(intensity_value)

        # -----------------------
        # 4. Update all enabled intensity fields in the ROI widgets
        # -----------------------
        # ROI widgets store: (checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx)
        for checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx in self.roi_widgets:
            if intensity_edit.isEnabled():
                # Reflect the new global intensity in each ROI intensity QLineEdit
                intensity_edit.setValue(intensity_value)

        # -----------------------
        # 5. Clear the global intensity input field (optional UX choice)
        # -----------------------
        self.intensity_field.clear()

    def toggle_all_roi_for_laser(self) -> None:
        """
        Toggle all ROI prep checkboxes on/off.
        """
        all_on = len(self.laser_prep_list) == len(self.roi_widgets)
        new_state = not all_on
        for checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx in self.roi_widgets:
            checkbox.setChecked(new_state)

    # def update_all_circle_diameters(self) -> None:
    #     """
    #     Update diameter of all visible circles across all layers.
    #     """
    #     try:
    #         self.global_roi_diameter = float(self.diameter_field.text())
    #     except ValueError:
    #         return
    #
    #     for image_plot in self.image_plots.values():
    #         image_plot.update_all_circle_diameters(self.global_roi_diameter)

    def update_all_circle_diameters(self) -> None:
        """
        Apply the global ROI diameter to all visible circles and update the internal laser_prep_list.
        This is triggered when the user modifies the global diameter field.
        """

        # -----------------------
        # 1. Read and validate global diameter
        # -----------------------
        try:
            # Attempt to read the value from the diameter QLineEdit
            self.global_roi_diameter = float(self.diameter_field.text())
            # Clamp the value to a sensible range (1 to 500 pixels)
            self.global_roi_diameter = max(1.0, min(500.0, self.global_roi_diameter))
        except ValueError:
            # Invalid input (empty or non-numeric) → do nothing
            return

        # -----------------------
        # 2. Update all circles in all image plots
        # -----------------------
        for image_plot in self.image_plots.values():
            # This function should update all visible ROI circles to use the new diameter
            image_plot.update_all_circle_diameters(self.global_roi_diameter)

        # -----------------------
        # 3. Update all entries in the laser_prep_list
        # -----------------------
        # Each entry is a tuple: (layer_idx, roi_idx, intensity, diameter)
        for idx, (layer_idx, roi_idx, intensity, diameter) in enumerate(self.laser_prep_list):
            # Replace the diameter with the new global diameter while keeping the intensity
            self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity, self.global_roi_diameter)

        # -----------------------
        # 4. Update all enabled diameter fields in the ROI widgets
        # -----------------------
        # ROI widgets store: (checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx)
        for checkbox, intensity_edit, diameter_edit, layer_idx, roi_idx in self.roi_widgets:
            if diameter_edit.isEnabled():
                # Reflect the new global diameter in each ROI diameter QLineEdit
                diameter_edit.setValue(self.global_roi_diameter)

        # -----------------------
        # 5. Clear the global diameter input field (optional UX choice)
        # -----------------------
        self.diameter_field.clear()

    # -------------------------
    # Frame & plot updates
    # -------------------------
    def update_frame(self) -> None:
        """
        Pull recent frames for each layer and update plots with mean or std.
        """
        for layer_idx, image_plot in self.image_plots.items():
            idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}', last=10)
            if len(idx) == 0:
                continue

            frame_avg = np.mean(frame, axis=0) if self.mode == "mean" else np.std(frame, axis=0)
            image_plot.update_frame(frame_avg)

    def build_image_plots(self, num_layers: int) -> None:
        """
        Build image plots grid for a given number of layers.

        Args:
            num_layers: Number of layers to display
        """
        if num_layers <= 0:
            print("Cannot build image plots with 0 layers.")
            return

        self.layer_num = num_layers
        self.image_tiles.clear()
        self.image_plots.clear()

        self.cols = math.ceil(math.sqrt(num_layers))
        self.rows = math.ceil(math.sqrt(num_layers))

        for i in range(num_layers):
            image_plot = ImagePlot(i)
            self.image_plots[i] = image_plot
            self.image_tiles.addItem(image_plot.plot_item, row=i // self.cols, col=i % self.cols)

        print(f"Built {num_layers} image plots.")

    # -------------------------
    # File & hardware operations
    # -------------------------
    def write_SysCon_file(self) -> None:
        """
        Export current laser-prepared ROIs to a SysCon file.
        """
        writer = SysconFileWriter()
        header = SysconHeader()
        writer.add_header(header)

        number_of_entities = 0

        for idx, (layer_idx, roi_idx, laser_intensity, diameter) in enumerate(self.laser_prep_list):
            roi = SysConRoutine.instance().rois_to_stimulate[(layer_idx, roi_idx)]
            temp_roi = CircleROI(idx)
            temp_roi.set_center(x=roi.x_center, y=roi.y_center, z=roi.z_center)
            temp_roi.set_laster_intensity(laser_intensity)
            temp_roi.add_vertex(x=diameter, y=diameter)
            writer.add_roi(temp_roi)
            number_of_entities += 1

        ttl_trigger = SysconTTL(number_of_entities, ttl_type="WaitForTTL")
        writer.add_TTL(ttl_trigger)


        writer.save()
        print(f"SysCon file {writer.filename} written successfully.")

    def upload_and_wait(self) -> None:
        """
        Placeholder for hardware upload. Prints current scanning parameters.
        """
        print(f"Scan mode: {self.scanning_combo.currentText()}, "
              f"Diameter: {self.diameter_field.text()}, "
              f"Duration: {self.duration_field.text()}")


class ImagePlot:
    """
    A class for displaying an image with ROI circles and optional mask overlays using PyQtGraph.

    Attributes
    ----------
    layer_idx : int
        Index of the image layer.
    plot_item : pg.PlotItem
        The plot item containing the image and ROIs.
    image_item : pg.ImageItem
        The main image display item.
    mask_item : pg.ImageItem
        Optional mask overlay with adjustable opacity.
    text : pg.TextItem
        Label for the image layer.
    circles : dict
        Stores ROI circles and associated text items keyed by ROI index.
    """

    def __init__(self, layer_idx: int):
        """
        Initialize an ImagePlot instance.

        Parameters
        ----------
        layer_idx : int
            Index of the image layer.
        """
        self.layer_idx = layer_idx
        self.no_init = True

        # Initialize main plot and image
        self.plot_item = pg.PlotItem()
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        self.plot_item.invertY(True)
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.plot_item.setAspectLocked(True)

        # Optional mask overlay
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)
        self.mask_item.setVisible(False)
        self.plot_item.addItem(self.mask_item)

        # Layer label
        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.plot_item.addItem(self.text)
        self.text.setPos(0, 0)

        # Dictionary to hold ROI circles
        self.circles = {}  # roi_idx -> dict with ellipse, text, center, diameter

    def update_frame(self, frame):
        """
        Update the displayed image.

        Parameters
        ----------
        frame : np.ndarray
            Image frame to display.
        """
        if self.no_init:
            self.image_item.setImage(frame, autoLevels=False, levels=(frame.min(), frame.max()))
            self.no_init = False
        self.image_item.setImage(frame, autoLevels=False)

    def create_or_update_circle(self, roi_idx, center, diameter, label=None,
                                alpha=0.0,  # transparency controller: 0=transparent, 1=opaque
                                fill_color=(0, 255, 0),  # RGB only, alpha handled separately
                                pen_color=(255, 0, 0)):
        """
        Create or update a circular ROI.

        Parameters
        ----------
        alpha : float
            Fill transparency between 0 and 1.
            0 = fully transparent, 1 = fully opaque.
        fill_color : tuple of int
            RGB color for the fill (alpha handled separately).
        """
        radius = diameter / 2
        y = center[0] - radius
        x = center[1] - radius

        # convert alpha 0–1 to Qt 0–255
        qt_alpha = int(max(0, min(0.5, alpha/2)) * 255)
        fill_rgba = (*fill_color, qt_alpha)

        if roi_idx not in self.circles:
            ellipse = QGraphicsEllipseItem(x, y, diameter, diameter)
            ellipse.setBrush(QBrush(QColor(*fill_rgba)))
            ellipse.setPen(QPen(QColor(*pen_color)))
            ellipse.setZValue(10)
            self.plot_item.addItem(ellipse)

            text_item = pg.TextItem(label or f'ROI {roi_idx}', anchor=(0.5, 0.5), color=pen_color)
            text_item.setPos(center[1], center[0])
            text_item.setZValue(11)
            self.plot_item.addItem(text_item)

            self.circles[roi_idx] = {
                'ellipse': ellipse,
                'text': text_item,
                'center': center,
                'diameter': diameter,
                'alpha': alpha
            }
        else:
            ellipse = self.circles[roi_idx]['ellipse']
            text_item = self.circles[roi_idx]['text']
            ellipse.setRect(x, y, diameter, diameter)
            ellipse.setBrush(QBrush(QColor(*fill_rgba)))
            text_item.setPos(center[1], center[0])
            self.circles[roi_idx]['center'] = center
            self.circles[roi_idx]['diameter'] = diameter
            self.circles[roi_idx]['alpha'] = alpha

    def set_circle_visible(self, roi_idx: int, visible: bool):
        """
        Show or hide the circle and label for a given ROI.

        Parameters
        ----------
        roi_idx : int
            Identifier of the ROI.
        visible : bool
            True to show, False to hide.
        """
        if roi_idx in self.circles:
            self.circles[roi_idx]['ellipse'].setVisible(visible)
            self.circles[roi_idx]['text'].setVisible(visible)

    def update_all_circle_diameters(self, new_diameter: float):
        for roi_idx, info in self.circles.items():
            self.create_or_update_circle(
                roi_idx,
                info['center'],
                new_diameter,
                alpha=info['alpha'],
                fill_color=info.get('fill_color', (0, 255, 0)),
                pen_color=info.get('pen_color', (255, 0, 0)),
                label=info['text'].toPlainText()
            )

    def update_all_circle_intensity(self, new_intensity: float):
        for roi_idx, info in self.circles.items():
            self.create_or_update_circle(
                roi_idx,
                info['center'],
                info['diameter'],
                alpha=new_intensity,
                fill_color=info.get('fill_color', (0, 255, 0)),
                pen_color=info.get('pen_color', (255, 0, 0)),
                label=info['text'].toPlainText()
            )

# class SysconHeader:
#     """
#     Represents a SysconHeader object that encapsulates configuration data for a specific system
#     or device setup and outputs it in a structured text format.
#
#     The class contains multiple attributes tied to configuration parameters, such as device
#     sequences, scan modes, auto trigger rules, and timeline settings. This data can be exported
#     to a `.txt`-formatted string for saving, viewing, or logging purposes.
#
#     :ivar name: Unique identifier or name of the SysconHeader.
#     :type name: str
#     :ivar version: Version number of the SysconHeader configuration.
#     :type version: str
#     :ivar scanmode: Scan mode setting (e.g., Accurate).
#     :type scanmode: str
#     :ivar runs: Number of execution runs for this configuration.
#     :type runs: str
#     :ivar DeviceSequenceID: Identifier for the device sequence.
#     :type DeviceSequenceID: str
#     :ivar invertedportcnt: Number of inverted ports associated with this configuration.
#     :type invertedportcnt: str
#     :ivar inverted0: Description of the first inverted port.
#     :type inverted0: str
#     :ivar AutoTriggerRulesCount: Number of auto-trigger rules defined.
#     :type AutoTriggerRulesCount: str
#     :ivar AutoTriggerRulesEnabled: Status indicating whether auto-trigger rules are enabled.
#     :type AutoTriggerRulesEnabled: str
#     :ivar timelinezoomfactor: Zoom factor for the timeline setting.
#     :type timelinezoomfactor: str
#     :ivar timelineviewposx: Horizontal view position for the timeline.
#     :type timelineviewposx: str
#     :ivar timelineviewposy: Vertical view position for the timeline.
#     :type timelineviewposy: str
#     :ivar TotalEditorGroups: Total groups in the editor associated with this configuration.
#     :type TotalEditorGroups: str
#     """
    # def __init__(self):
    #     self.name = "0E-04-16-81-9A-39-D0-E8-88-7E-A6-6A-FC-25-A0-2A"
    #     self.version = "2"
    #     self.scanmode = "Accurate"
    #     self.runs = "1"
    #     self.DeviceSequenceID = "0"
    #     self.invertedportcnt = "1"
    #     self.inverted0 = "240-2971_0 RMI In"
    #     self.AutoTriggerRulesCount = "0"
    #     self.AutoTriggerRulesEnabled = "False"
    #     self.timelinezoomfactor = "73"
    #     self.timelineviewposx = "0"
    #     self.timelineviewposy = "0"
    #     self.TotalEditorGroups = "0"
    #
    # def to_txt(self):
    #     lines = []
    #     lines.append(self.name)
    #     lines.append(f"version={self.version}")
    #     lines.append(f"scanmode={self.scanmode}")
    #     lines.append(f"runs={self.runs}")
    #     lines.append(f"DeviceSequenceID={self.DeviceSequenceID}")
    #     lines.append(f"invertedportcnt={self.invertedportcnt}")
    #     lines.append(f"inverted0={self.inverted0}")
    #     lines.append(f"AutoTriggerRulesCount={self.AutoTriggerRulesCount}")
    #     lines.append(f"AutoTriggerRulesEnabled={self.AutoTriggerRulesEnabled}")
    #     lines.append(f"timelinezoomfactor={self.timelinezoomfactor}")
    #     lines.append(f"timelineviewposx={self.timelineviewposx}")
    #     lines.append(f"timelineviewposy={self.timelineviewposy}")
    #     lines.append(f"TotalEditorGroups={self.TotalEditorGroups}")
    #     return "\n".join(lines)

class SysconHeader():
    """
    Represents the header of a Syscon sequence file.

    This class encapsulates global configuration settings for a Syscon
    sequence file (.seq), including scan mode, run counts, inverted ports,
    auto-trigger rules, and timeline view settings. The header is written
    at the top of the sequence file.

    Attributes
    ----------
    nohash : str
        Literal value 'nohash' for the header.
    version : str
        Version of the Syscon file format.
    scanmode : str
        Scan mode setting (e.g., 'Accurate').
    runs : str
        Number of runs to execute the sequence (0 = infinite).
    DeviceSequenceID : str
        Identifier for the device sequence (usually irrelevant for users).
    invertedportcnt : str
        Number of TTL ports that are inverted.
    inverted0 : str
        Name of the first inverted TTL port.
    AutoTriggerRulesEnabled : str
        Whether automatic TTL triggering is enabled ('True' or 'False').
    AutoTriggerRulesCount : str
        Number of auto-trigger rules defined.
    timelinezoomfactor : str
        Zoom factor for timeline view (visualization only).
    timelineviewposx : str
        Horizontal view position in timeline UI (visualization only).
    timelineviewposy : str
        Vertical view position in timeline UI (visualization only).
    """

    # Methods: __init__, as_dict, to_txt

    def __init__(self):
        self.nohash = "nohash"  # literal entry, not a variable name
        self.version = "3"
        self.scanmode = "Accurate"
        self.runs = "1"
        self.DeviceSequenceID = "1"
        self.invertedportcnt = "1"
        self.inverted0 = "UGA-42 TTL Out 1"
        self.AutoTriggerRulesEnabled = "False"
        self.AutoTriggerRulesCount = "0"
        self.timelinezoomfactor = "0"
        self.timelineviewposx = "0"
        self.timelineviewposy = "0"
        # You can still include TotalEditorGroups if older tools expect it:
        # self.TotalEditorGroups = "0"

    def as_dict(self):
        """Return ordered key-value pairs reflecting the new export structure."""
        return {
            "nohash": self.nohash,
            "version": self.version,
            "scanmode": self.scanmode,
            "runs": self.runs,
            "DeviceSequenceID": self.DeviceSequenceID,
            "invertedportcnt": self.invertedportcnt,
            "inverted0": self.inverted0,
            "AutoTriggerRulesEnabled": self.AutoTriggerRulesEnabled,
            "AutoTriggerRulesCount": self.AutoTriggerRulesCount,
            "timelinezoomfactor": self.timelinezoomfactor,
            "timelineviewposx": self.timelineviewposx,
            "timelineviewposy": self.timelineviewposy,
        }

    def to_text(self):
        """Export to updated .txt-style block for .seq file."""
        data = self.as_dict()
        lines = [data["nohash"]]  # first line is literal 'nohash'
        for key, value in data.items():
            if key != "nohash":
                lines.append(f"{key}={value}")
        return "\n".join(lines)


class SysconEntity:
    """
    Base class for all Syscon sequence entities, including ROIs (shapes)
    and TTL events.

    This class defines shared attributes like ID, timeline information,
    repeats, lightsource references, and the block formatting required
    to generate a valid Syscon file section.

    Subclasses should override `_subclass_block()` to include
    type-specific fields.

    Attributes
    ----------
    block_index : int
        The index used to identify the entity block in the sequence file.
    entity_type : str
        Type of the entity ('Shape', 'TTLPulse', 'WaitForTTL', etc.).
    entity_id : int
        Unique identifier for the entity (usually block_index + 1).
    data : dict
        Dictionary of common timeline-related fields such as repeats,
        lightsource info, stepsize, and timeline index.
    """

    # Methods: __init__, set, get, _base_block, _subclass_block, to_text, __repr__

    def __init__(self, block_index: int, entity_type: str = "Shape"):
        self.block_index = block_index
        self.entity_type = entity_type
        self.entity_id = self.block_index + 1

        # Common Syscon timeline fields
        self.data = {
            "ID": self.entity_id,
            "type": self.entity_type,
            "TotalTimings": 1,
            "TimelineInfo0_TimelineIndex": 0,
            "TimelineInfo0_starttime": 0,
            "TimelineInfo0_description": "",
            "TimelineInfo0_repeats": 1,
            "TimelineInfo0_LightsourceCount": 1,
            "TimelineInfo0_LightsourceID_0": "240-2971_0", #for the
            "TimelineInfo0_Intensity_0": 0.0,
            "TimelineInfo0_timelinegroupid": -1,
            "TimelineInfo0_Stepsize": 1
        }

    def set(self, key: str, value):
        """Sets a field in the entity dictionary."""
        if key in self.data:
            self.data[key] = value
        else:
            raise KeyError(f"Invalid SysconEntity key: {key}")

    def set_laster_intensity(self, value):
        self.data["TimelineInfo0_Intensity_0"] = value


    def get(self, key: str):
        """Gets a field value from the entity dictionary."""
        return self.data.get(key, None)

    def _base_block(self) -> str:
        """Return the base Syscon lines for this entity (no subclass fields)."""
        # Define the desired order of keys
        keys_order = [
            "ID",
            "type",
            "TotalTimings",
            "TimelineInfo0_TimelineIndex",
            "TimelineInfo0_starttime",
            "TimelineInfo0_description",
            "TimelineInfo0_repeats",
            "TimelineInfo0_LightsourceCount",
            "TimelineInfo0_LightsourceID_0",
            "TimelineInfo0_Intensity_0",
            "TimelineInfo0_timelinegroupid",
            "TimelineInfo0_Stepsize"
        ]

        lines = []
        for key in keys_order:
            # Only include keys that exist in self.data
            if key in self.data:
                lines.append(f"{key}={self.data[key]}")

        return "\n".join(lines)


    def _subclass_block(self) -> str:
        """
        Placeholder for subclass-specific content.
        Subclasses should override this to add extra parameters.
        """
        return "(here should the subclass output be written)"

    def to_text(self) -> str:
        """Return the full formatted Syscon block."""
        header = f"[{self.block_index}]"
        footer = f"[/{self.block_index}]"
        return f"{header}\n{self._base_block()}\n{self._subclass_block()}\n{footer}"

    def __repr__(self):
        return f"<SysconEntity block={self.block_index} ID={self.entity_id} type={self.entity_type}>"


class SysconROI(SysconEntity):
    """
    Base class for all Region of Interest (ROI) shapes in a Syscon sequence file.

    This class stores all shape-generic fields defined by the Syscon .seq
    format and provides the common block output logic. Subclasses represent
    specific shape types and enforce their own vertex requirements.

    The Syscon format defines five ROI types:
        0 : Point
        1 : Line
        2 : Circle
        3 : Rectangle
        4 : Polygon

    All shapes share:
    - A "center" position (CenterX, CenterY, CenterZ)
    - An optional rotation
    - A scale factor
    - A vertex list (X, Y, Z tuples), interpreted differently per shape
    - A consistent block output format: ShapeN_FieldName=value
    """

    def __init__(self, block_index: int, shape_type: int):
        super().__init__(block_index, entity_type="Shape")

        self.shape_data = {
            "Type": shape_type,
            "Filled": True,
            "CenterX": 0.0,
            "CenterY": 0.0,
            "CenterZ": 0.0,
            "Rotation": 0.0,
            "Scale": 1.0,
            "VerticesCount": 0,
            "VerticesToDrawCount": 0,
            "TranslationVerticesCount": 0,
            "Reversed": False,
            "GroupID": -1,
            "Linewidth": 1.0,
        }

        # List of (x, y, z) vertices. Subclasses control allowed count.
        self.vertices = []

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        """
        Adds a vertex to the shape. Subclasses override this to enforce
        vertex-count rules appropriate to the Syscon shape type.
        """
        self.vertices.append((x, y, z))
        self.shape_data["VerticesCount"] = len(self.vertices)

    def set_shape(self, key: str, value):
        """Sets a field in the entity dictionary."""
        if key in self.shape_data:
            self.shape_data[key] = value
        else:
            raise KeyError(f"Invalid SysconEntity key: {key}")

    def set_center(self, x: float, y: float, z: float = 0.0):
        """Sets the center position of the shape."""
        self.shape_data["CenterX"] = x
        self.shape_data["CenterY"] = y
        self.shape_data["CenterZ"] = z



    def _subclass_block(self) -> str:
        """
        Generates the ShapeN_… block containing all Syscon-specific fields.

        Subclasses inherit this unless they need to modify output layout.
        """
        prefix = f"Shape{self.block_index}_"
        lines = []

        # Write all generic shape fields
        for key, value in self.shape_data.items():
            lines.append(f"{prefix}{key}={value}")

        # Write vertex data
        for i, (x, y, z) in enumerate(self.vertices):
            lines.append(f"{prefix}Vertex{i}_X={x}")
            lines.append(f"{prefix}Vertex{i}_Y={y}")
            lines.append(f"{prefix}Vertex{i}_Z={z}")

        return "\n".join(lines)

    def __repr__(self):
        return f"<SysconROI block={self.block_index} ID={self.entity_id} Type={self.shape_data['Type']} Vertices={len(self.vertices)}>"

class DotROI(SysconROI):
    """
    Represents a point-type ROI (Syscon Type 0).

    A point does not use any vertices; all geometric meaning comes from its
    center coordinates. Attempts to add vertices raise an exception.
    """

    def __init__(self, block_index: int):
        super().__init__(block_index, shape_type=0)

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        raise ValueError("DotROI does not support vertices.")

class LineROI(SysconROI):
    """
    Represents a line-type ROI (Syscon Type 1).

    A line is defined by exactly two vertices, given relative to the center.
    Attempts to add more than two vertices are not allowed.
    """

    def __init__(self, block_index: int):
        super().__init__(block_index, shape_type=1)

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        if len(self.vertices) >= 2:
            raise ValueError("LineROI requires exactly two vertices.")
        super().add_vertex(x, y, z)

class CircleROI(SysconROI):
    """
    Represents a circle-type ROI (Syscon Type 2).

    Syscon circles use a single vertex representing a radius vector.
    This vector, combined with the scale factor, determines the circle size.
    """

    def __init__(self, block_index: int):
        super().__init__(block_index, shape_type=2)

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        if len(self.vertices) >= 1:
            raise ValueError("CircleROI uses exactly one radius vector vertex.")
        super().add_vertex(x, y, z)

class RectangleROI(SysconROI):
    """
    Represents a rectangle-type ROI (Syscon Type 3).

    A rectangle is defined by four vertices relative to its center.
    The ordering defines the drawing direction. Reversed=True flips the order.
    """

    def __init__(self, block_index: int):
        super().__init__(block_index, shape_type=3)

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        if len(self.vertices) >= 4:
            raise ValueError("RectangleROI requires exactly four vertices.")
        super().add_vertex(x, y, z)

class PolygonROI(SysconROI):
    """
    Represents a polygon-type ROI (Syscon Type 4).

    Polygons support any number of vertices (three or more). Vertices are
    interpreted relative to the shape center. Drawing order is clockwise
    unless Reversed=True.
    """

    def __init__(self, block_index: int):
        super().__init__(block_index, shape_type=4)

    def add_vertex(self, x: float, y: float, z: float = 0.0):
        super().add_vertex(x, y, z)

    def finalize(self):
        """
        Optional helper ensuring the polygon has enough vertices before export.
        Call this before writing to file if desired.
        """
        if len(self.vertices) < 3:
            raise ValueError("PolygonROI requires at least three vertices.")


class SysconTTL(SysconEntity):
    """
    Represents a TTL signal entity in a Syscon sequence file.

    A SysconTTL instance can represent either a TTL output pulse
    ('TTLPulse') or a TTL input/wait condition ('WaitForTTL').
    The entity stores port information and, for WaitForTTL, an
    optional edge-trigger behaviour ("rise" or "fall").

    Relationship to TimelineInfo fields
    ----------------------------------
    TTL entities rely on the parent SysconEntity's timeline fields.
    In particular:

        * If the TTL action targets a **lightsource**, the parent
          entity must specify:
              TimelineInfo0_LightsourceCount = 1

        * If the TTL action targets a **controller port** (i.e. a
          standard hardware TTL line), then:
              TimelineInfo0_LightsourceCount = 0

    Attributes
    ----------
    ttl_data : dict
        TTL-specific configuration values:
            port : str
                Name of the TTL input/output port.
            behaviour : str or None
                For 'WaitForTTL' entities only. Defines the required
                signal edge: "rise" or "fall".

    Methods
    -------
    set_port(port_name)
        Assign the TTL port for this entity.

    set_behaviour(behaviour)
        Assign the rising or falling edge behaviour. Valid only for
        'WaitForTTL' entities.

    _subclass_block()
        Generate TTL-specific key-value lines for inclusion in the
        Syscon output block.

    """

    #TODO: repeats: Wiederholungen der Ticktime des Systems (UGA-42 Systeme: 50us, Holo Systeme: 500us), 0 = 1 Ticktime


    def __init__(self, block_index: int, ttl_type: str = "TTLPulse", target_lasers = 0):
        super().__init__(block_index, entity_type=ttl_type)

        self.ttl_data = {
            "port": "UGA-42TTL In 1", #TODO
            "behaviour": None
        }

        if ttl_type == "WaitForTTL":
            self.ttl_data["behaviour"] = "rise"

        # Set Lightsource fields if targeting a laser
        if target_lasers:
            self.data["TimelineInfo0_LightsourceCount"] = target_lasers
            self.data["TimelineInfo0_LightsourceID_0"] = "2971_0"
            self.data["TimelineInfo0_Intensity_0"] = 0

        else:
            # Controller TTL output -> remove lightsource info
            self.data["TimelineInfo0_LightsourceCount"] = target_lasers
            self.data.pop("TimelineInfo0_LightsourceID_0", None)
            self.data.pop("TimelineInfo0_Intensity_0", None)


    def set_port(self, port_name: str):
        """Sets the TTL port name."""
        self.ttl_data["port"] = port_name

    def set_behaviour(self, behaviour: str):
        """Sets the behaviour (for WaitForTTL type only)."""
        if self.entity_type != "WaitForTTL":
            raise ValueError("Behaviour can only be set for WaitForTTL entities")
        if behaviour not in ("rise", "fall"):
            raise ValueError("Invalid TTL behaviour: must be 'rise' or 'fall'")
        self.ttl_data["behaviour"] = behaviour


    def _subclass_block(self) -> str:
        """
        Generates the TTL-specific output block.

        Enforces:
            TotalTimings must be exactly 1.
        """
        if self.data["TotalTimings"] != 1:
            raise ValueError(
                f"SysconTTL requires TotalTimings = 1, found {self.data['TotalTimings']}"
            )

        lines = [f"port={self.ttl_data['port']}"]
        if self.ttl_data["behaviour"] is not None:
            lines.append(f"behaviour={self.ttl_data['behaviour']}")
        return "\n".join(lines)

    def __repr__(self):
        return (
            f"<SysconTTL block={self.block_index} "
            f"ID={self.entity_id} type={self.entity_type} "
            f"port={self.ttl_data['port']}>"
        )





class SysconFileWriter:
    """
    Handles writing Syscon sequence files with headers and ROI definitions.

    Attributes
    ----------
    header : SysconHeader
        The header information for the sequence file.
    rois : list
        List of ROI objects to include in the file.
    filename : str
        Name of the output sequence file.
    """

    def __init__(self, filename: str = None):
        """
        Initialize the SysconFileWriter.

        Parameters
        ----------
        filename : str, optional
            Filename to save as. If None, generates a timestamped default name.
        """
        self.header = SysconHeader()
        self.rois = []
        self.TTLs = []

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = f"Syscon_test_{timestamp}.seq"
        else:
            # Ensure filename ends with .seq
            if not filename.endswith(".seq"):
                filename += ".seq"
            self.filename = filename

    def save(self, filepath: str = "~/Documents/Test_syscon_files"):
        """
        Save the Syscon file to disk.

        Parameters
        ----------
        filepath : str
            Directory path where the file will be saved. Defaults to ~/Documents/Test_syscon_files.
        """
        filepath = os.path.expanduser(filepath)
        os.makedirs(filepath, exist_ok=True)

        full_path = os.path.join(filepath, self.filename)

        with open(full_path, 'w') as f:
            f.write(self.header.to_text())
            f.write("\n")
            for roi in self.rois:
                f.write(roi.to_text())
                f.write("\n")
            for TTL in self.TTLs:
                f.write(TTL.to_text())
                f.write("\n")

    def upload_via_tcp(self):
        #TODO: implement this
        raise Exception("Not yet implemented")


    def add_header(self, header):
        """
        Replace the current header.

        Parameters
        ----------
        header : SysconHeader
            New header to use.
        """
        self.header = header

    def add_roi(self, roi):
        """
        Add an ROI to the list.

        Parameters
        ----------
        roi : ROI
            ROI object to append.
        """
        self.rois.append(roi)

    def add_TTL(self, TTL):
        """
        Add a TTL to the list.

        Parameters
        ----------
        TTL : SysconTTL
            TTL object to append.
        """
        self.TTLs.append(TTL)
