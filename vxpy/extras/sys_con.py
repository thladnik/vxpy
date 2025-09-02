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

    rois_to_stimulate = {}
    new_rois_set = False
    num_layers = 0
    ui_update_rois = False



    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)



    def main(self, *args, **kwargs):


        if SysConRoutine.instance().new_rois_set:

            print(SysConRoutine.instance().rois_to_stimulate)

            SysConRoutine.instance().new_rois_set = False
            SysConRoutine.instance().ui_update_rois = True
            # Do stuff
        elif False:
            pass

        else:
            pass


class SysConControlWindow(vxui.WorkerAddonWidget):

    frame_name: str = 'roi_activity_tracker_frame'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mode = "mean"
        self.image_plots = {}
        self.layer_num = SysConRoutine.instance().num_layers

        self.global_laser_intensity = 0.0
        self.laser_prep_list = []
        self.roi_widgets = []  # Tuples: (checkbox, intensity_edit, layer_idx, roi_idx)

        # === Layout: Split left (plots) and right (controls) ===
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.central_widget.setLayout(QtWidgets.QVBoxLayout())
        self.central_widget.layout().addWidget(splitter)

        # --- Left: Image tiles ---
        self.image_tiles = pg.GraphicsLayoutWidget()
        splitter.addWidget(self.image_tiles)

        # --- Right: Control panel ---
        right_container = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        splitter.addWidget(right_container)

        # === Top Right: ROI Controls ===
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

        # === Bottom Right: Controls and Settings ===
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 10)
        button_layout.setSpacing(8)

        # Label
        label = QtWidgets.QLabel("SysCon export and controls.")
        button_layout.addWidget(label)

        # --- Laser Intensity (%)
        intensity_layout = QtWidgets.QHBoxLayout()
        intensity_label = QtWidgets.QLabel("Laser Intensity:")
        self.intensity_field = QtWidgets.QLineEdit()
        self.intensity_field.setPlaceholderText("%")
        intensity_unit = QtWidgets.QLabel("%")
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addStretch(1)
        intensity_layout.addWidget(self.intensity_field)
        intensity_layout.addWidget(intensity_unit)
        button_layout.addLayout(intensity_layout)
        self.intensity_field.editingFinished.connect(self.set_all_laser_intensity)

        # --- Toggle all button
        self.toggle_all_button = QtWidgets.QPushButton("Toggle all ROIs for laser")
        self.toggle_all_button.clicked.connect(self.toggle_all_roi_for_laser)
        button_layout.addWidget(self.toggle_all_button)

        # --- Duration (ms)
        duration_layout = QtWidgets.QHBoxLayout()
        duration_label = QtWidgets.QLabel("Duration:")
        self.duration_field = QtWidgets.QLineEdit()
        self.duration_field.setPlaceholderText("ms")
        duration_unit = QtWidgets.QLabel("ms")
        duration_layout.addWidget(duration_label)
        duration_layout.addStretch(1)
        duration_layout.addWidget(self.duration_field)
        duration_layout.addWidget(duration_unit)
        button_layout.addLayout(duration_layout)

        # --- Scanning mode combo box
        scanning_layout = QtWidgets.QHBoxLayout()
        scanning_label = QtWidgets.QLabel("Scanning mode:")
        self.scanning_combo = QtWidgets.QComboBox()
        self.scanning_combo.addItems(["spiral scanning", "parallel scanning"])
        scanning_layout.addWidget(scanning_label)
        scanning_layout.addStretch(1)
        scanning_layout.addWidget(self.scanning_combo)
        button_layout.addLayout(scanning_layout)

        # --- Diameter field (µm)
        self.diameter_widget = QtWidgets.QWidget()
        diameter_layout = QtWidgets.QHBoxLayout(self.diameter_widget)
        diameter_label = QtWidgets.QLabel("Diameter:")
        self.diameter_field = QtWidgets.QLineEdit()
        self.diameter_field.setPlaceholderText("pixel")
        diameter_unit = QtWidgets.QLabel("pixel")
        diameter_layout.addWidget(diameter_label)
        diameter_layout.addStretch(1)
        diameter_layout.addWidget(self.diameter_field)
        diameter_layout.addWidget(diameter_unit)
        button_layout.addWidget(self.diameter_widget)
        self.diameter_field.editingFinished.connect(self.update_all_circle_diameters)
        self.update_diameter_visibility()
        self.scanning_combo.currentTextChanged.connect(self.update_diameter_visibility)

        # --- Write SysCon file button
        self.write_button = QtWidgets.QPushButton("Write SysCon File")
        self.write_button.clicked.connect(self.write_SysCon_file)
        button_layout.addWidget(self.write_button)

        # --- Upload / Wait for Trigger Button ---

        self.upload_button = QtWidgets.QPushButton("Upload/Wait for Trigger")
        self.upload_button.clicked.connect(self.upload_and_wait)
        button_layout.addWidget(self.upload_button)

        # === Combine Top/Bottom Right ===
        vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_splitter.addWidget(self.roi_group_box)
        vertical_splitter.addWidget(button_container)
        vertical_splitter.setStretchFactor(0, 3)
        vertical_splitter.setStretchFactor(1, 1)
        right_layout.addWidget(vertical_splitter)

        # Timer hook
        self.connect_to_timer(self.check_state)

    def update_diameter_visibility(self):
        if self.scanning_combo.currentText() == "spiral scanning":
            self.diameter_widget.setVisible(True)
        else:
            self.diameter_widget.setVisible(False)

    def check_state(self):
        syscon = SysConRoutine.instance()
        self.update_frame()
        if syscon.ui_update_rois:
            syscon.ui_update_rois = False

            num_layers = syscon.num_layers
            self.build_image_plots(num_layers)
            self.populate_roi_rows()


    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_roi_rows(self):
        roi_dict = SysConRoutine.instance().rois_to_stimulate

        # print(f"num of layers: {self.layer_num}")
        # self._rebuild_image_plots(num_layers = self.layer_num)

        tracked_rois = [
            ((layer_idx, roi_idx), roi)
            for (layer_idx, roi_idx), roi in roi_dict.items()
            if roi.tracked
        ]

        # Clear old widgets & stored widgets
        self.clear_layout(self.scroll_layout)
        self.roi_widgets.clear()
        self.laser_prep_list.clear()

        for row_idx, ((layer_idx, roi_idx), roi) in enumerate(tracked_rois):
            roi_label = QtWidgets.QLabel(
                f"ROI {roi_idx} [{layer_idx}]<br><span style='font-size:10px;'>"
                f"x: {round(roi.x_center)}, y: {round(roi.y_center)}, z: {round(roi.z_center)}</span>"
            )
            roi_label.setTextFormat(QtCore.Qt.RichText)
            roi_label.setWordWrap(True)

            prep_checkbox = QtWidgets.QCheckBox("Prep Laser")
            prep_checkbox.setChecked(roi.prep_laser)

            intensity_edit = QtWidgets.QLineEdit()
            intensity_edit.setPlaceholderText("Intensity")
            intensity_edit.setFixedWidth(80)

            # If ROI prep_laser enabled, show intensity edit with stored or global intensity
            initial_intensity = self.global_laser_intensity
            if roi.prep_laser:
                # If you have stored intensity, use it, else global
                intensity_edit.setText(str(initial_intensity))
                intensity_edit.setEnabled(True)
                self.laser_prep_list.append((layer_idx, roi_idx, initial_intensity))
            else:
                intensity_edit.setEnabled(False)

            self.roi_widgets.append((prep_checkbox, intensity_edit, layer_idx, roi_idx))

            def on_checkbox_toggled(state, l=layer_idx, r=roi_idx, edit=intensity_edit):
                self.on_checkbox_toggled(state, l, r, edit)

            prep_checkbox.stateChanged.connect(on_checkbox_toggled)

            def on_intensity_changed(edit, l, r):
                text = edit.text()
                try:
                    intensity_value = float(text)
                    if intensity_value < 0.0:
                        intensity_value = 0.0
                        edit.setText("0")
                    elif intensity_value > 100.0:
                        intensity_value = 100.0
                        edit.setText("100")
                except ValueError:
                    intensity_value = 0.0
                    edit.setText("0")

                for idx, entry in enumerate(self.laser_prep_list):
                    if entry[0] == l and entry[1] == r:
                        self.laser_prep_list[idx] = (l, r, intensity_value)

            intensity_edit.editingFinished.connect(
                partial(on_intensity_changed, intensity_edit, layer_idx, roi_idx))

            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(10)

            # Add widgets
            row_layout.addWidget(roi_label, stretch=3)
            row_layout.addWidget(prep_checkbox, stretch=1)
            row_layout.addWidget(intensity_edit, stretch=1)

            self.scroll_layout.addWidget(row_widget)

        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            self.on_checkbox_toggled(checkbox.isChecked(), layer_idx, roi_idx, edit)
    # def on_checkbox_toggled(self, state, layer_idx, roi_idx, intensity_edit):
    #     existing_entry = None
    #     for entry in self.laser_prep_list:
    #         if entry[0] == layer_idx and entry[1] == roi_idx:
    #             existing_entry = entry
    #             break
    #
    #     if bool(state):
    #         if existing_entry is None:
    #             try:
    #                 intensity_value = float(intensity_edit.text())
    #             except ValueError:
    #                 intensity_value = self.global_laser_intensity
    #                 intensity_edit.setText(str(intensity_value))
    #             self.laser_prep_list.append((layer_idx, roi_idx, intensity_value))
    #     else:
    #         if existing_entry is not None:
    #             self.laser_prep_list.remove(existing_entry)
    #
    #     intensity_edit.setEnabled(bool(state))
    #     # Do NOT overwrite intensity_edit text here to preserve user edits

    def on_checkbox_toggled(self, state, layer_idx, roi_idx, intensity_edit):
        roi = SysConRoutine.instance().rois_to_stimulate.get((layer_idx, roi_idx))
        if not roi:
            return

        image_plot = self.image_plots.get(layer_idx)
        if not image_plot:
            return

        is_checked = bool(state)
        intensity_edit.setEnabled(is_checked)

        # Read or fallback to default diameter
        #TODO: find pixel to µm convertion
        try:
            diameter = float(self.diameter_field.text())
        except ValueError:
            diameter = 30.0

        # Create or update the circle once (persistent)
        image_plot.create_or_update_circle(
            roi_idx=roi_idx,
            center=(roi.x_center, roi.y_center),
            diameter=diameter,
            label=f"ROI {roi_idx}"
        )

        # Toggle visibility based on checkbox
        image_plot.set_circle_visible(roi_idx, is_checked)

        # Manage internal laser_prep_list
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


    def set_all_laser_intensity(self):
        text = self.intensity_field.text()
        try:
            intensity_value = float(text)
            if intensity_value < 0.0:
                intensity_value = 0.0
                self.intensity_field.setText("0")
            elif intensity_value > 100.0:
                intensity_value = 100.0
                self.intensity_field.setText("100")
        except ValueError:
            self.intensity_field.clear()
            intensity_value = self.global_laser_intensity

        self.global_laser_intensity = intensity_value

        # Update all laser_prep_list entries
        for idx, (layer_idx, roi_idx, _) in enumerate(self.laser_prep_list):
            self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value)

        # Update all visible intensity edits
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            if edit.isEnabled():
                edit.setText(str(intensity_value))

        self.intensity_field.clear()

    def toggle_all_roi_for_laser(self):
        all_on = len(self.laser_prep_list) == len(self.roi_widgets)
        new_state = not all_on
        # Set all checkboxes to new_state, triggers stateChanged, updating all internals & visibility
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            checkbox.setChecked(new_state)

    def update_all_circle_diameters(self):
        """Update the diameter of all visible circles across all layers."""
        try:
            new_diameter = float(self.diameter_field.text())
        except ValueError:
            return  # Invalid input — ignore

        for image_plot in self.image_plots.values():
            image_plot.update_all_circle_diameters(new_diameter)

    def update_frame(self):
        """Pull frames and update all plots."""

        # if ScanImageFrameReceiverTcpServer.instance().layer_num != self.current_num_layers:
        #     self._rebuild_image_plots(self.current_num_layers)

        for layer_idx, image_plot in self.image_plots.items():
            idx, time, frame = vxattribute.read_attribute(f'{self.frame_name}_{layer_idx}', last=10)
            if len(idx) == 0:
                continue
            if self.mode == "mean":
                frame_avg = np.mean(frame, axis=0)
                image_plot.update_frame(frame_avg)
            elif self.mode == "std":
                frame_std = np.std(frame, axis=0)
                image_plot.update_frame(frame_std)


    # def _rebuild_image_plots(self, num_layers):
    #     self.image_tiles.clear()  # Clear existing plots
    #     self.image_plots.clear()
    #
    #     self.cols = math.ceil(math.sqrt(num_layers))
    #     self.rows = math.ceil(math.sqrt(num_layers))
    #
    #     for i in range(num_layers):
    #         image_plot = ImagePlot(i)
    #         self.image_plots[i] = image_plot
    #
    #         row = i // self.cols
    #         col = i % self.cols
    #         self.image_tiles.addItem(image_plot.plot_item, row=row, col=col)

        # self.current_num_layers = num_layers

    def build_image_plots(self, num_layers):
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

            row = i // self.cols
            col = i % self.cols
            self.image_tiles.addItem(image_plot.plot_item, row=row, col=col)

        print(f"Built {num_layers} image plots.")


    def write_SysCon_file(self):

        writer = SysconFileWriter()
        header = SysconHeader()
        writer.add_header(header)

        print("write: ", SysConRoutine.instance().rois_to_stimulate)

        # selected_roi = [
        #     ((layer_idx, roi_idx), roi)
        #     for (layer_idx, roi_idx), roi in SysConRoutine.instance().rois_to_stimulate.items()
        #     if roi.prep_laser]

        # print(f"selected_roi: {len(selected_roi)}")

        print(f"laser_prep_list: {len(self.laser_prep_list)}, {self.laser_prep_list}")

        for idx, (layer_idx, roi_idx, laser_intensity) in enumerate(self.laser_prep_list):

        # for idx, (layer_idx, roi_idx), roi in enumerate(self.roi_slice_params.items()): #slice_params
        # for idx, ((layer_idx, roi_idx), roi) in enumerate(
        #         (item for item in self.roi_slice_params.items() if item[1].prep_laser)):

            roi = SysConRoutine.instance().rois_to_stimulate[(layer_idx, roi_idx)]

            x, y, z = roi.x_center, roi.y_center, roi.z_center

            temp_roi = SysconROI(idx)
            temp_roi.CenterX = x
            temp_roi.CenterY = y
            temp_roi.CenterZ = z
            temp_roi.Intensity = laser_intensity

            writer.add_roi(temp_roi)

        writer.save()

        #TODO: SCI schnittstelle implementieren hier!

        print(f"SysCon file {writer.filename} written successfully.")

    def upload_and_wait(self):

        print(f"Scan mode: {self.scanning_combo}, Diameter: {self.diameter_field.text()}, Duration: {self.duration_field.text()}")

