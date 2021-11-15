"""
MappApp ./gui/display/__init__.py
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
import os
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel
import time
from typing import Any, Dict, List

from vxpy import api
from vxpy import Def
from vxpy import modules
from vxpy.core import gui, ipc
from vxpy.core import visual
from vxpy.utils import uiutils
from vxpy.core.protocol import get_available_protocol_paths


class Protocols(gui.AddonWidget):

    def __init__(self, *args, **kwargs):
        gui.AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        # Left
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.left_widget)

        # Protocol list
        self.protocols = QtWidgets.QListWidget()
        self.left_widget.layout().addWidget(QLabel('Files'))
        self.left_widget.layout().addWidget(self.protocols)

        # Right
        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.right_widget)

        # Protocol (phase) progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setTextVisible(False)
        self.right_widget.layout().addWidget(self.progress)

        # Start button
        self.setLayout(QtWidgets.QVBoxLayout())
        self.btn_start = QtWidgets.QPushButton('Start protocol')
        self.btn_start.clicked.connect(self.start_protocol)
        self.right_widget.layout().addWidget(self.btn_start)
        # Abort protocol button
        self.btn_abort = QtWidgets.QPushButton('Abort protocol')
        self.btn_abort.clicked.connect(self.abort_protocol)
        self.right_widget.layout().addWidget(self.btn_abort)

        # Spacer
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.right_widget.layout().addItem(vSpacer)

        # Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(50)
        self._tmr_update.timeout.connect(self.update_ui)
        self._tmr_update.start()

        # Once set up: compile file list for first time
        self.load_protocol_list()

    def load_protocol_list(self):
        self.protocols.clear()
        self.btn_start.setEnabled(False)

        protocol_paths = get_available_protocol_paths()
        for path in protocol_paths:
            item = QtWidgets.QListWidgetItem(self.protocols)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            # Shorten display path
            parts = path.split('.')
            # shown_path = [''] * len(parts[:-2]) + parts[-2:]
            item.setText('.'.join(parts[-2:]))
            item.setToolTip(path)
            self.protocols.addItem(item)

    def update_ui(self):
        # Enable/Disable control elements
        ctrl_is_idle = ipc.in_state(Def.State.IDLE, Def.Process.Controller)
        self.btn_start.setEnabled(ctrl_is_idle)
        self.protocols.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(ipc.Control.Protocol[Def.ProtocolCtrl.name])
        self.btn_abort.setEnabled(protocol_is_running)

        # Update progress
        start_phase = ipc.Control.Protocol[Def.ProtocolCtrl.phase_start]
        if start_phase is not None:
            self.progress.setEnabled(True)
            phase_diff = time.time() - start_phase
            self.progress.setMaximum(int((ipc.Control.Protocol[Def.ProtocolCtrl.phase_stop] - start_phase) * 1000))
            if phase_diff > 0.:
                self.progress.setValue(int(phase_diff * 1000))

        if not(bool(ipc.Control.Protocol[Def.ProtocolCtrl.name])):
            self.progress.setEnabled(False)

    def start_protocol(self):
        protocol_path = self.protocols.currentItem().data(QtCore.Qt.ItemDataRole.UserRole)

        # Start recording
        ipc.rpc(Def.Process.Controller, modules.Controller.start_recording)

        # Start protocol
        ipc.rpc(Def.Process.Controller, modules.Controller.start_protocol, protocol_path)

    def abort_protocol(self):
        self.progress.setValue(0)
        self.progress.setEnabled(False)
        ipc.rpc(Def.Process.Controller, modules.Controller.abort_protocol)


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
        self.tree.itemCollapsed.connect(self.resize_columns)
        self.tree.itemExpanded.connect(self.resize_columns)
        self.left_widget.layout().addWidget(self.tree)
        self.tree.itemDoubleClicked.connect(self.start_visual)

        self.tree_widgets = dict()
        self.toplevel_items: List[QtWidgets.QTreeWidgetItem] = []
        self.visual_items: List[QtWidgets.QTreeWidgetItem]  = []
        self.visuals = dict()
        # TODO: add core module visuals
        
        # Add application visuals
        for visual_container in os.listdir(Def.Path.Visual):
            visual_container = str(visual_container)
            base_path = (Def.Path.Visual, visual_container)
            if visual_container.startswith('_'):
                continue

            # Import module
            if os.path.isdir(os.path.join(*base_path)):
                module = importlib.import_module('.'.join(base_path))
            else:
                module = importlib.import_module('.'.join([*base_path[:-1], base_path[-1].split('.')[0]]))

            self.tree_widgets[base_path] = QtWidgets.QTreeWidgetItem(self.tree)
            self.tree_widgets[base_path].setText(0, visual_container)            

            for clsname, cls in inspect.getmembers(module, inspect.isclass):
                if not(issubclass(cls, (visual.BaseVisual, visual.PlanarVisual, visual.SphericalVisual))) or cls in (visual.PlanarVisual, visual.SphericalVisual):
                    continue

                # Create item which references the visual class
                tree_widget_item = (cls, QtWidgets.QTreeWidgetItem(self.tree_widgets[base_path]))
                tree_widget_item[1].setText(0, clsname)
                tree_widget_item[1].setText(1, cls.description)
                tree_widget_item[1].setData(0, QtCore.Qt.ItemDataRole.ToolTipRole, cls.description)
                tree_widget_item[1].setData(1, QtCore.Qt.ItemDataRole.ToolTipRole, cls.description)
                # Set visual class to UserRole
                tree_widget_item[1].setData(0, QtCore.Qt.ItemDataRole.UserRole, (cls.__module__, cls.__name__))
                self.visual_items.append(tree_widget_item)

        # Add items
        self.tree.addTopLevelItems(self.toplevel_items)

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
        #     Logging.write(Logging.WARNING, 'Starting visual with some unset parameters.')

        ipc.rpc(Def.Process.Display, modules.Display.run_visual, visual_cls, **defaults) #**visual_cls.parameters)

    def update_parameter(self, name):
        def _update(value):
            ipc.rpc(Def.Process.Display, modules.Display.update_visual, **{name: value})
        return _update

    def stop_visual(self):
        ipc.rpc(Def.Process.Display, modules.Display.stop_visual)

    def clear_layout(self, layout: QtWidgets.QLayout):
        while layout.count():
            child = layout.itemAt(0)
            if isinstance(child, QtWidgets.QSpacerItem):
                layout.removeItem(child)
            elif child.widget() is not None:
                child.widget().setParent(None)
            elif child.layout() is not None:
                self.clear_layout(child.layout())