"""
MappApp ./utils/uiutils.py
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
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QLabel

class DoubleSliderWidget(QtWidgets.QWidget):

    def __init__(self,slider_name,min_val,max_val,default_val,*args,
                 label_width=None,step_size=None,decimals=1,**kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self._callbacks = []

        if step_size is None:
            step_size = (max_val - min_val) / 10

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        # Label
        self.label = QtWidgets.QLabel(slider_name)
        if label_width is not None:
            self.label.setFixedWidth(label_width)
        self.layout().addWidget(self.label)

        # Double spinner
        self.spinner = QtWidgets.QDoubleSpinBox()
        self.spinner.setFixedWidth(75)
        self.spinner.setDecimals(decimals)
        self.spinner.setMinimum(min_val)
        self.spinner.setMaximum(max_val)
        self.spinner.setSingleStep(step_size)
        self.spinner.setValue(default_val)
        self.spinner.valueChanged.connect(self.spinner_value_changed)
        self.layout().addWidget(self.spinner)

        # Slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMaximumHeight(20)
        self.slider.setMinimum(0)
        self.slider.setMaximum((max_val-min_val)//step_size + 1)
        self.slider.setSingleStep(step_size)
        self.slider.setTickInterval(self.slider.maximum()//10)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBothSides)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.layout().addWidget(self.slider)

        # Force slider update
        self.spinner.valueChanged.emit(self.spinner.value())

    def slider_value_changed(self, value):
        """Update spinner widget"""
        self.spinner.blockSignals(True)
        self.spinner.setValue(self.spinner.minimum()+self.spinner.singleStep()*value)
        self.spinner.blockSignals(False)

        self._exc_callback()

    def spinner_value_changed(self, value):
        """Update slider widget"""
        self.slider.blockSignals(True)
        self.slider.setValue((value-self.spinner.minimum()) // self.spinner.singleStep())
        self.slider.blockSignals(False)

        self._exc_callback()

    def get_value(self):
        return self.spinner.value()

    def set_value(self, value):
        self.spinner.setValue(value)

    def connect_to_result(self,callback):
        self._callbacks.append(callback)

    def emit_current_value(self):
        self.spinner.valueChanged.emit(self.spinner.value())

    def _exc_callback(self):
        for callback in self._callbacks:
            callback(self.spinner.value())


class IntSliderWidget(QtWidgets.QWidget):

    def __init__(self,slider_name,min_val,max_val,default_val,*args,
                 label_width=None,step_size=None,**kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self._callbacks = []

        if step_size is None:
            step_size = (max_val - min_val) // 10

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        # Label
        self.label = QtWidgets.QLabel(slider_name)
        if label_width is not None:
            self.label.setFixedWidth(label_width)
        self.layout().addWidget(self.label)

        # Spinner
        self.spinner = QtWidgets.QSpinBox()
        self.spinner.setFixedWidth(75)
        self.spinner.setMinimum(min_val)
        self.spinner.setMaximum(max_val)
        self.spinner.setSingleStep(step_size)
        self.spinner.setValue(default_val)
        self.spinner.valueChanged.connect(self.spinner_value_changed)
        self.layout().addWidget(self.spinner)

        # Slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMaximumHeight(20)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setSingleStep(step_size)
        self.slider.setTickInterval((max_val-min_val) // 10)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBothSides)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.layout().addWidget(self.slider)

        # Force slider update
        self.spinner.valueChanged.emit(self.spinner.value())

    def slider_value_changed(self, value):
        """Update spinner widget"""
        self.spinner.blockSignals(True)
        self.spinner.setValue(value)
        self.spinner.blockSignals(False)

        self._exc_callback()

    def spinner_value_changed(self, value):
        """Update slider widget"""
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)

        self._exc_callback()

    def get_value(self):
        return self.spinner.value()

    def set_value(self, value):
        self.spinner.setValue(value)

    def connect_to_result(self, callback):
        self._callbacks.append(callback)

    def emit_current_value(self):
        self.spinner.valueChanged.emit(self.spinner.value())

    def _exc_callback(self):
        for callback in self._callbacks:
            callback(self.spinner.value())


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
        return self.spinner.value()

    def set_value(self,value):
        self.spinner.setValue(value)