class ImagePlot:
    def __init__(self, layer_idx):
        self.layer_idx = layer_idx
        self.no_init = True

        self.plot_item = pg.PlotItem()
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)

        self.plot_item.invertY(True)
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.plot_item.setAspectLocked(True)

        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)
        self.mask_item.setVisible(False)
        self.plot_item.addItem(self.mask_item)

        self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
        self.plot_item.addItem(self.text)
        self.text.setPos(0, 0)

        self.circles = {}  # roi_idx -> dict with ellipse, text, center, diameter

    def update_frame(self, frame):
        if self.no_init:
            self.image_item.setImage(frame, autoLevels=False, levels=(frame.min(), frame.max()))
            self.no_init = False
        self.image_item.setImage(frame, autoLevels=False)

    def create_or_update_circle(self, roi_idx, center, diameter, label=None, color=(0, 255, 0, 80), pen_color=(255, 0, 0)):
        """
        Create or update an ROI circle at center with label.
        """
        radius = diameter / 2
        y = center[0] - radius
        x = center[1] - radius

        if roi_idx not in self.circles:
            # Create new graphics items
            ellipse = QGraphicsEllipseItem(x, y, diameter, diameter)
            ellipse.setBrush(QBrush(QColor(*color)))
            ellipse.setPen(QPen(QColor(*pen_color)))
            ellipse.setZValue(10)
            self.plot_item.addItem(ellipse)

            text_item = pg.TextItem(label or f'ROI {roi_idx}', anchor=(0.5, 0.5), color=pen_color)
            text_item.setPos(center[0], center[1])
            text_item.setZValue(11)
            self.plot_item.addItem(text_item)

            self.circles[roi_idx] = {
                'ellipse': ellipse,
                'text': text_item,
                'center': center,
                'diameter': diameter
            }
        else:
            # Update existing ellipse
            ellipse = self.circles[roi_idx]['ellipse']
            text_item = self.circles[roi_idx]['text']
            ellipse.setRect(x, y, diameter, diameter)
            text_item.setPos(center[1], center[0])
            self.circles[roi_idx]['center'] = center
            self.circles[roi_idx]['diameter'] = diameter

    def set_circle_visible(self, roi_idx, visible: bool):
        """Show or hide the circle and label for a given ROI."""
        if roi_idx in self.circles:
            self.circles[roi_idx]['ellipse'].setVisible(visible)
            self.circles[roi_idx]['text'].setVisible(visible)

    def update_all_circle_diameters(self, new_diameter):
        """Apply a new diameter to all visible ROI circles."""
        for roi_idx, info in self.circles.items():
            self.create_or_update_circle(roi_idx, info['center'], new_diameter)

