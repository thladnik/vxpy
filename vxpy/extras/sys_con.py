from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Queue
from functools import partial
import copy


import cv2
import numpy as np
import pyqtgraph as pg

from PySide6 import QtWidgets


import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui




class SysConRoutine(vxroutine.WorkerRoutine):

    rois_to_stimulate = {}
    new_rois_set = False

    ui_update_rois = False



    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.command_queue = Queue()




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


# class SysConControlWindow(vxui.WorkerAddonWidget):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         # ===================================================
#         # Main layout: attach to central_widget (not self)
#         # ===================================================
#         main_layout = QtWidgets.QHBoxLayout()
#         self.central_widget.setLayout(main_layout)
#
#         # ===================================================
#         # Left side: Scroll area for ROI controls
#         # ===================================================
#         self.scroll_area = QtWidgets.QScrollArea()
#         self.scroll_area.setWidgetResizable(True)
#
#         self.scroll_widget = QtWidgets.QWidget()
#         self.scroll_layout = QtWidgets.QGridLayout(self.scroll_widget)
#
#         self.scroll_area.setWidget(self.scroll_widget)
#         main_layout.addWidget(self.scroll_area)
#
#         # ===================================================
#         # Right side: Buttons and settings vertical layout
#         # ===================================================
#         button_layout = QtWidgets.QVBoxLayout()
#
#         # ---- Label ----
#         label = QtWidgets.QLabel("SysCon export and controls.")
#         button_layout.addWidget(label)
#
#         # ---- Set all laser intensity field ----
#         intensity_layout = QtWidgets.QHBoxLayout()
#         intensity_label = QtWidgets.QLabel("Set all laser intensity:")
#         self.intensity_field = QtWidgets.QLineEdit()
#         self.intensity_field.setPlaceholderText("%")
#         intensity_layout.addWidget(intensity_label)
#         intensity_layout.addWidget(self.intensity_field)
#         button_layout.addLayout(intensity_layout)
#         self.intensity_field.editingFinished.connect(self.set_all_laser_intensity)
#
#         # ---- Toggle all ROI for Laser ----
#         self.toggle_all_button = QtWidgets.QPushButton("Toggle all ROIs for laser")
#         self.toggle_all_button.clicked.connect(self.toggle_all_roi_for_laser)
#         button_layout.addWidget(self.toggle_all_button)
#
#         # ---- Duration field ----
#         duration_layout = QtWidgets.QHBoxLayout()
#         duration_label = QtWidgets.QLabel("Duration:")
#         self.duration_field = QtWidgets.QLineEdit()
#         self.duration_field.setPlaceholderText("ms")
#         duration_layout.addWidget(duration_label)
#         duration_layout.addWidget(self.duration_field)
#         button_layout.addLayout(duration_layout)
#
#         # ---- Scanning mode selection ----
#         scanning_layout = QtWidgets.QHBoxLayout()
#         scanning_label = QtWidgets.QLabel("Scanning mode:")
#         self.scanning_combo = QtWidgets.QComboBox()
#         self.scanning_combo.addItems(["spiral scanning", "parallel scanning"])
#         scanning_layout.addWidget(scanning_label)
#         scanning_layout.addWidget(self.scanning_combo)
#         button_layout.addLayout(scanning_layout)
#
#         # ---- Diameter field (wrapped in a QWidget for visibility toggle) ----
#         self.diameter_widget = QtWidgets.QWidget()
#         diameter_layout = QtWidgets.QHBoxLayout(self.diameter_widget)
#         diameter_label = QtWidgets.QLabel("Diameter:")
#         self.diameter_field = QtWidgets.QLineEdit()
#         self.diameter_field.setPlaceholderText("µm")
#         diameter_layout.addWidget(diameter_label)
#         diameter_layout.addWidget(self.diameter_field)
#         button_layout.addWidget(self.diameter_widget)
#
#         # ---- Update diameter field visibility based on scanning mode ----
#         self.update_diameter_visibility()
#         self.scanning_combo.currentTextChanged.connect(self.update_diameter_visibility)
#
#         # ---- Write SysCon File button ----
#         self.write_button = QtWidgets.QPushButton("Write SysCon File")
#         self.write_button.clicked.connect(self.write_SysCon_file)
#         button_layout.addWidget(self.write_button)
#
#         # ---- Stretch to push everything up ----
#         button_layout.addStretch()
#
#         # ===================================================
#         # Wrap button layout in a widget and add to main layout
#         # ===================================================
#         button_widget = QtWidgets.QWidget()
#         button_widget.setLayout(button_layout)
#         main_layout.addWidget(button_widget)
#
#         # ===================================================
#         # Final initializations
#         # ===================================================
#         self.connect_to_timer(self.check_state)
#
#         self.global_laser_intensity = 0.0
#         self.laser_prep_list = []
#         self.intensity_edits = []
#
#     def update_diameter_visibility(self):
#         if self.scanning_combo.currentText() == "spiral scanning":
#             self.diameter_widget.setVisible(True)
#         else:
#             self.diameter_widget.setVisible(False)
#
#     def check_state(self):
#         if SysConRoutine.instance().ui_update_rois:
#             self.populate_roi_rows()
#             SysConRoutine.instance().ui_update_rois = False
#
#     def populate_roi_rows(self):
#         roi_dict = SysConRoutine.instance().rois_to_stimulate
#
#         tracked_rois = [
#             ((layer_idx, roi_idx), roi)
#             for (layer_idx, roi_idx), roi in roi_dict.items()
#             if roi.tracked]
#
#         # === ADDED: clear intensity_edits to avoid duplicates ===
#         self.intensity_edits.clear()
#
#         for row_idx, ((layer_idx, roi_idx), roi) in enumerate(tracked_rois):
#
#             roi_label = QtWidgets.QLabel(
#                 f"Layer {layer_idx}, ROI {roi_idx}, x: {roi.x_center:.2f}, y: {roi.y_center:.2f}, z: {roi.z_center:.2f}")
#             self.scroll_layout.addWidget(roi_label, row_idx, 0)
#
#             # Checkbox for prep_laser
#             prep_checkbox = QtWidgets.QCheckBox("Prep Laser")
#             prep_checkbox.setChecked(roi.prep_laser)
#
#             # LineEdit for laser_intensity
#             intensity_edit = QtWidgets.QLineEdit()
#             intensity_edit.setPlaceholderText("Intensity")
#             intensity_edit.setFixedWidth(80)
#             intensity_edit.setText(str(self.global_laser_intensity))
#             intensity_edit.setVisible(roi.prep_laser)  # visible only if prep_laser is True
#
#             # === ADDED: store intensity_edit globally ===
#             self.intensity_edits.append((intensity_edit, layer_idx, roi_idx))
#
#             # === Checkbox callback ===
#             # def on_checkbox_toggled(state, layer_idx=layer_idx, roi_idx=roi_idx, intensity_edit=intensity_edit):
#             #
#             #     existing_entry = None
#             #     for entry in self.laser_prep_list:
#             #         if entry[0] == layer_idx and entry[1] == roi_idx:
#             #             existing_entry = entry
#             #             break
#             #
#             #     if bool(state) == False:
#             #         # If checkbox is unchecked, remove the existing entry if found
#             #         if existing_entry is not None:
#             #             self.laser_prep_list.remove(existing_entry)
#             #     else:
#             #         # If checkbox is checked, add new entry
#             #         self.laser_prep_list.append((layer_idx, roi_idx, self.global_laser_intensity))
#             #
#             #     intensity_edit.setVisible(bool(state))
#             #     intensity_edit.setText(str(self.global_laser_intensity))
#
#
#             # prep_checkbox.stateChanged.connect(on_checkbox_toggled)
#             prep_checkbox.stateChanged.connect(
#                 lambda state, l=layer_idx, r=roi_idx, e=intensity_edit: self.on_checkbox_toggled(state, l, r, e))
#
#
#             # === Intensity edit callback ===
#             def on_intensity_changed(edit, layer_idx, roi_idx):
#                 text = edit.text()
#                 try:
#                     intensity_value = float(text)
#                     if intensity_value < 0.0:
#                         intensity_value = 0.0
#                         edit.setText(str(0))
#                     elif intensity_value > 100.0:
#                         intensity_value = 100.0
#                         edit.setText(str(100))
#
#                 except ValueError:
#                     intensity_value = 0.0
#                     edit.setText(str(0))
#
#                 for idx, entry in enumerate(self.laser_prep_list):
#                     if entry[0] == layer_idx and entry[1] == roi_idx:
#                         self.laser_prep_list[idx] = (layer_idx, roi_idx, intensity_value)
#
#             intensity_edit.editingFinished.connect(
#                 partial(on_intensity_changed, intensity_edit, layer_idx, roi_idx))
#
#             # Add checkbox and intensity edit to layout
#             self.scroll_layout.addWidget(prep_checkbox, row_idx, 1)
#             self.scroll_layout.addWidget(intensity_edit, row_idx, 2)
#
#     def on_checkbox_toggled(self, state, layer_idx, roi_idx, intensity_edit):
#         existing_entry = None
#         for entry in self.laser_prep_list:
#             if entry[0] == layer_idx and entry[1] == roi_idx:
#                 existing_entry = entry
#                 break
#
#         if bool(state) == False:
#             if existing_entry is not None:
#                 self.laser_prep_list.remove(existing_entry)
#         else:
#             if existing_entry is None:
#                 self.laser_prep_list.append((layer_idx, roi_idx, self.global_laser_intensity))
#
#         intensity_edit.setVisible(bool(state))
#         intensity_edit.setText(str(self.global_laser_intensity))
#
#     def set_all_laser_intensity(self):
#         text = self.intensity_field.text()
#         try:
#             intensity_value = float(text)
#             if intensity_value < 0.0:
#                 intensity_value = 0.0
#                 self.intensity_field.setText(str(0))
#             elif intensity_value > 100.0:
#                 intensity_value = 100.0
#                 self.intensity_field.setText(str(100))
#
#         except ValueError:
#             # intensity_value = 0.0
#             self.intensity_field.clear()
#             intensity_value = self.global_laser_intensity
#
#         self.global_laser_intensity = intensity_value
#
#         for idx, (layer_idx, roi_idx, _) in enumerate(self.laser_prep_list):
#             self.laser_prep_list[idx] = (layer_idx, roi_idx, self.global_laser_intensity)
#
#         # Update all visible intensity_edit fields and laser_prep_list entries
#         for edit, _, _ in self.intensity_edits:
#             if edit.isVisible():
#                 edit.setText(str(intensity_value))
#
#         self.intensity_field.clear()
#
#     def toggle_all_roi_for_laser(self):
#         tracked_rois = [
#             (layer_idx, roi_idx)
#             for (layer_idx, roi_idx), roi in SysConRoutine.instance().rois_to_stimulate.items()
#             if roi.tracked
#         ]
#
#         # Create a set of existing (layer_idx, roi_idx) pairs for quick lookup
#         existing_rois = {(layer_idx, roi_idx) for layer_idx, roi_idx, _ in self.laser_prep_list}
#
#         # Determine if we need to add missing ROIs or update existing ones
#         if len(self.laser_prep_list) != len(tracked_rois):
#             # Add missing tracked ROIs with global intensity
#             for idx, (layer_idx, roi_idx) in enumerate(tracked_rois):
#                 if (layer_idx, roi_idx) not in existing_rois:
#                     # self.laser_prep_list.append((layer_idx, roi_idx, self.global_laser_intensity))
#                     self.on_checkbox_toggled(state= True, layer_idx=layer_idx, roi_idx=roi_idx, intensity_edit=self.intensity_edits[idx][0])
#         else:
#             # Update all tracked ROIs to global intensity
#             for idx, (layer_idx, roi_idx, _) in enumerate(self.laser_prep_list):
#                 # self.laser_prep_list[idx] = (layer_idx, roi_idx, self.global_laser_intensity)
#                 self.on_checkbox_toggled(state=False, layer_idx=layer_idx, roi_idx=roi_idx,
#                                          intensity_edit=self.intensity_edits[idx][0])

