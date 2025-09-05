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

    rois_to_stimulate: dict = {}
    new_rois_set: bool = False
    num_layers: int = 0
    ui_update_rois: bool = False

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
        routine = SysConRoutine.instance()

        if routine.new_rois_set:
            # Print received ROIs (for debug/logging purposes)
            print(routine.rois_to_stimulate)

            # Reset flags after processing
            routine.new_rois_set = False
            routine.ui_update_rois = True

        else:
            # Placeholder for other routine processing if needed
            pass


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
        self.global_laser_intensity: float = 0.0
        self.laser_prep_list: list = []
        self.roi_widgets: list[tuple] = []  # Tuples: (checkbox, intensity_edit, layer_idx, roi_idx)

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

        # --- Toggle all ROIs
        self.toggle_all_button = QtWidgets.QPushButton("Toggle all ROIs for laser")
        self.toggle_all_button.clicked.connect(self.toggle_all_roi_for_laser)
        button_layout.addWidget(self.toggle_all_button)

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

        # Filter only tracked ROIs
        tracked_rois = [
            ((layer_idx, roi_idx), roi)
            for (layer_idx, roi_idx), roi in roi_dict.items()
            if roi.tracked
        ]

        # Clear old widgets & internal tracking lists
        self.clear_layout(self.scroll_layout)
        self.roi_widgets.clear()
        self.laser_prep_list.clear()

        for row_idx, ((layer_idx, roi_idx), roi) in enumerate(tracked_rois):
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
            prep_checkbox = QtWidgets.QCheckBox("Prep Laser")
            prep_checkbox.setChecked(roi.prep_laser)

            # -----------------------
            # Intensity field
            # -----------------------
            intensity_edit = QtWidgets.QLineEdit()
            intensity_edit.setPlaceholderText("Intensity")
            intensity_edit.setFixedWidth(80)

            initial_intensity = self.global_laser_intensity
            if roi.prep_laser:
                intensity_edit.setText(str(initial_intensity))
                intensity_edit.setEnabled(True)
                self.laser_prep_list.append((layer_idx, roi_idx, initial_intensity))
            else:
                intensity_edit.setEnabled(False)

            # Track widgets for later updates
            self.roi_widgets.append((prep_checkbox, intensity_edit, layer_idx, roi_idx))

            # -----------------------
            # Connect checkbox signal
            # -----------------------
            def on_checkbox_toggled(state, l=layer_idx, r=roi_idx, edit=intensity_edit):
                self.on_checkbox_toggled(state, l, r, edit)

            prep_checkbox.stateChanged.connect(on_checkbox_toggled)

            # -----------------------
            # Connect intensity editing signal
            # -----------------------
            def on_intensity_changed(edit_widget, l_idx, r_idx):
                """Validate and store intensity value."""
                text = edit_widget.text()
                try:
                    val = float(text)
                    val = max(0.0, min(100.0, val))  # clamp 0-100
                except ValueError:
                    val = 0.0
                edit_widget.setText(str(int(val)))

                # Update laser_prep_list
                for idx, entry in enumerate(self.laser_prep_list):
                    if entry[0] == l_idx and entry[1] == r_idx:
                        self.laser_prep_list[idx] = (l_idx, r_idx, val)

            intensity_edit.editingFinished.connect(
                partial(on_intensity_changed, intensity_edit, layer_idx, roi_idx)
            )

            # -----------------------
            # Combine widgets in a horizontal row
            # -----------------------
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(10)
            row_layout.addWidget(roi_label, stretch=3)
            row_layout.addWidget(prep_checkbox, stretch=1)
            row_layout.addWidget(intensity_edit, stretch=1)

            self.scroll_layout.addWidget(row_widget)

        # Ensure checkbox states are consistent with laser_prep_list
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            self.on_checkbox_toggled(checkbox.isChecked(), layer_idx, roi_idx, edit)

    # -------------------------
    # Signal handlers
    # -------------------------
    def on_checkbox_toggled(self, state: int, layer_idx: int, roi_idx: int, intensity_edit: QtWidgets.QLineEdit) -> None:
        """
        Handle ROI prep checkbox toggled.

        Args:
            state: Checkbox state (Qt.Checked / Qt.Unchecked)
            layer_idx: Layer of the ROI
            roi_idx: ROI index
            intensity_edit: Associated QLineEdit for intensity
        """
        roi = SysConRoutine.instance().rois_to_stimulate.get((layer_idx, roi_idx))
        if not roi:
            return

        image_plot = self.image_plots.get(layer_idx)
        if not image_plot:
            return

        is_checked = bool(state)
        intensity_edit.setEnabled(is_checked)

        diameter = self._get_diameter()

        image_plot.create_or_update_circle(
            roi_idx=roi_idx,
            center=(roi.x_center, roi.y_center),
            diameter=diameter,
            label=f"ROI {roi_idx}"
        )

        image_plot.set_circle_visible(roi_idx, is_checked)

        # Update internal laser prep list
        self.laser_prep_list = [
            entry for entry in self.laser_prep_list if not (entry[0] == layer_idx and entry[1] == roi_idx)
        ]
        if is_checked:
            try:
                intensity_value = float(intensity_edit.text())
            except ValueError:
                intensity_value = self.global_laser_intensity
                intensity_edit.setText(str(intensity_value))
            self.laser_prep_list.append((layer_idx, roi_idx, intensity_value))

    def on_intensity_changed(self, intensity_edit: QtWidgets.QLineEdit, layer_idx: int, roi_idx: int) -> None:
        """
        Handle editing finished for intensity field.

        Args:
            intensity_edit: QLineEdit widget
            layer_idx: Layer index
            roi_idx: ROI index
        """
        text = intensity_edit.text()
        try:
            intensity_value = float(text)
            intensity_value = max(0.0, min(intensity_value, 100.0))
            intensity_edit.setText(str(intensity_value))
        except ValueError:
            intensity_value = self.global_laser_intensity
            intensity_edit.setText(str(intensity_value))

        # Update laser prep list
        for idx, entry in enumerate(self.laser_prep_list):
            if entry[0] == layer_idx and entry[1] == roi_idx:
                self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value)

    # -------------------------
    # Global controls
    # -------------------------
    def set_all_laser_intensity(self) -> None:
        """
        Apply global laser intensity to all ROI intensity edits and internal list.
        """
        try:
            intensity_value = float(self.intensity_field.text())
            intensity_value = max(0.0, min(intensity_value, 100.0))
        except ValueError:
            intensity_value = self.global_laser_intensity

        self.global_laser_intensity = intensity_value

        # Update laser prep list and edits
        for idx, (layer_idx, roi_idx, _) in enumerate(self.laser_prep_list):
            self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value)
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            if edit.isEnabled():
                edit.setText(str(intensity_value))

        self.intensity_field.clear()

    def toggle_all_roi_for_laser(self) -> None:
        """
        Toggle all ROI prep checkboxes on/off.
        """
        all_on = len(self.laser_prep_list) == len(self.roi_widgets)
        new_state = not all_on
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            checkbox.setChecked(new_state)

    def update_all_circle_diameters(self) -> None:
        """
        Update diameter of all visible circles across all layers.
        """
        try:
            new_diameter = float(self.diameter_field.text())
        except ValueError:
            return

        for image_plot in self.image_plots.values():
            image_plot.update_all_circle_diameters(new_diameter)

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

        for idx, (layer_idx, roi_idx, laser_intensity) in enumerate(self.laser_prep_list):
            roi = SysConRoutine.instance().rois_to_stimulate[(layer_idx, roi_idx)]
            temp_roi = SysconROI(idx)
            temp_roi.CenterX = roi.x_center
            temp_roi.CenterY = roi.y_center
            temp_roi.CenterZ = roi.z_center
            temp_roi.Intensity = laser_intensity
            writer.add_roi(temp_roi)

        writer.save()
        print(f"SysCon file {writer.filename} written successfully.")

    def upload_and_wait(self) -> None:
        """
        Placeholder for hardware upload. Prints current scanning parameters.
        """
        print(f"Scan mode: {self.scanning_combo.currentText()}, "
              f"Diameter: {self.diameter_field.text()}, "
              f"Duration: {self.duration_field.text()}")

    # -------------------------
    # Helpers
    # -------------------------
    def _get_diameter(self) -> float:
        """Return diameter from input field or default if invalid."""
        try:
            return float(self.diameter_field.text())
        except ValueError:
            return 30.0



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
                                color=(0, 255, 0, 80), pen_color=(255, 0, 0)):
        """
        Create a new ROI circle or update an existing one.

        Parameters
        ----------
        roi_idx : int
            Unique identifier for the ROI.
        center : tuple of float
            (row, column) coordinates of the ROI center.
        diameter : float
            Diameter of the circle.
        label : str, optional
            Text label to display in the circle. Defaults to 'ROI {roi_idx}'.
        color : tuple of int, optional
            RGBA color of the circle fill. Defaults to (0, 255, 0, 80).
        pen_color : tuple of int, optional
            RGB color of the circle outline and label. Defaults to (255, 0, 0).
        """
        radius = diameter / 2
        y = center[0] - radius
        x = center[1] - radius

        if roi_idx not in self.circles:
            # Create new ellipse and text items
            ellipse = QGraphicsEllipseItem(x, y, diameter, diameter)
            ellipse.setBrush(QBrush(QColor(*color)))
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
                'diameter': diameter
            }
        else:
            # Update existing ellipse and text
            ellipse = self.circles[roi_idx]['ellipse']
            text_item = self.circles[roi_idx]['text']
            ellipse.setRect(x, y, diameter, diameter)
            text_item.setPos(center[1], center[0])
            self.circles[roi_idx]['center'] = center
            self.circles[roi_idx]['diameter'] = diameter

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
        """
        Update the diameter of all existing ROI circles.

        Parameters
        ----------
        new_diameter : float
            New diameter to apply to all circles.
        """
        for roi_idx, info in self.circles.items():
            self.create_or_update_circle(roi_idx, info['center'], new_diameter)

