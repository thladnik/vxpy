"""
MappApp ./gui/display/display_calibration.py
Copyright (C) 2020 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import importlib
import inspect
import pathlib

import numpy as np
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel
import time
from typing import Any, Dict, List, Tuple, Union, Type

from vxpy import api
from vxpy.definitions import *
from vxpy import definitions
from vxpy.definitions import *
from vxpy import modules, visuals
from vxpy.core import gui, ipc
from vxpy.core import visual
from vxpy.utils import widgets
from vxpy.core.protocol import get_available_protocol_paths, get_protocol


class Protocols(gui.AddonWidget):

    def __init__(self, *args, **kwargs):
        gui.AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())
        
        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        # Create selection widget
        self.selection = QtWidgets.QWidget()
        self.selection.setLayout(QtWidgets.QVBoxLayout())
        self.tab_widget.addTab(self.selection, 'Selection')

        self.protocol_list = QtWidgets.QListWidget()
        self.selection.layout().addWidget(self.protocol_list)

        # Start button
        self.start_btn = QtWidgets.QPushButton('Start protocol')
        self.start_btn.clicked.connect(self.start_protocol)
        self.selection.layout().addWidget(self.start_btn)

        # Create progress widget
        self.progress = QtWidgets.QWidget()
        self.progress.setLayout(QtWidgets.QVBoxLayout())
        self.tab_widget.addTab(self.progress, 'Progress')
        self.tab_widget.setTabEnabled(1, False)

        # Overall protocol progress
        self.protocol_progress_bar = QtWidgets.QProgressBar()
        self.protocol_progress_bar.setMinimum(0)
        self.protocol_progress_bar.setTextVisible(True)
        self.progress.layout().addWidget(self.protocol_progress_bar)

        # Phase progress
        self.phase_progress_bar = QtWidgets.QProgressBar()
        self.phase_progress_bar.setMinimum(0)
        self.phase_progress_bar.setTextVisible(True)
        self.progress.layout().addWidget(self.phase_progress_bar)

        # Show current visual information
        self.progress.layout().addWidget(QtWidgets.QLabel('Visual properties'))
        self.current_visual_name = QtWidgets.QLineEdit('')
        self.current_visual_name.setDisabled(True)
        self.progress.layout().addWidget(self.current_visual_name)

        self.visual_properties = QtWidgets.QTableWidget()
        self.visual_properties.setColumnCount(2)
        self.visual_properties.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.progress.layout().addWidget(self.visual_properties)

        # Abort button
        self.abort_btn = QtWidgets.QPushButton('Abort protocol')
        self.abort_btn.clicked.connect(self.abort_protocol)
        self.progress.layout().addWidget(self.abort_btn)

        # Spacer
        # vspacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        # self.progress.layout().addItem(vspacer)

        # Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(50)
        self._tmr_update.timeout.connect(self.update_ui)
        self._tmr_update.timeout.connect(self.check_status)
        self._tmr_update.start()

        self.current_protocol = None
        self.last_protocol = None
        self.current_phase = None
        self.last_phase = None

        # Once set up: compile file list for first time
        self.load_protocol_list()

    def load_protocol_list(self):
        self.protocol_list.clear()
        self.start_btn.setEnabled(False)

        protocol_paths = get_available_protocol_paths()
        for path in protocol_paths:
            item = QtWidgets.QListWidgetItem(self.protocol_list)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            # Shorten display path
            parts = path.split('.')
            new_parts = [parts[0], *parts[-2:]]
            if len(parts) > 3:
                new_parts.insert(1, '..')
            item.setText('.'.join(new_parts))
            item.setToolTip(path)
            self.protocol_list.addItem(item)

    def check_status(self):

        phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]

        if self.current_protocol is None or phase_id is None:
            return

        if self.current_phase == self.current_protocol.get_phase(phase_id):
            return

        self.current_phase = self.current_protocol.get_phase(phase_id)

        if self.current_phase is None:
            return

        self.current_visual_name.setText(self.current_phase.visual.__qualname__)

        # Update current visual properties in table
        self.visual_properties.clearContents()
        self.visual_properties.setRowCount(len(self.current_phase.visual_parameters))
        for i, (name, value) in enumerate(self.current_phase.visual_parameters.items()):
            self.visual_properties.setItem(i, 0, QtWidgets.QTableWidgetItem(str(name)))
            self.visual_properties.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))
        self.visual_properties.resizeColumnToContents(0)
        self.visual_properties.resizeColumnToContents(1)

    def update_ui(self):
        # Enable/Disable control elements
        ctrl_is_idle = ipc.in_state(definitions.State.IDLE, PROCESS_CONTROLLER)
        self.start_btn.setEnabled(ctrl_is_idle)
        self.protocol_list.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(ipc.Control.Protocol[definitions.ProtocolCtrl.name])
        start_phase = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start]
        phase_stop = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop]
        phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]

        if protocol_is_running:
            self.abort_btn.setEnabled(phase_stop is not None and time.time() <= phase_stop - .2)
        else:
            self.abort_btn.setEnabled(False)

        if ipc.Control.Protocol[definitions.ProtocolCtrl.name] is None:
            self.phase_progress_bar.setEnabled(False)
            self.protocol_progress_bar.setEnabled(False)
            self.protocol_progress_bar.setTextVisible(False)
            self.phase_progress_bar.setTextVisible(False)
            self.protocol_progress_bar.setValue(0)
        else:
            self.phase_progress_bar.setEnabled(True)
            self.protocol_progress_bar.setEnabled(True)
            self.protocol_progress_bar.setTextVisible(True)
            self.phase_progress_bar.setTextVisible(True)

        if start_phase is None:
            self.phase_progress_bar.setValue(0)
            return

        if phase_stop is None:
            return

        # Update progress
        phase_diff = time.time() - start_phase
        phase_duration = phase_stop - start_phase
        if phase_stop is not None:
            # Update phase progress
            self.phase_progress_bar.setMaximum(int(phase_duration * 1000))
            if phase_diff > 0.:
                self.phase_progress_bar.setValue(int(phase_diff * 1000))
                self.phase_progress_bar.setFormat(f'{phase_diff:.1f}/{phase_duration:.1f}s')

            # Update protocol progress
            self.protocol_progress_bar.setMaximum(self.current_protocol.phase_count * 100)
            self.protocol_progress_bar.setValue(100 * phase_id + int(phase_diff/phase_duration * 100))
            self.protocol_progress_bar.setFormat(f'Phase {phase_id+1}/{self.current_protocol.phase_count}')


    def start_protocol(self):
        protocol_path = self.protocol_list.currentItem().data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_protocol = get_protocol(protocol_path)()
        self.tab_widget.setCurrentWidget(self.progress)
        self.tab_widget.setTabEnabled(1, True)
        self.protocol_progress_bar.setFormat('Preparing...')
        self.phase_progress_bar.setFormat('Preparing...')

        # Start recording
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.start_recording)

        # Start protocol
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.start_protocol, protocol_path)

    def abort_protocol(self):
        self.phase_progress_bar.setValue(0)
        self.phase_progress_bar.setEnabled(False)
        self.tab_widget.setCurrentWidget(self.selection)
        self.tab_widget.setTabEnabled(1, False)
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.abort_protocol)


class VisualInteractor(gui.AddonWidget):

    def __init__(self, *args, **kwargs):
        gui.AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        # Available visuals widget
        self.overview_tab = QtWidgets.QWidget(self)
        self.overview_tab.setLayout(QtWidgets.QGridLayout())
        self.tab_widget.addTab(self.overview_tab, 'Available visuals')

        # Tree widget
        self.tree = QtWidgets.QTreeWidget(self.overview_tab)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['', 'Description'])
        self.tree.itemChanged.connect(self.resize_columns)
        self.tree.itemCollapsed.connect(self.resize_columns)
        self.tree.itemExpanded.connect(self.resize_columns)
        self.tree.itemDoubleClicked.connect(self.start_visual)
        self.overview_tab.layout().addWidget(self.tree, 0, 0, 2, 1)

        self.toplevel_tree_items: List[QtWidgets.QTreeWidgetItem] = []
        self.tree_items: List[Tuple[object, QtWidgets.QTreeWidgetItem]] = []
        self.append_directory_to_tree(PATH_VISUALS)
        # self.append_directory_to_tree('vxpy.visuals')

        # Visual parameters widget
        self.parameter_tab = QtWidgets.QWidget(self)
        self.parameter_tab.setLayout(QtWidgets.QGridLayout())
        self.tab_widget.addTab(self.parameter_tab, 'Visual parameters')
        self.tab_widget.setTabEnabled(1, False)
        # Scroll area
        self.parameter_scrollarea = QtWidgets.QScrollArea(self.parameter_tab)
        self.parameter_scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.parameter_scrollarea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.parameter_scrollarea.setWidgetResizable(True)
        # Tuner widget
        self.tuner = QtWidgets.QWidget()
        self.tuner.setLayout(QtWidgets.QGridLayout())
        self.parameter_scrollarea.setWidget(self.tuner)
        # Set layout
        self.parameter_tab.layout().addWidget(self.parameter_scrollarea, 0, 0, 2, 1)
        self.parameter_tab.layout().setColumnStretch(0, 1)
        self.parameter_tab.layout().setColumnStretch(1, 0)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start visual')
        self.btn_start.clicked.connect(self.start_visual)
        self.overview_tab.layout().addWidget(self.btn_start, 1, 1)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop visual')
        self.btn_stop.clicked.connect(self.stop_visual)
        self.parameter_tab.layout().addWidget(self.btn_stop, 0, 1)

        self._parameter_widgets = {}

    def append_directory_to_tree(self, path: Union[str, object]):
        # Add application visuals
        if isinstance(path, str):
            module_list = os.listdir(path)
        else:
            module_list = dir(path)

        for visual_container in module_list:
            visual_container = str(visual_container)
            base_path = (path, visual_container)
            if visual_container.startswith('_'):
                continue

            # Import module
            if os.path.isdir(os.path.join(*base_path)):
                module = importlib.import_module('.'.join(base_path))
            else:
                module = importlib.import_module('.'.join([*base_path[:-1], base_path[-1].split('.')[0]]))

            toplevel_tree_item = QtWidgets.QTreeWidgetItem(self.tree)
            toplevel_tree_item.setText(0, visual_container)
            self.toplevel_tree_items.append(toplevel_tree_item)

            for clsname, cls in inspect.getmembers(module, inspect.isclass):
                if not (issubclass(cls, (visual.BaseVisual, visual.PlanarVisual, visual.SphericalVisual, visual.PlainVisual))) or cls in (
                visual.PlanarVisual, visual.SphericalVisual):
                    continue

                # Create item which references the visual class
                tree_item = (cls, QtWidgets.QTreeWidgetItem(self.toplevel_tree_items[-1]))
                tree_item[1].setText(0, clsname)
                tree_item[1].setText(1, cls.description)
                tree_item[1].setData(0, QtCore.Qt.ItemDataRole.ToolTipRole, cls.description)
                tree_item[1].setData(1, QtCore.Qt.ItemDataRole.ToolTipRole, cls.description)
                # Set visual class to UserRole
                tree_item[1].setData(0, QtCore.Qt.ItemDataRole.UserRole, (cls.__module__, cls.__name__))
                self.tree_items.append(tree_item)

    def resize_columns(self):
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)

    def start_visual(self, item=False, column=False):

        # Get item data
        if not item:
            item = self.tree.currentItem()
        new_visual = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if new_visual is None:
            return

        # Clear layout
        self.clear_layout(self.tuner.layout())

        # Import visual class
        visual_module, visual_name = new_visual
        module = importlib.reload(importlib.import_module(visual_module))
        visual_cls: Type[visual.AbstractVisual] = getattr(module, visual_name)

        # Instantiate
        current_visual = visual_cls()

        # Set up parameter widgets for interaction
        j = 0
        if len(current_visual.static_parameters) > 0:
            label = QLabel('Static parameters')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for i, parameter in enumerate(current_visual.static_parameters):
                if self._add_parameter_widget(j, parameter):
                    j += 1

        if len(current_visual.variable_parameters) > 0:
            label = QLabel('Variable parameters')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for i, parameter in enumerate(current_visual.variable_parameters):
                if self._add_parameter_widget(j, parameter):
                    j += 1

        # Set up triggers
        if len(current_visual.trigger_functions) > 0:
            label = QLabel('Triggers')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for trigger_fun in current_visual.trigger_functions:
                btn = QtWidgets.QPushButton(trigger_fun.__name__)
                btn.clicked.connect(self.trigger_visual_function(trigger_fun))
                self.tuner.layout().addWidget(btn, j, 0, 1, 2)
                j += 1

        # Add spacer for better layout
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.tuner.layout().addItem(spacer)

        # Run visual
        defaults = {name: wdgt.get_value() for name, wdgt in self._parameter_widgets.items()}
        ipc.rpc(PROCESS_DISPLAY, modules.Display.run_visual, visual_cls, defaults)
        self.tab_widget.setTabEnabled(1, True)
        self.tab_widget.setCurrentWidget(self.parameter_tab)

    def _get_widget(self, parameter):
        # Number types
        dtype = parameter.dtype
        if dtype in (np.uint32, np.int32, np.float32, np.float64):
            # Floats
            if dtype in (np.float32, np.float64):
                wdgt = widgets.DoubleSlider(self.tuner)
            else:
                wdgt = widgets.IntSlider(self.tuner)

            # (optional) Set range
            limits = parameter.limits
            if limits is not None:
                wdgt.set_range(*limits)

            # (optional) Set step size
            step_size = parameter.step_size
            if step_size is not None:
                wdgt.set_step(step_size)

            # Set default value
            _default = parameter.default
            if _default is None:
                if limits is not None:
                    _default = dtype(sum(limits) / 2)
                else:
                    _default = dtype(1)
            wdgt.set_value(_default)

        # Assume it is bool otherwise -> Checkbox
        else:
            # TODO: use custom implementation of checbox which has connect_callback
            wdgt = QtWidgets.QCheckBox()
            wdgt.setTristate(False)
            state = False if parameter.default is None or parameter.default else True
            wdgt.setCheckState(QtCore.Qt.CheckState(state))
            wdgt.get_value(wdgt.checkState)

        return wdgt

    def _add_parameter_widget(self, row_id: int, parameter: visual.Parameter) -> bool:

        # If parameter is marked as internal, skip it (e.g. time parameters)
        if parameter.internal:
            return False

        # For textures: print info
        if issubclass(parameter.__class__, visual.Texture):
            self.tuner.layout().addWidget(QLabel(f'Texture {parameter.name}'), row_id, 0)
            label = QLabel(str(parameter.data.shape) if parameter.data is not None else 'Shape unknown')
            self.tuner.layout().addWidget(label, row_id, 1)
            return True

        # Add label with parameter name
        self.tuner.layout().addWidget(QLabel(parameter.name), row_id, 0)

        value_map = parameter.value_map
        if bool(value_map):

            if hasattr(value_map, 'keys'):
                # Combobox if value_map is a dictionary
                wdgt = widgets.ComboBox(self.tuner)
                wdgt.add_items([str(key) for key in value_map.keys()])
                if parameter.default is not None:
                    wdgt.set_value(parameter.default)
            else:
                # Normal widget if value_map is a function
                wdgt = self._get_widget(parameter)

        else:
            wdgt = self._get_widget(parameter)

        # Add callback to update visual
        if hasattr(wdgt, 'connect_callback'):
            # Get update callback
            callback = self.update_parameter(parameter.name)

            # Set widget callback to delay timer
            wdgt.connect_callback(callback)

        # Add widget
        self._parameter_widgets[parameter.name] = wdgt
        self.tuner.layout().addWidget(wdgt, row_id, 1)

        return True

    @staticmethod
    def update_parameter(name):
        def _update(value):
            ipc.rpc(PROCESS_DISPLAY, modules.Display.update_visual, {name: value})
        return _update

    @staticmethod
    def trigger_visual_function(function):
        def _trigger():
            ipc.rpc(PROCESS_DISPLAY, modules.Display.trigger_visual, function.__name__)
        return _trigger

    def stop_visual(self):
        self.clear_layout(self.tuner.layout())
        self.tab_widget.setCurrentWidget(self.overview_tab)
        self.tab_widget.setTabEnabled(1, False)
        ipc.rpc(PROCESS_DISPLAY, modules.Display.stop_visual)

    def clear_layout(self, layout: QtWidgets.QLayout):
        self._parameter_widgets = {}
        while layout.count():
            child = layout.itemAt(0)
            if isinstance(child, QtWidgets.QSpacerItem):
                layout.removeItem(child)
            elif child.widget() is not None:
                child.widget().setParent(None)
            elif child.layout() is not None:
                self.clear_layout(child.layout())