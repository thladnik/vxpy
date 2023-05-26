"""
MappApp ./utils/widgets.py
Copyright (C) 2020 Tim Hladnik

* The "qn" class was originally created by Yue Zhang and is also available
   at https://github.com/nash-yzhang/Q_numpy

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
import decimal
from typing import Any, List, Tuple, Union

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel


class WidgetInteraction:
    def __init__(self):
        self.ui: QtWidgets.QWidget = None
        self.connection = None

    def set_type(self, itype):
        if itype == '':
            pass


class UniformWidth:
    """Simple object to synchronize the widths of QWidget and its descendants (makes stuff look prettier)"""

    def __init__(self):
        self._widgets: List[QtWidgets.QWidget] = []

    def add_widget(self, widget: QtWidgets.QWidget):
        # Append widget to list
        self._widgets.append(widget)

        # Apply to all
        self.apply()

    def apply(self):
        # Adjust all to fit content first
        for w in self._widgets:
            w.adjustSize()

        # Find maximum width among all
        max_width = max([w.width() for w in self._widgets])

        # Apply fixed width to all
        for w in self._widgets:
            w.setFixedWidth(max_width)

    def clear(self):
        self._widgets = []


class SearchableListWidget(QtWidgets.QWidget):
    """Wrapper around QListWidget with an integrated QLineEdit that allows for simple filtering of list items"""

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.setLayout(QtWidgets.QGridLayout())

        # Add searchbar
        self.search_field = QtWidgets.QLineEdit(self)
        self.search_field.setPlaceholderText('Search...')
        self.search_field.textChanged.connect(self.filter)
        self.layout().addWidget(self.search_field, 0, 0)

        # Add sort order toggle
        self.sort_order = QtWidgets.QComboBox(self)
        self.sort_order.addItems(['Ascending', 'Descending'])
        self.sort_order.currentTextChanged.connect(self.set_sort_order)
        self.layout().addWidget(self.sort_order, 0, 1)

        # Add list widget
        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.setSortingEnabled(True)
        self.layout().addWidget(self.list_widget, 1, 0, 1, 2)

    def set_sort_order(self, order: str):
        """Change the sort order of the list based on order argument"""

        if order.lower().startswith('asc'):
            self.list_widget.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        else:
            self.list_widget.sortItems(QtCore.Qt.SortOrder.DescendingOrder)

    def add_item(self, text: str = None, custom_data: Any = None) -> QtWidgets.QListWidgetItem:
        """Add a new QListWidgetItem to the QListWidget"""

        # Create item
        item = QtWidgets.QListWidgetItem(self.list_widget)

        # (optionally) Set display test of item
        if text is not None:
            item.setText(text)

        if custom_data is not None:
            item.setData(QtCore.Qt.ItemDataRole.UserRole, custom_data)
            item.data

        # Return created item
        return item

    def clear(self):
        self.list_widget.clear()

    def filter(self, substr: str):
        """Filter QListWidgetItems based on substr and set visibility accordingly"""

        # Get all items matching the filter keyword
        filtered_items = self.list_widget.findItems(substr, QtCore.Qt.MatchFlag.MatchContains)

        # Set visibility of each item in the QListWidget
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(item not in filtered_items)

    def __getattr__(self, item):
        """Automatically foward non-existent attribute calls to list widget"""
        if item not in self.__dict__:
            return getattr(self.list_widget, item)
        return self.__getattribute__(item)


class DoubleSliderWidget(QtWidgets.QWidget):
    """Synchronized combination of a QDoubleSpinBox with a QSlider"""

    max_precision = -5

    def __init__(self, parent,
                 label: str = None,
                 default: float = None,
                 limits: Tuple[float, float] = None,
                 step_size: float = None,
                 *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Add label
        self.label = None
        if label is not None:
            self.label = QLabel(label)
            self.layout().addWidget(self.label)
        self.setMaximumHeight(30)

        # Double spinner
        self.spinner = QtWidgets.QDoubleSpinBox()
        self.spinner.valueChanged.connect(self.spinner_value_changed)
        self.layout().addWidget(self.spinner)

        # Slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.NoTicks)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.layout().addWidget(self.slider)

        # Apply optional args
        if limits is not None:
            self.set_range(*limits)
        if default is not None:
            self.set_value(default)
        if step_size is not None:
            self.set_step(step_size)

    def slider_value_changed(self, value):
        """Update spinner widget"""
        new_val = value * 10 ** self.max_precision + self.spinner.minimum()
        new_val = new_val // self.spinner.singleStep() * self.spinner.singleStep()
        self.spinner.setValue(new_val)

    def spinner_value_changed(self, value):
        """Update slider widget"""
        self.slider.blockSignals(True)
        new_val = int((value - self.spinner.minimum()) / 10 ** self.max_precision)
        self.slider.setValue(new_val)
        self.slider.blockSignals(False)

    def set_range(self, min_val, max_val):
        self.spinner.setRange(min_val, max_val)

        # Sliders can only be >= 0 integers, therefore range needs to be adjusted
        self.slider.setRange(0, int((max_val - min_val) / 10 ** self.max_precision))

    def set_step(self, step_size):
        decimal_places = abs(decimal.Decimal(str(step_size)).as_tuple().exponent)
        self.spinner.setDecimals(decimal_places)
        self.spinner.setSingleStep(step_size)
        # Sliders can only be integers
        self.slider.setSingleStep(int(step_size / 10 ** self.max_precision))

    def get_value(self):
        return self.spinner.value()

    def set_value(self, value):
        self.spinner.setValue(value)
        self.spinner_value_changed(value)

    def connect_callback(self, callback):
        self.spinner.valueChanged.connect(callback)

    def emit_current_value(self):
        self.spinner.valueChanged.emit(self.spinner.value())


class IntSliderWidget(QtWidgets.QWidget):
    """Synchronized combination of a QSpinBox with a QSlider"""

    def __init__(self, parent,
                 label: str = None,
                 default: int = None,
                 limits: Tuple[int, int] = None,
                 step_size: int = None,
                 *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(30)

        # Add label
        self.label = None
        if label is not None:
            self.label = QLabel(label)
            self.layout().addWidget(self.label)
        self.setMaximumHeight(30)

        # Double spinner
        self.spinner = QtWidgets.QSpinBox()
        self.spinner.valueChanged.connect(self.spinner_value_changed)
        self.layout().addWidget(self.spinner)

        # Slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.NoTicks)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.layout().addWidget(self.slider)

        # Force slider update
        # self.spinner.valueChanged.emit(self.spinner.value())

        # Apply optional args
        if limits is not None:
            self.set_range(*limits)
        if default is not None:
            self.set_value(default)
        if step_size is not None:
            self.set_step(step_size)

    def slider_value_changed(self, value):
        """Update spinner widget"""
        self.spinner.setValue(value)

    def spinner_value_changed(self, value):
        """Update slider widget"""
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)

    def set_range(self, min_val, max_val):
        self.spinner.setRange(min_val, max_val)
        self.slider.setRange(min_val, max_val)

    def set_step(self, step_size):
        self.spinner.setSingleStep(step_size)
        self.slider.setSingleStep(step_size)

    def get_value(self):
        return self.spinner.value()

    def set_value(self, value):
        self.spinner.setValue(value)

    def connect_callback(self, callback):
        self.spinner.valueChanged.connect(callback)

    def emit_current_value(self):
        self.spinner.valueChanged.emit(self.spinner.value())


class ComboBox(QtWidgets.QWidget):
    """Wrapper around QComboBox which mimics the interface and style of IntSliderWidget and DoubleSliderWidget"""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(30)

        self.combobox = QtWidgets.QComboBox(self)
        self.combobox.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.combobox)

    def add_items(self, items):
        self.combobox.addItems(items)

    def connect_callback(self, callback):
        self.combobox.currentTextChanged.connect(callback)

    def get_value(self):
        return self.combobox.currentText()

    def set_value(self, value):
        self.combobox.setCurrentText(value)


class Checkbox(QtWidgets.QWidget):
    """Wrapper around QCheckBox which mimics the interface and style of IntSliderWidget and DoubleSliderWidget"""

    def __init__(self, name, default_val, label_width=None):
        QtWidgets.QWidget.__init__(self)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(30)

        # Label
        self.label = QtWidgets.QLabel(name)
        if label_width is not None:
            self.label.setFixedWidth(label_width)
        self.layout().addWidget(self.label)

        # Checkbox
        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setTristate(False)
        self.checkbox.setChecked(default_val)
        self.layout().addWidget(self.checkbox)

    def get_value(self):
        return self.checkbox.isChecked()

    def set_value(self, value):
        self.checkbox.setChecked(value)

    def connect_callback(self, callback):
        self.checkbox.stateChanged.connect(callback)


class ParameterWidget(QtWidgets.QWidget):

    def __init__(self, label: Union[str, QLabel], widget: QtWidgets.QWidget, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        # Set layout
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Add label
        if isinstance(label, str):
            self.label = QLabel(label)
        else:
            self.label = label
        self.layout().addWidget(self.label)
        self.setMaximumHeight(30)

        # Set widget
        self.widget = widget
        self.layout().addWidget(self.widget)
