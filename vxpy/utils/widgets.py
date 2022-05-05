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
from typing import List, Tuple

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QLabel


class UniformFixedWidth:

    def __init__(self):
        self._widgets: List[QtWidgets.QWidget] = []

    def add_widget(self, widget: QtWidgets.QWidget):
        self._widgets.append(widget)
        self.apply()

    def apply(self):
        # Adjust all
        for w in self._widgets:
            w.adjustSize()

        # Fin max width
        max_width = max([w.width() for w in self._widgets])

        # Apply fixed width
        for w in self._widgets:
            w.setFixedWidth(max_width)


class SearchableListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QVBoxLayout())

        # Add searchbar
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.textChanged.connect(self.filter)
        self.search_field.setPlaceholderText('Search...')
        self.layout().addWidget(self.search_field)

        # Add list widget
        self.list_widget = QtWidgets.QListWidget(self)
        self.layout().addWidget(self.list_widget)

    def add_item(self, text: str = None) -> QtWidgets.QListWidgetItem:
        item = QtWidgets.QListWidgetItem(self.list_widget)
        if text is not None:
            item.setText(text)

        self.list_widget.addItem(item)
        return item

    def filter(self, substr: str):
        filtered_items = self.list_widget.findItems(substr, QtCore.Qt.MatchFlag.MatchContains)

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(item not in filtered_items)

    def __getattr__(self, item):
        """Automatically foward non-existent attribute calls to list widget"""
        if item not in self.__dict__:
            return getattr(self.list_widget, item)
        return self.__getattribute__(item)