# class ImagePlot:
#     def __init__(self, layer_idx):
#         self.layer_idx = layer_idx
#         # self.on_roi_selected = on_roi_selected
#         # self.on_histogram_selected = on_histogram_selected
#         self.no_init = True
#
#         self.plot_item = pg.PlotItem()
#         # self.vb = CustomViewBox(parent=self)
#         # self.plot_item = pg.PlotItem(viewBox=self.vb)
#         self.image_item = pg.ImageItem()
#         self.plot_item.addItem(self.image_item)
#
#         self.plot_item.invertY(True)
#         self.plot_item.hideAxis('left')
#         self.plot_item.hideAxis('bottom')
#         self.plot_item.setAspectLocked(True)
#
#         # ROI mask image overlay (initially hidden)
#         self.mask_item = pg.ImageItem()
#         self.mask_item.setOpacity(0.3)  # semi-transparent
#         self.mask_item.setVisible(False)
#         self.plot_item.addItem(self.mask_item)
#         self.mask_visible = False
#
#         # Delay connection to avoid NoneType scene error
#
#         self.text = pg.TextItem(f'Layer {self.layer_idx}', color=(255, 0, 0))
#         self.plot_item.addItem(self.text)
#         self.text.setPos(0, 0)
#
#
#     def update_frame(self, frame: np.ndarray):
#         if self.no_init:
#             immin, immax = np.min(frame), np.max(frame)
#             # self.histogram.setHistogramRange(immin, immax)
#             # self.histogram.setLevels(immin, immax)
#             self.image_item.setImage(frame, autoLevels=False,levels= (np.min(frame), np.max(frame)))
#             self.no_init = False
#
#         self.image_item.setImage(frame, autoLevels=False)

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
    def __init__(self, filename=None):
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

    def save(self, filepath="~/Documents/Test_syscon_files"):
        filepath = os.path.expanduser(filepath)

        # Create the directory if it does not exist
        os.makedirs(filepath, exist_ok=True)

        # Build the full path to the file
        full_path = os.path.join(filepath, self.filename)

        with open(full_path, 'w') as f:
            f.write(self.header.to_txt())
            f.write("\n")
            for roi in self.rois:
                f.write(roi.to_txt())
                f.write("\n")

    def add_header(self, header):
        self.header = header

    def add_roi(self, roi):
        self.rois.append(roi)


