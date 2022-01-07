import logging
import os
import yaml

from vxpy import calib

log = logging.getLogger(__name__)


def load_calibration(filepath: str):
    log.debug(f'Load calibration file {filepath}')
    if not os.path.exists(filepath):
        log.warning('Failed to load calibration. File does not exist.')
        return

    with open(filepath, 'r') as f:
        _calibration = yaml.safe_load(f)
        calib.__dict__.update(_calibration)


def save_calibration(filepath: str):
    log.info(f'Save current calibration to file {filepath}')
    if not filepath.endswith('.yaml'):
        log.error('Abort saving calibration. File path may be wrong. Use .yaml extension.')
        return

    with open(filepath, 'w') as f:
        _calibration = {k: d for k, d in calib.__dict__.items() if k.startswith('CALIB_')}
        yaml.safe_dump(_calibration, f)