class SysConControlWindow(vxui.WorkerAddonWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Main layout
        main_layout = QtWidgets.QHBoxLayout()
        self.central_widget.setLayout(main_layout)

        # Left: Scroll area for ROI controls
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)

        # Right: Buttons and settings layout
        button_layout = QtWidgets.QVBoxLayout()

        label = QtWidgets.QLabel("SysCon export and controls.")
        button_layout.addWidget(label)

        intensity_layout = QtWidgets.QHBoxLayout()
        intensity_label = QtWidgets.QLabel("Set all laser intensity:")
        self.intensity_field = QtWidgets.QLineEdit()
        self.intensity_field.setPlaceholderText("%")
        intensity_layout.addWidget(intensity_label)
        intensity_layout.addWidget(self.intensity_field)
        button_layout.addLayout(intensity_layout)
        self.intensity_field.editingFinished.connect(self.set_all_laser_intensity)

        self.toggle_all_button = QtWidgets.QPushButton("Toggle all ROIs for laser")
        self.toggle_all_button.clicked.connect(self.toggle_all_roi_for_laser)
        button_layout.addWidget(self.toggle_all_button)

        duration_layout = QtWidgets.QHBoxLayout()
        duration_label = QtWidgets.QLabel("Duration:")
        self.duration_field = QtWidgets.QLineEdit()
        self.duration_field.setPlaceholderText("ms")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_field)
        button_layout.addLayout(duration_layout)

        scanning_layout = QtWidgets.QHBoxLayout()
        scanning_label = QtWidgets.QLabel("Scanning mode:")
        self.scanning_combo = QtWidgets.QComboBox()
        self.scanning_combo.addItems(["spiral scanning", "parallel scanning"])
        scanning_layout.addWidget(scanning_label)
        scanning_layout.addWidget(self.scanning_combo)
        button_layout.addLayout(scanning_layout)

        self.diameter_widget = QtWidgets.QWidget()
        diameter_layout = QtWidgets.QHBoxLayout(self.diameter_widget)
        diameter_label = QtWidgets.QLabel("Diameter:")
        self.diameter_field = QtWidgets.QLineEdit()
        self.diameter_field.setPlaceholderText("µm")
        diameter_layout.addWidget(diameter_label)
        diameter_layout.addWidget(self.diameter_field)
        button_layout.addWidget(self.diameter_widget)

        self.update_diameter_visibility()
        self.scanning_combo.currentTextChanged.connect(self.update_diameter_visibility)

        self.write_button = QtWidgets.QPushButton("Write SysCon File")
        self.write_button.clicked.connect(self.write_SysCon_file)
        button_layout.addWidget(self.write_button)

        button_layout.addStretch()
        button_widget = QtWidgets.QWidget()
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        self.connect_to_timer(self.check_state)

        self.global_laser_intensity = 0.0
        self.laser_prep_list = []

        # Store tuples: (checkbox, intensity_edit, layer_idx, roi_idx)
        self.roi_widgets = []

    def update_diameter_visibility(self):
        if self.scanning_combo.currentText() == "spiral scanning":
            self.diameter_widget.setVisible(True)
        else:
            self.diameter_widget.setVisible(False)

    def check_state(self):
        if SysConRoutine.instance().ui_update_rois:
            self.populate_roi_rows()
            SysConRoutine.instance().ui_update_rois = False

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_roi_rows(self):
        roi_dict = SysConRoutine.instance().rois_to_stimulate

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
                f"Layer {layer_idx}, ROI {roi_idx}, x: {roi.x_center:.2f}, y: {roi.y_center:.2f}, z: {roi.z_center:.2f}")
            self.scroll_layout.addWidget(roi_label, row_idx, 0)

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
                intensity_edit.setVisible(True)
                self.laser_prep_list.append((layer_idx, roi_idx, initial_intensity))
            else:
                intensity_edit.setVisible(False)

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

            self.scroll_layout.addWidget(prep_checkbox, row_idx, 1)
            self.scroll_layout.addWidget(intensity_edit, row_idx, 2)

    def on_checkbox_toggled(self, state, layer_idx, roi_idx, intensity_edit):
        existing_entry = None
        for entry in self.laser_prep_list:
            if entry[0] == layer_idx and entry[1] == roi_idx:
                existing_entry = entry
                break

        if bool(state):
            if existing_entry is None:
                try:
                    intensity_value = float(intensity_edit.text())
                except ValueError:
                    intensity_value = self.global_laser_intensity
                    intensity_edit.setText(str(intensity_value))
                self.laser_prep_list.append((layer_idx, roi_idx, intensity_value))
        else:
            if existing_entry is not None:
                self.laser_prep_list.remove(existing_entry)

        intensity_edit.setVisible(bool(state))
        # Do NOT overwrite intensity_edit text here to preserve user edits

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
            if edit.isVisible():
                edit.setText(str(intensity_value))

        self.intensity_field.clear()

    def toggle_all_roi_for_laser(self):
        all_on = len(self.laser_prep_list) == len(self.roi_widgets)
        new_state = not all_on
        # Set all checkboxes to new_state, triggers stateChanged, updating all internals & visibility
        for checkbox, edit, layer_idx, roi_idx in self.roi_widgets:
            checkbox.setChecked(new_state)

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
        self.threshold: float = 2000
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

        return np.mean(activity_pixels) if len(activity_pixels) > 0 else 0 # *np.std(activity_pixels)

    def calculate_z(self):

        self.z_center =  self.layer_idx #TODO: adapt this correctly

