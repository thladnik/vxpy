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
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel
import time
from typing import Any, Dict, List, Tuple, Union

from vxpy import api
from vxpy.definitions import *
from vxpy import definitions
from vxpy.definitions import *
from vxpy import modules
from vxpy.core import gui, ipc
from vxpy.core import visual
from vxpy.utils import uiutils
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

        self.left_widget = QtWidgets.QWidget(self)
        self.left_widget.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.left_widget)

        self.right_widget = QtWidgets.QWidget(self)
        self.right_widget.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.right_widget)

        # Set stretch
        self.layout().setStretchFactor(self.left_widget, 1)
        self.layout().setStretchFactor(self.right_widget, 1)

        # Tree widget
        self.tree = QtWidgets.QTreeWidget(self.left_widget)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['', 'Description'])
        self.tree.itemChanged.connect(self.resize_columns)
        self.tree.itemCollapsed.connect(self.resize_columns)
        self.tree.itemExpanded.connect(self.resize_columns)
        self.left_widget.layout().addWidget(self.tree)
        self.tree.itemDoubleClicked.connect(self.start_visual)

        self.toplevel_tree_items: List[QtWidgets.QTreeWidgetItem] = []
        self.tree_items: List[Tuple[object, QtWidgets.QTreeWidgetItem]] = []
        self.append_directory_to_tree(PATH_VISUALS)
        # self.append_directory_to_tree(vxpy.visuals)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start visual')
        self.btn_start.clicked.connect(self.start_visual)
        self.left_widget.layout().addWidget(self.btn_start)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop visual')
        self.btn_stop.clicked.connect(self.stop_visual)
        self.left_widget.layout().addWidget(self.btn_stop)

        # Visual tuning widget
        self.tuner = QtWidgets.QGroupBox('Visual parameters',self.right_widget)
        self.tuner.setLayout(QtWidgets.QVBoxLayout())
        self.right_widget.layout().addWidget(self.tuner)

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
                if not (issubclass(cls, (visual.BaseVisual, visual.PlanarVisual, visual.SphericalVisual))) or cls in (
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
        if not(item):
            item = self.tree.currentItem()

        visual = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if visual is None:
            return

        # TODO: Reload does not seem to work yet
        visual_module, visual_name = visual
        module = importlib.reload(importlib.import_module(visual_module))
        visual_cls = getattr(module, visual_name)

        # Clear layout
        self.clear_layout(self.tuner.layout())

        # Add UI components for visual
        defaults: Dict[str, Any]= dict()
        for name, *args in visual_cls.interface:
            vdef = None
            if isinstance(args[0], str):
                wdgt = uiutils.ComboBoxWidget(name, args)
                vdef = args[0]
                wdgt.setParent(self.tuner)
                wdgt.connect_to_result(self.update_parameter(name))
            elif isinstance(args[0], list):
                pass
                # kwargs = dict()
                # if len(args) > 3:
                #     kwargs = args.pop(-1)
                # vdef, vmin, vmax = args
                # wdgt = uiutils.Dial3d(name, vmin, vmax, vdef)
                # wdgt.setParent(self.tuner)
                # wdgt.connect_to_result(self.update_parameter(name))
            elif isinstance(args[0], bool):
                kwargs = dict()
                if len(args) > 3:
                    kwargs = args.pop(-1)
                vdef = args[0]
                wdgt = uiutils.Checkbox(name, vdef)
                wdgt.setParent(self.tuner)
                wdgt.connect_to_result(self.update_parameter(name))
            elif isinstance(args[0], int):
                kwargs = dict()
                if len(args) > 3:
                    kwargs = args.pop(-1)
                vdef, vmin, vmax = args
                wdgt = uiutils.IntSliderWidget(name, vmin, vmax, vdef, **kwargs)
                wdgt.setParent(self.tuner)
                wdgt.connect_to_result(self.update_parameter(name))
            elif isinstance(args[0], float):
                kwargs = dict()
                if len(args) > 3:
                    kwargs = args.pop(-1)
                vdef, vmin, vmax = args
                wdgt = uiutils.DoubleSliderWidget(name, vmin, vmax, vdef, **kwargs)
                wdgt.setParent(self.tuner)
                wdgt.connect_to_result(self.update_parameter(name))
            elif callable(args[0]):
                wdgt = QtWidgets.QPushButton(name)
                wdgt.clicked.connect(lambda: api.display_rpc(modules.Display.trigger_visual, args[0]))
                wdgt.setParent(self.tuner)
            else:
                wdgt = QLabel(f'<{name}> has unclear type {type(args[0])}', self.tuner)

            self.tuner.layout().addWidget(wdgt)

            # Add default values (if applicable)
            if vdef is not None:
                defaults[name] = vdef

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.tuner.layout().addItem(spacer)

        # TODO: this causes ValueError if visual_cls.paramters.values() contains a numpy.ndarray
        # if None in visual_cls.parameters.values():
        #     logging.write(logging.WARNING, 'Starting visual with some unset parameters.')

        ipc.rpc(PROCESS_DISPLAY, modules.Display.run_visual, visual_cls, **defaults) #**visual_cls.parameters)

    def update_parameter(self, name):
        def _update(value):
            ipc.rpc(PROCESS_DISPLAY, modules.Display.update_visual, **{name: value})
        return _update

    def stop_visual(self):
        ipc.rpc(PROCESS_DISPLAY, modules.Display.stop_visual)

    def clear_layout(self, layout: QtWidgets.QLayout):
        while layout.count():
            child = layout.itemAt(0)
            if isinstance(child, QtWidgets.QSpacerItem):
                layout.removeItem(child)
            elif child.widget() is not None:
                child.widget().setParent(None)
            elif child.layout() is not None:
                self.clear_layout(child.layout())