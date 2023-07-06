"""Example helper module
"""
import os.path
from typing import Any, Dict, List

import vxpy.core.logger as vxlogger
from vxpy.definitions import *

log = vxlogger.getLogger(__name__)

_available: Dict[str, Dict[str, Any]] = {}
_required: Dict[str, Dict[str, Any]] = {}


def require_dataset(name: str):
    """Add a given name to the list of required datasets, if it is listed ad available"""
    global _available, _required
    if name in _required:
        return

    if name not in _available:
        log.error(f'Required dataset {name} is not available')

    _required[name] = {}


def fetch_dataset(name: str):
    """Fetch given dataset's HDF5 file from approriate source"""
    global _required

    # TODO: actually download

    _required[name]['loaded'] = True


def get_dataset_handle(name: str):
    """Get the handle on the given dataset HDF5 file"""
    if not name in _required:
        log.error('Dataset name is not not listed as required')


def check_loaded():
    """Check which example files are available"""
    global _available, _loaded

    for name, info in _available.items():
        path = os.path.join(get_sample_path(), f'{name}.hdf5')
        _required[name]['loaded'] = os.path.exists(path) and os.path.isfile(path)


def process():
    """Make sure all required datasets are locally available"""
    global _available, _required
    check_loaded()

    for name, info in _required.items():
        if not info['loaded']:
            fetch_dataset(name)