class DoubleSliderWidget(QtWidgets.QWidget):

    max_precision = -5

    def __init__(self, parent,
                 label: str = None,
                 default: float = None,
                 limits: Tuple[float, float] = None,
                 step_size: float = None,
                 *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

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
        new_val = value * 10**self.max_precision + self.spinner.minimum()
        new_val = new_val // self.spinner.singleStep() * self.spinner.singleStep()
        self.spinner.setValue(new_val)

    def spinner_value_changed(self, value):
        """Update slider widget"""
        self.slider.blockSignals(True)
        new_val = int((value - self.spinner.minimum()) / 10**self.max_precision)
        self.slider.setValue(new_val)
        self.slider.blockSignals(False)

    def set_range(self, min_val, max_val):
        self.spinner.setRange(min_val, max_val)
        # Sliders can only be >= 0 integers
        self.slider.setRange(0, int((max_val - min_val) / 10**self.max_precision))

    def set_step(self, step_size):
        decimal_places = abs(decimal.Decimal(str(step_size)).as_tuple().exponent)
        self.spinner.setDecimals(decimal_places)
        self.spinner.setSingleStep(step_size)
        # Sliders can only be integers
        self.slider.setSingleStep(int(step_size / 10**self.max_precision))

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

    def __init__(self, parent,
                 label: str = None,
                 default: int = None,
                 limits: Tuple[int, int] = None,
                 step_size: int = None,
                 *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
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
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.setMaximumHeight(30)

        self.cb = QtWidgets.QComboBox(self)
        self.cb.setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.cb)

    def add_items(self, items):
        self.cb.addItems(items)

    def connect_callback(self, callback):
        self.cb.currentTextChanged.connect(callback)

    def get_value(self):
        return self.cb.currentText()

    def set_value(self, value):
        self.cb.setCurrentText(value)


# class DoubleSliderWidget(QtWidgets.QWidget):
#
#     def __init__(self, slider_name, min_val, max_val, default_val,*args,
#                  label_width=None,step_size=None,decimals=1,**kwargs):
#         QtWidgets.QWidget.__init__(self, *args, **kwargs)
#
#         self._callbacks = []
#
#         self.step_size = step_size
#         if self.step_size is None:
#             self.step_size = (max_val - min_val) / 10
#
#         self.setLayout(QtWidgets.QHBoxLayout())
#         self.layout().setContentsMargins(0,0,0,0)
#
#         # Label
#         self.label = QtWidgets.QLabel(slider_name)
#         if label_width is not None:
#             self.label.setFixedWidth(label_width)
#         self.layout().addWidget(self.label)
#
#         # Double spinner
#         self.spinner = QtWidgets.QDoubleSpinBox()
#         self.spinner.setFixedWidth(75)
#         self.spinner.setDecimals(decimals)
#         self.spinner.setMinimum(min_val)
#         self.spinner.setMaximum(max_val)
#         self.spinner.setSingleStep(step_size)
#         self.spinner.setValue(default_val)
#         self.spinner.valueChanged.connect(self.spinner_value_changed)
#         self.layout().addWidget(self.spinner)
#
#         # Slider
#         self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
#         self.slider.setMaximumHeight(20)
#         self.slider.setMinimum(min_val // step_size)
#         self.slider.setMaximum(max_val // step_size)
#         # self.slider.setSingleStep(step_size)
#         self.slider.setTickInterval((max_val - min_val) // step_size)
#         self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBothSides)
#         self.slider.valueChanged.connect(self.slider_value_changed)
#         self.layout().addWidget(self.slider)
#
#         # Force slider update
#         self.spinner.valueChanged.emit(self.spinner.value())
#
#     def slider_value_changed(self, value):
#         """Update spinner widget"""
#         self.spinner.blockSignals(True)
#         # self.spinner.setValue(self.spinner.minimum()+self.spinner.singleStep()*value)
#         self.spinner.setValue(self.slider.value() * self.step_size)
#         self.spinner.blockSignals(False)
#
#         self._exc_callback()
#
#     def spinner_value_changed(self, value):
#         """Update slider widget"""
#         self.slider.blockSignals(True)
#         self.slider.setValue((value-self.spinner.minimum()) // self.spinner.singleStep())
#         self.slider.blockSignals(False)
#
#         self._exc_callback()
#
#     def get_value(self):
#         return self.spinner.value()
#
#     def set_value(self, value):
#         self.spinner.setValue(value)
#
#     def connect_to_result(self,callback):
#         self._callbacks.append(callback)
#
#     def emit_current_value(self):
#         self.spinner.valueChanged.emit(self.spinner.value())
#
#     def _exc_callback(self):
#         for callback in self._callbacks:
#             callback(self.spinner.value())
#
#
# class IntSliderWidget(QtWidgets.QWidget):
#
#     def __init__(self,slider_name,min_val,max_val,default_val,*args,
#                  label_width=None,step_size=None,**kwargs):
#         QtWidgets.QWidget.__init__(self, *args, **kwargs)
#
#         self._callbacks = []
#
#         if step_size is None:
#             step_size = (max_val - min_val) // 10
#
#         self.setLayout(QtWidgets.QHBoxLayout())
#         self.layout().setContentsMargins(0,0,0,0)
#
#         # Label
#         self.label = QtWidgets.QLabel(slider_name)
#         if label_width is not None:
#             self.label.setFixedWidth(label_width)
#         self.layout().addWidget(self.label)
#
#         # Spinner
#         self.spinner = QtWidgets.QSpinBox()
#         self.spinner.setFixedWidth(75)
#         self.spinner.setMinimum(min_val)
#         self.spinner.setMaximum(max_val)
#         self.spinner.setSingleStep(step_size)
#         self.spinner.setValue(default_val)
#         self.spinner.valueChanged.connect(self.spinner_value_changed)
#         self.layout().addWidget(self.spinner)
#
#         # Slider
#         self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
#         self.slider.setMaximumHeight(20)
#         self.slider.setMinimum(min_val)
#         self.slider.setMaximum(max_val)
#         self.slider.setSingleStep(step_size)
#         self.slider.setTickInterval((max_val-min_val) // 10)
#         self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBothSides)
#         self.slider.valueChanged.connect(self.slider_value_changed)
#         self.layout().addWidget(self.slider)
#
#         # Force slider update
#         self.spinner.valueChanged.emit(self.spinner.value())
#
#     def slider_value_changed(self, value):
#         """Update spinner widget"""
#         self.spinner.blockSignals(True)
#         self.spinner.setValue(value)
#         self.spinner.blockSignals(False)
#
#         self._exc_callback()
#
#     def spinner_value_changed(self, value):
#         """Update slider widget"""
#         self.slider.blockSignals(True)
#         self.slider.setValue(value)
#         self.slider.blockSignals(False)
#
#         self._exc_callback()
#
#     def get_value(self):
#         return self.spinner.value()
#
#     def set_value(self, value):
#         self.spinner.setValue(value)
#
#     def connect_to_result(self, callback):
#         self._callbacks.append(callback)
#
#     def emit_current_value(self):
#         self.spinner.valueChanged.emit(self.spinner.value())
#
#     def _exc_callback(self):
#         for callback in self._callbacks:
#             callback(self.spinner.value())


class Dial3d(QtWidgets.QWidget):

    def __init__(self, slider_name, min_vals, max_vals, default_vals, *args,
                 label_width=None, step_size=None, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self._callbacks = []

        if step_size is None:
            step_size = (max_vals - min_vals) // 10

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        # Label
        self.label = QtWidgets.QLabel(slider_name)
        if label_width is not None:
            self.label.setFixedWidth(label_width)
        self.layout().addWidget(self.label)

    def get_value(self):
        return self.spinner.value()

    def set_value(self, value):
        self.spinner.setValue(value)

    def connect_to_result(self, callback):
        self._callbacks.append(callback)

    def emit_current_value(self):
        pass

    def _exc_callback(self):
        for callback in self._callbacks:
            callback(self.spinner.value())


class Checkbox(QtWidgets.QWidget):

    def __init__(self, name, default_val, label_width=None):
        QtWidgets.QWidget.__init__(self)

        self._callbacks = []

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Label
        self.label = QtWidgets.QLabel(name)
        if label_width is not None:
            self.label.setFixedWidth(label_width)
        self.layout().addWidget(self.label)

        # Checkbox
        self.checkbox = QtWidgets.QCheckBox()
        self.layout().addWidget(self.checkbox)
        self.checkbox.setChecked(default_val)
        self.checkbox.stateChanged.connect(self._exc_callback)

    def get_value(self):
        return self.checkbox.isChecked()

    def set_value(self, value):
        self.checkbox.setChecked(value)

    def connect_to_result(self, callback):
        self._callbacks.append(callback)

    def _exc_callback(self):
        for callback in self._callbacks:
            callback(self.checkbox.isChecked())


class ComboBoxWidget(QtWidgets.QWidget):
    def __init__(self, name, options, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self._callbacks = []

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.lbl = QLabel(name,self)
        self.lbl.setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.lbl)
        self.cb = QtWidgets.QComboBox(self)
        self.cb.addItems(options)
        self.cb.setContentsMargins(0,0,0,0)
        self.cb.addItems(args)
        self.layout().addWidget(self.cb)

    def connect_to_result(self, callback):
        self.cb.currentTextChanged.connect(callback)

    def get_value(self):
        return self.spinner.data()

    def set_value(self,value):
        self.spinner.setValue(value)