class SysconHeader:
    """
    Represents a SysconHeader object that encapsulates configuration data for a specific system
    or device setup and outputs it in a structured text format.

    The class contains multiple attributes tied to configuration parameters, such as device
    sequences, scan modes, auto trigger rules, and timeline settings. This data can be exported
    to a `.txt`-formatted string for saving, viewing, or logging purposes.

    :ivar name: Unique identifier or name of the SysconHeader.
    :type name: str
    :ivar version: Version number of the SysconHeader configuration.
    :type version: str
    :ivar scanmode: Scan mode setting (e.g., Accurate).
    :type scanmode: str
    :ivar runs: Number of execution runs for this configuration.
    :type runs: str
    :ivar DeviceSequenceID: Identifier for the device sequence.
    :type DeviceSequenceID: str
    :ivar invertedportcnt: Number of inverted ports associated with this configuration.
    :type invertedportcnt: str
    :ivar inverted0: Description of the first inverted port.
    :type inverted0: str
    :ivar AutoTriggerRulesCount: Number of auto-trigger rules defined.
    :type AutoTriggerRulesCount: str
    :ivar AutoTriggerRulesEnabled: Status indicating whether auto-trigger rules are enabled.
    :type AutoTriggerRulesEnabled: str
    :ivar timelinezoomfactor: Zoom factor for the timeline setting.
    :type timelinezoomfactor: str
    :ivar timelineviewposx: Horizontal view position for the timeline.
    :type timelineviewposx: str
    :ivar timelineviewposy: Vertical view position for the timeline.
    :type timelineviewposy: str
    :ivar TotalEditorGroups: Total groups in the editor associated with this configuration.
    :type TotalEditorGroups: str
    """
    def __init__(self):
        self.name = "0E-04-16-81-9A-39-D0-E8-88-7E-A6-6A-FC-25-A0-2A"
        self.version = "2"
        self.scanmode = "Accurate"
        self.runs = "1"
        self.DeviceSequenceID = "0"
        self.invertedportcnt = "1"
        self.inverted0 = "240-2971_0 RMI In"
        self.AutoTriggerRulesCount = "0"
        self.AutoTriggerRulesEnabled = "False"
        self.timelinezoomfactor = "73"
        self.timelineviewposx = "0"
        self.timelineviewposy = "0"
        self.TotalEditorGroups = "0"

    def to_txt(self):
        lines = []
        lines.append(self.name)
        lines.append(f"version={self.version}")
        lines.append(f"scanmode={self.scanmode}")
        lines.append(f"runs={self.runs}")
        lines.append(f"DeviceSequenceID={self.DeviceSequenceID}")
        lines.append(f"invertedportcnt={self.invertedportcnt}")
        lines.append(f"inverted0={self.inverted0}")
        lines.append(f"AutoTriggerRulesCount={self.AutoTriggerRulesCount}")
        lines.append(f"AutoTriggerRulesEnabled={self.AutoTriggerRulesEnabled}")
        lines.append(f"timelinezoomfactor={self.timelinezoomfactor}")
        lines.append(f"timelineviewposx={self.timelineviewposx}")
        lines.append(f"timelineviewposy={self.timelineviewposy}")
        lines.append(f"TotalEditorGroups={self.TotalEditorGroups}")
        return "\n".join(lines)


