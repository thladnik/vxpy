"""
vxPy ./core/configuration.py
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

from vxpy import config
from vxpy.core import logger

log = logger.getLogger(__name__)


def load_configuration(filepath: str):

    log.debug(f'Load configuration file {filepath}')
    if not os.path.exists(filepath):
        log.error('Failed to load configuration. File does not exist.')
        return False

    with open(filepath, 'r') as f:
        _configuration = yaml.safe_load(f)
        config.PRESERVED_ORDER = list(_configuration.keys())
        config.__dict__.update(_configuration)

    return True


def save_configuration(filepath: str):
    log.info(f'Save current configuration to file {filepath}')

    if not filepath.endswith('.yaml'):
        log.error('Abort saving configuration. File path may be wrong. Use .yaml extension.')
        return False

    with open(filepath, 'w') as f:
        _configuration = {k: getattr(config, k) for k in config.PRESERVED_ORDER}
        yaml.safe_dump(_configuration, f, sort_keys=False)

    return True
