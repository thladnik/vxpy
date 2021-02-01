from PyQt5 import QtCore, QtWidgets

class DoubleSliderWidget(QtWidgets.QWidget):

    def __init__(self,slider_name,min_val,max_val,default_val,*args,
                 label_width=None,step_size=None,decimals=1,**kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self._callbacks = []

        if step_size is None:
            step_size = (max_val - min_val) / 10

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,3,0,3)

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
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMaximumHeight(20)
        self.slider.setMinimum(0)
        self.slider.setMaximum((max_val-min_val)//step_size + 1)
        self.slider.setSingleStep(step_size)
        self.slider.setTickInterval(self.slider.maximum()//10)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
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
        self.layout().setContentsMargins(0,3,0,3)

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
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMaximumHeight(20)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setSingleStep(step_size)
        self.slider.setTickInterval((max_val-min_val) // 10)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
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

    def set_value(self, value):
        self.spinner.setValue(value)

    def connect_to_result(self,callback):
        self._callbacks.append(callback)

    def emit_current_value(self):
        self.spinner.valueChanged.emit(self.spinner.value())

    def _exc_callback(self):
        for callback in self._callbacks:
            callback(self.spinner.value())