class ROI:
    def __init__(self, mode: str ='', params=None, layer_idx: int =0):

        self.mode = mode
        self.tracked: bool = False
        self.prep_laser: bool = False
        self.layer_idx = layer_idx
        self.x_center: float = 0.0
        self.y_center: float = 0.0
        self.z_center: float = 0.0
        self.params = params
        self.pixel_coords: np.ndarray = np.array([])  # you can keep it simple without `field`
        # self.threshold: float = 2000
        self.laser_intensity: float = 0.0


    def calculate_center(self, image_frame: np.ndarray):

        """
        Returns the (x, y) centre coordinates of the ROI given mode and parameters.

        Parameters:
            mode (str): 'affine_slice' or 'polyline_points'
            params: slice parameters or polyline points
            preprocessed_frame: the image array used for generating masks or slices

        Returns:
            (float, float): x_center, y_center
        """

        if self.mode == 'affine_slice':
            slice_params = self.params
            coords = pg.affineSliceCoords(
                slice_params[0],
                slice_params[2],
                slice_params[1],
                (0, 1)
            )
            ys = coords[0]
            xs = coords[1]
            self.pixel_coords = np.vstack((ys, xs)).T  # (N,2)
            self.x_center = np.mean(xs)
            self.y_center = np.mean(ys)

        elif self.mode == 'polyline_points':
            points = np.array(self.params)
            points_int = np.round(points).astype(np.int32)
            contour = points_int.reshape((-1, 1, 2))
            contour = contour[..., [1, 0]]  # switch x and y

            mask = np.zeros(image_frame.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [contour], color=1)

            ys, xs = np.nonzero(mask)
            if len(xs) == 0 or len(ys) == 0:
                self.x_center = None
                self.y_center = None
                self.pixel_coords = None
            else:
                self.pixel_coords = np.vstack((ys, xs)).T  # (N,2)
                self.x_center = np.mean(xs)
                self.y_center = np.mean(ys)

    def calculate_activity(self, preprocessed_frame: np.ndarray) -> float:
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

        roi_activity = np.mean(activity_pixels)/1000 if len(activity_pixels) > 0 else 0 # * np.std(activity_pixels) /1000
        return roi_activity #TODO: correct activity measurement ?

    def calculate_z(self):

        self.z_center =  self.layer_idx #TODO: adapt this correctly