class SysconROI:
    def __init__(self, index):
        self.index = index
        self.type = "Entity"
        self.TotalTimings = 1
        self.TimelineIndex = index
        self.starttime = 0
        self.description = ""
        self.repeats = 0
        self.LightsourceCount = 1
        self.LightsourceID = "240-2971_0"
        self.Intensity = 0
        self.timelinegroupid = -1
        self.Stepsize = 100
        self.Entity_Type = 0
        self.Entity_Filled = False
        self.CenterX = 0
        self.CenterY = 0
        self.CenterZ = 0
        self.Rotation = 0
        self.ScaleX = 1
        self.ScaleY = 1
        self.ScaleZ = 1
        self.VertexCount = 0
        self.reversed = False

    def to_txt(self):
        lines = []
        lines.append(f"[{self.index}]")
        lines.append(f"type={self.type}")
        lines.append(f"TotalTimings={self.TotalTimings}")
        lines.append(f"TimelineInfo0_TimelineIndex={self.TimelineIndex}")
        lines.append(f"TimelineInfo0_starttime={self.starttime}")
        lines.append(f"TimelineInfo0_description={self.description}")
        lines.append(f"TimelineInfo0_repeats={self.repeats}")
        lines.append(f"TimelineInfo0_LightsourceCount={self.LightsourceCount}")
        lines.append(f"TimelineInfo0_LightsourceID_0={self.LightsourceID}")
        lines.append(f"TimelineInfo0_Intensity_0={self.Intensity}")
        lines.append(f"TimelineInfo0_timelinegroupid={self.timelinegroupid}")
        lines.append(f"TimelineInfo0_Stepsize={self.Stepsize}")

        lines.append(f"Entity{self.index}_Type={self.Entity_Type}")
        lines.append(f"Entity{self.index}_Filled={str(self.Entity_Filled)}")
        lines.append(f"Entity{self.index}_CenterX={self.CenterX}")
        lines.append(f"Entity{self.index}_CenterY={self.CenterY}")
        lines.append(f"Entity{self.index}_CenterZ={self.CenterZ}")
        lines.append(f"Entity{self.index}_Rotation={self.Rotation}")
        lines.append(f"Entity{self.index}_ScaleX={self.ScaleX}")
        lines.append(f"Entity{self.index}_ScaleY={self.ScaleY}")
        lines.append(f"Entity{self.index}_ScaleZ={self.ScaleZ}")
        lines.append(f"Entity{self.index}_VertexCount={self.VertexCount}")
        lines.append(f"Entity{self.index}_reversed={str(self.reversed)}")
        lines.append(f"[/{self.index}]")
        return "\n".join(lines)


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
            f.write(self.header.to_txt())
            f.write("\n")
            for roi in self.rois:
                f.write(roi.to_txt())
                f.write("\n")

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


