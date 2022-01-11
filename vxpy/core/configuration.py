import os
import yaml

from vxpy import config
from vxpy.core import logging

log = logging.getLogger(__name__)


def load_configuration(filepath: str):

    log.debug(f'Load configuration file {filepath}')
    if not os.path.exists(filepath):
        log.error('Failed to load configuration. File does not exist.')
        return False

    with open(filepath, 'r') as f:
        _configuration = yaml.safe_load(f)
        config.__dict__.update(_configuration)

    return True


def save_configuration(filepath: str):
    log.info(f'Save current configuration to file {filepath}')

    if not filepath.endswith('.yaml'):
        log.error('Abort saving configuration. File path may be wrong. Use .yaml extension.')
        return False

    with open(filepath, 'w') as f:
        _configuration = {k: d for k, d in config.__dict__.items() if k.startswith('CALIB_')}
        yaml.safe_dump(_configuration, f)

    return True
