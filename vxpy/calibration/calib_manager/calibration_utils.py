
import vxpy.core.transform as vxtransform
from vxpy import config
from vxpy.extras import display_widgets
from vxpy.calibration.calib_manager import CalibrationWindow


class VisualInteractorCalibWidget(display_widgets.VisualInteractorInnerWidget):
    """Reimplementation of VisualInteractor for calibration."""

    def __init__(self):
        display_widgets.VisualInteractorInnerWidget.__init__(self)

    @staticmethod
    def set_update_parameter(name):
        def _update(value):
            CalibrationWindow.canvas.current_visual.update({name: value})
        return _update

    @staticmethod
    def set_trigger_visual_function(function):
        def _trigger():
            CalibrationWindow.canvas.current_visual.trigger(function)
        return _trigger

    @staticmethod
    def call_visual_execution(visual_class, parameters):
        """Reimplementation of visual execution method"""
        _transform = vxtransform.get_transform(config.DISPLAY_TRANSFORM)()
        visual = visual_class(CalibrationWindow.canvas, _transform=_transform)
        visual.update(parameters)
        visual.initialize()
        CalibrationWindow.canvas.set_visual(visual)
        CalibrationWindow.canvas.set_transform(_transform)

    @staticmethod
    def call_visual_execution_stop():
        """Reimplementation of visual stop method"""
        CalibrationWindow.canvas.set_visual(None)