class ROI:
    """
    Represents a Region of Interest (ROI) for a Syscon sequence file.

    Attributes
    ----------
    mode : str
        The ROI mode ('affine_slice' or 'polyline_points').
    tracked : bool
        Whether the ROI is tracked.
    prep_laser : bool
        Whether the laser should be prepared for this ROI.
    layer_idx : int
        The layer index of the ROI.
    x_center : float
        X-coordinate of the ROI center.
    y_center : float
        Y-coordinate of the ROI center.
    z_center : float
        Z-coordinate of the ROI center (layer).
    params : any
        Parameters required to define the ROI (slice parameters or polyline points).
    pixel_coords : np.ndarray
        Array of pixel coordinates covered by the ROI.
    laser_intensity : float
        Laser intensity for the ROI.
    """

    def __init__(self, mode: str = '', params=None, layer_idx: int = 0):
        self.mode = mode
        self.tracked: bool = False
        self.prep_laser: bool = False
        self.layer_idx = layer_idx
        self.x_center: float = 0.0
        self.y_center: float = 0.0
        self.z_center: float = 0.0
        self.params = params
        self.pixel_coords: np.ndarray = np.array([])
        self.laser_intensity: float = 0.0

    def calculate_center(self, image_frame: np.ndarray):
        """
        Calculate the (x, y) center of the ROI.

        Parameters
        ----------
        image_frame : np.ndarray
            The image frame used for generating ROI pixel coordinates.

        Updates
        -------
        self.x_center, self.y_center, self.pixel_coords
        """
        if self.mode == 'affine_slice':
            slice_params = self.params
            coords = pg.affineSliceCoords(
                slice_params[0],
                slice_params[2],
                slice_params[1],
                (0, 1)
            )
            ys, xs = coords
            self.pixel_coords = np.vstack((ys, xs)).T
            self.x_center = np.mean(xs)
            self.y_center = np.mean(ys)

        elif self.mode == 'polyline_points':
            points = np.array(self.params)
            points_int = np.round(points).astype(np.int32)
            contour = points_int.reshape((-1, 1, 2))
            contour = contour[..., [1, 0]]

            mask = np.zeros(image_frame.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [contour], color=1)

            ys, xs = np.nonzero(mask)
            if len(xs) == 0 or len(ys) == 0:
                self.x_center = None
                self.y_center = None
                self.pixel_coords = None
            else:
                self.pixel_coords = np.vstack((ys, xs)).T
                self.x_center = np.mean(xs)
                self.y_center = np.mean(ys)

    def calculate_activity(self, preprocessed_frame: np.ndarray) -> float:
        """
        Calculate the average activity of the ROI in a preprocessed image.

        Parameters
        ----------
        preprocessed_frame : np.ndarray
            Image array used to compute activity.

        Returns
        -------
        float
            Mean activity of pixels in the ROI (scaled by 1/1000).
        """
        if self.mode == 'affine_slice':
            slice_params = self.params
            _slice, coords = pg.affineSlice(
                preprocessed_frame,
                slice_params[0],
                slice_params[2],
                slice_params[1],
                (0, 1),
                returnCoords=True
            )
            self.pixel_coords = coords
            activity_pixels = _slice.flatten()

        elif self.mode == 'polyline_points':
            points = np.array(self.params)
            points_int = np.round(points).astype(np.int32)
            contour = points_int.reshape((-1, 1, 2))
            contour = contour[..., [1, 0]]

            mask = np.zeros(preprocessed_frame.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [contour], color=1)

            self.pixel_coords = mask
            activity_pixels = preprocessed_frame[mask > 0]

        else:
            raise ValueError(f"Unknown mode: {self.mode}")

        roi_activity = np.mean(activity_pixels)/1000 if len(activity_pixels) > 0 else 0
        return roi_activity

    def calculate_z(self):
        """
        Set the Z-coordinate (layer index) for the ROI.
        """
        self.z_center = self.layer_idx
