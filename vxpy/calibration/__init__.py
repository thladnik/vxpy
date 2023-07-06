import os
from typing import Any, Dict, Union

import qdarktheme
import yaml
from PySide6 import QtWidgets

from vxpy import calib, config, configuration
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


def load_calibration(filepath: str):
    log.debug(f'Load calibration file {filepath}')

    if not os.path.exists(filepath):
        log.warning('Failed to load calibration. File does not exist.')
        return

    with open(filepath, 'r') as f:
        _calib_data = yaml.safe_load(f)

    # Preserve order and save path
    # Set meta info
    calib.PRESERVED_ORDER = list(_calib_data.keys())
    calib.CALIB_FILEPATH = filepath
    # Set calibration data
    set_calibration_data(_calib_data)

    return _calib_data


def set_calibration_data(_calib_data: Dict[str, Any]):
    calib.__dict__.update(_calib_data)


def get_calibration_data() -> Dict[str, Any]:
    return {k: getattr(calib, k) for k in calib.PRESERVED_ORDER}


def save_calibration(filepath: str = None, _calib_data: Union[None, Dict] = None):
    log.info(f'Save current calibration to file {filepath}')

    if filepath is None:
        filepath = calib.CALIB_FILEPATH

    if not filepath.endswith('.yaml'):
        log.error('Abort saving calibration. File path may be wrong. Use .yaml extension.')
        return

    # If _config_data is None, save currently set environment config
    if _calib_data is None:
        _calib_data = get_calibration_data()

    print(f'Save calib {_calib_data} to {filepath}')

    with open(filepath, 'w') as f:
        yaml.safe_dump(_calib_data, f, sort_keys=False)

    return True


def run_calibration_manager(_config_path: str) -> None:
    """Run calibration manager to make changes to a configuration

    Args:
        _config_path (dict): dictionary of all current configuration settings

    Returns:
        None
    """

    from vxpy.calibration import calib_manager

    _app = QtWidgets.QApplication.instance()
    if _app is None:
        _app = QtWidgets.QApplication([])

    # Set theme
    qdarktheme.setup_theme('dark')

    # Load configuration
    configuration.load_configuration(_config_path)
    # Load calibration in this configuration
    load_calibration(config.PATH_CALIBRATION)

    # Create window
    _window = calib_manager.CalibrationWindow()
    _window.show()

    # Run app
    _app.exec()
