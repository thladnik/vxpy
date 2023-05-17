"""Core configuration module

Provides methods for loading, setting and saving configurations
"""
import os
from typing import Any, Dict, Union

import yaml

from vxpy import config
import vxpy.core.ipc as vxipc
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
        config.PRESERVED_ORDER = list(_config_data.keys())

    return _config_data


def set_configuration_data(_config_data: Dict[str, Any]):
    config.__dict__.update(_config_data)


def save_configuration(filepath: str, _config_data: Union[None, Dict] = None):
    log.info(f'Save current configuration to file {filepath}')

    if not filepath.endswith('.yaml'):
        log.error('Abort saving configuration. File path may be wrong. Use .yaml extension.')
        return False

    # If _config_data is None, save currently set environment config
    if _config_data is None:
        _config_data = {k: getattr(config, k) for k in config.PRESERVED_ORDER}

    with open(filepath, 'w') as f:
        yaml.safe_dump(_config_data, f, sort_keys=False)

    return True
