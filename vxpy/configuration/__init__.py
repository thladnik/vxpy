"""Core configuration module

Provides methods for loading, setting and saving configurations.
Includes a manager for changing of configurations
"""
import os
from typing import Any, Dict, Union

import qdarktheme
import yaml
from PySide6 import QtWidgets

from vxpy import config
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


def load_configuration(filepath: str) -> Union[None, Dict[str, Any]]:
    log.debug(f'Load configuration file {filepath}')

    if not os.path.exists(filepath):
        log.error('Failed to load configuration. File does not exist.')
        return None

    with open(filepath, 'r') as f:
        _config_data = yaml.safe_load(f)

    # Preserve order of configuration items in file
    # Set meta info
    config.PRESERVED_ORDER = list(_config_data.keys())
    config.CONFIG_FILEPATH = filepath
    # Set config data
    set_configuration_data(_config_data)

    return _config_data


def set_configuration_data(_config_data: Dict[str, Any]):
    config.__dict__.update(_config_data)


def get_configuration_data() -> Dict[str, Any]:
    return {k: getattr(config, k) for k in config.PRESERVED_ORDER}


def save_configuration(filepath: str = None, _config_data: Union[None, Dict] = None):
    log.info(f'Save current configuration to file {filepath}')

    if filepath is None:
        filepath = config.CONFIG_FILEPATH

    # TODO: implement different configuration file options
    if not filepath.endswith('.yaml'):
        log.error('Abort saving configuration. File path may be wrong. Use .yaml extension.')
        return False

    # If _config_data is None, save currently set environment config
    if _config_data is None:
        _config_data = get_configuration_data()

    with open(filepath, 'w') as f:
        yaml.safe_dump(_config_data, f, sort_keys=False)

    return True


def run_configuration_manager(_config_path: str) -> None:
    """Run configuration manager to make changes to a configuration

    Args:
        _config_path (dict): dictionary of all current configuration settings

    Returns:
        None
    """

    from vxpy.configuration import config_manager

    _app = QtWidgets.QApplication.instance()
    if _app is None:
        _app = QtWidgets.QApplication([])

    # Set theme
    qdarktheme.setup_theme('dark')

    # Load configuration
    set_configuration_data(load_configuration(_config_path))

    # Create window
    _window = config_manager.ConfigurationWindow()
    _window.show()

    # Run app
    _app.exec()

