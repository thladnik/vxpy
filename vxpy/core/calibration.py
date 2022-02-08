"""
vxPy ./core/calibration.py
Copyright (C) 2022 Tim Hladnik

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
import os
import yaml

from vxpy import calib
from vxpy.core import logger

log = logger.getLogger(__name__)


def load_calibration(filepath: str):
    log.debug(f'Load calibration file {filepath}')
    if not os.path.exists(filepath):
        log.warning('Failed to load calibration. File does not exist.')
        return

    with open(filepath, 'r') as f:
        _calibration = yaml.safe_load(f)
        calib.PRESERVED_ORDER = list(_calibration.keys())
        calib.__dict__.update(_calibration)


def save_calibration(filepath: str):
    log.info(f'Save current calibration to file {filepath}')
    if not filepath.endswith('.yaml'):
        log.error('Abort saving calibration. File path may be wrong. Use .yaml extension.')
        return

    with open(filepath, 'w') as f:
        _calibration = {k: getattr(calib, k) for k in calib.PRESERVED_ORDER}
        yaml.safe_dump(_calibration, f, sort_keys=False)
