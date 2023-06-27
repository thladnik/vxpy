"""
vxPy ./gui/display/display_widgets.py
Copyright (C) 2022 Tim Hladnik

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
import logging
from types import ModuleType

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel
from typing import Any, Dict, List, Tuple, Union, Type

from vxpy import calib
from vxpy import config
import vxpy.visuals
from vxpy.definitions import *
import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.visual as vxvisual
import vxpy.core.ui as vxui
import vxpy.modules as vxmodules
import vxpy.visuals
from vxpy.utils import widgets

log = logging.getLogger(__name__)


class VisualInteractor(vxui.DisplayAddonWidget):

    def __init__(self, *args, **kwargs):
        vxui.DisplayAddonWidget.__init__(self, *args, **kwargs)

        self.central_widget.setLayout(QtWidgets.QHBoxLayout())
        self.inner_widget = VisualInteractorInnerWidget()
        self.central_widget.layout().addWidget(self.inner_widget)


class VisualInteractorInnerWidget(QtWidgets.QWidget):
    """Widget which allows for independent display of visual stimuli and interactive manipulation of parameters"""

    display_name = 'Visual control'

    def __init__(self, *args, **kwargs):
        # vxui.DisplayAddonWidget.__init__(self, *args, **kwargs)
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.tab_widget = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tab_widget)

        # Available visuals widget
        self.overview_tab = QtWidgets.QWidget(self)
        self.overview_tab.setLayout(QtWidgets.QGridLayout())
        self.tab_widget.addTab(self.overview_tab, 'Available visuals')

        # Tree widget
        self.visual_list = widgets.SearchableListWidget(self.overview_tab)
        self.visual_list.itemDoubleClicked.connect(self.start_visual)
        self.overview_tab.layout().addWidget(self.visual_list, 0, 0, 2, 1)

        self.find_on_path(PATH_VISUALS)
        self.find_in_module(vxpy.visuals)

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
        self._uniform_label_width = widgets.UniformWidth()

    def find_in_module(self, _module: ModuleType):
        for _submodule_name in _module.__all__:
            try:
                self._scan_module(importlib.import_module(f'{_module.__name__}.{_submodule_name}'))
            except Exception as exc:
                logging.warning(f'Failed {_submodule_name} // {exc}')

    def find_on_path(self, path: str):
        """Add all visuals on path to the list"""

        # Import from files on a relative given path
        module_list = os.listdir(path)
        # Split
        path_parts = path.split(os.sep)

        # Scan all available containers on path
        for _container_name in module_list:
            _container_name = str(_container_name)
            if _container_name.startswith('_'):
                continue

            # Import module
            if os.path.isdir(os.path.join(*[*path_parts, _container_name])):
                _module = importlib.import_module('.'.join([*path_parts, _container_name]))
            else:
                _module = importlib.import_module('.'.join([*path_parts, _container_name.split('.')[0]]))

            self._scan_module(_module)

    def _scan_module(self, _module: ModuleType):
        # Go through all classes in _module
        for _classname, _class in inspect.getmembers(_module, inspect.isclass):
            if not issubclass(_class, vxvisual.AbstractVisual) or _class in vxvisual.visual_bases:
                continue

            # Create item which references the visual class
            self._add_visual_item(f'{_module.__name__}.{_classname}', _class)

    def _add_visual_item(self, name: str, _class: Type[vxvisual.AbstractVisual]):
        if config.DISPLAY_TRANSFORM not in [_t.__name__ for _t in _class.available_transforms]:
            return
        item = self.visual_list.add_item()
        item.setText(name)
        item.setData(QtCore.Qt.ItemDataRole.ToolTipRole, _class.description)
        # Set visual class information to UserRole
        item.setData(QtCore.Qt.ItemDataRole.UserRole, (_class.__module__, _class.__name__))

    def start_visual(self, item=False):
        # Reset label list
        self._uniform_label_width.clear()

        # Get item data
        if not item:
            item = self.visual_list.currentItem()
        new_visual = item.data(QtCore.Qt.ItemDataRole.UserRole)

        if new_visual is None:
            return

        # Clear layout
        self.clear_layout(self.tuner.layout())

        # Import visual class
        visual_module, visual_name = new_visual
        module = importlib.reload(importlib.import_module(visual_module))
        visual_class: Type[vxvisual.AbstractVisual] = getattr(module, visual_name)

        # Instantiate visual
        current_visual = visual_class()

        # Set up parameter widgets for interaction
        j = 0

        # Add static parameters (not meant to be updated at runtime, but still possible)
        if len(current_visual.static_parameters) > 0:
            label = QLabel('Static parameters')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for i, parameter in enumerate(current_visual.static_parameters):
                if self._add_parameter_widget(j, parameter):
                    j += 1

        # Add variable parameters (meant to be updated online)
        if len(current_visual.variable_parameters) > 0:
            label = QLabel('Variable parameters')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for i, parameter in enumerate(current_visual.variable_parameters):
                if self._add_parameter_widget(j, parameter):
                    j += 1

        # Set up custom triggers
        if len(current_visual.trigger_functions) > 0:
            label = QLabel('Triggers')
            label.setStyleSheet('font-weight:bold;')
            self.tuner.layout().addWidget(label, j, 0, 1, 2)
            j += 1
            for trigger_fun in current_visual.trigger_functions:
                btn = QtWidgets.QPushButton(trigger_fun.__name__)
                btn.clicked.connect(self.set_trigger_visual_function(trigger_fun))
                self.tuner.layout().addWidget(btn, j, 0, 1, 2)
                j += 1

        # Add spacer for better layout
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.tuner.layout().addItem(spacer)

        # Run visual
        defaults = {name: wdgt.get_value() for name, wdgt in self._parameter_widgets.items()}
        self.call_visual_execution(visual_class, defaults)
        self.tab_widget.setTabEnabled(1, True)
        self.tab_widget.setCurrentWidget(self.parameter_tab)

    @staticmethod
    def call_visual_execution(visual_class, parameters):
        """Method to be called when a visual starts. May be overwritten"""
        vxipc.rpc(PROCESS_DISPLAY, vxmodules.Display.run_visual, visual_class, parameters)

    def stop_visual(self):
        self.clear_layout(self.tuner.layout())
        self.tab_widget.setCurrentWidget(self.overview_tab)
        self.tab_widget.setTabEnabled(1, False)

        # Call stop
        self.call_visual_execution_stop()

    @staticmethod
    def call_visual_execution_stop():
        """Method to be called when a visual stops. May be overwritten"""
        vxipc.rpc(PROCESS_DISPLAY, vxmodules.Display.stop_visual)

    def _get_widget(self, parameter):

        # Skip attributes, TODO: better
        if isinstance(parameter, (vxvisual.Attribute, vxvisual.BoolAttribute)):
            return

        # Number types
        dtype = parameter.dtype
        if dtype in (np.uint32, np.int32, np.float32, np.float64):
            # Floats
            if dtype in (np.float32, np.float64):
                wdgt = widgets.DoubleSliderWidget(self.tuner)
            else:
                wdgt = widgets.IntSliderWidget(self.tuner)

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

    def _add_parameter_widget(self, row_id: int, parameter: vxvisual.Parameter) -> bool:

        # If parameter is marked as internal, skip it (e.g. time parameters)
        if parameter.internal:
            return False

        # For textures: print info
        if issubclass(parameter.__class__, vxvisual.Texture):
            self.tuner.layout().addWidget(QLabel(f'Texture {parameter.name}'), row_id, 0)
            label = QLabel(str(parameter.data.shape) if parameter.data is not None else 'Shape unknown')
            self.tuner.layout().addWidget(label, row_id, 1)
            return True

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
                # TODO: fix this, otherwise this only reflects the background datatype of the mapping,
                #  which is usually not helpful to the user
                wdgt = self._get_widget(parameter)

        else:
            wdgt = self._get_widget(parameter)

        # No widget returned: skip
        if wdgt is None:
            return False

        # Add callback to update visual
        if hasattr(wdgt, 'connect_callback'):
            # Get update callback
            callback = self.set_update_parameter(parameter.name)

            # Set widget callback to delay timer
            wdgt.connect_callback(callback)

        # Add label with parameter name
        label = QLabel(parameter.name)
        self._uniform_label_width.add_widget(label)
        self.tuner.layout().addWidget(label, row_id, 0)

        # Add widget
        self._parameter_widgets[parameter.name] = wdgt
        self.tuner.layout().addWidget(wdgt, row_id, 1)

        return True

    @staticmethod
    def set_update_parameter(name):
        def _update(value):
            vxipc.rpc(PROCESS_DISPLAY, vxmodules.Display.update_visual, {name: value})
        return _update

    @staticmethod
    def set_trigger_visual_function(function):
        def _trigger():
            vxipc.rpc(PROCESS_DISPLAY, vxmodules.Display.trigger_visual, function.__name__)
        return _trigger

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


class VisualStreamAddon(vxui.DisplayAddonWidget):

    display_name = 'Visual view'

    def __init__(self, *args, **kwargs):
        vxui.DisplayAddonWidget.__init__(self, *args, **kwargs)

        self.central_widget.setLayout(QtWidgets.QHBoxLayout())

        # Add visual widget
        self.graphics_widget = GraphicsWidget(self, parent=self)
        self.central_widget.layout().addWidget(self.graphics_widget)

        self.connect_to_timer(self.update_frame)

    def update_frame(self):

        idx, time, frame = vxattribute.read_attribute('display_frame')

        if frame is None:
            return

        self.graphics_widget.image_item.setImage(frame[0])


class GraphicsWidget(pg.GraphicsLayoutWidget):

    def __init__(self, main, **kwargs):
        pg.GraphicsLayoutWidget.__init__(self, **kwargs)

        # Add plot
        self.image_plot = self.addPlot(0, 0, 1, 10)

        # Set up plot image item
        self.image_item = pg.ImageItem()
        self.image_plot.invertY(True)
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)
        self.image_plot.addItem(self.image_item)
