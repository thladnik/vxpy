"""Example helper module
"""
import os.path
from typing import Any, Dict, List, Tuple, Union

import h5py
import numpy as np
import requests

import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
from vxpy.definitions import *
from vxpy.utils import ui

log = vxlogger.getLogger(__name__)

# Record of all available datasets. Format is 'key': ('release version number', 'filename', 'type')
# Example datasets are attached as assets to the GitHub release
_available_datasets: Dict[str, Tuple[str, str, str]] = {
    'single_zf_spontaneous_eye_movements_115Hz': ('0.1.4', 'single_zf_spontaneous_eye_movements_115Hz.hdf5', 'camera'),
    'multiple_zf_driven_eye_movements_20Hz': ('0.1.4', 'multiple_zf_driven_eye_movements_20Hz.hdf5', 'camera'),
    'single_zf_freeswim_dot_chased_50Hz': ('0.1.4', 'single_zf_freeswim_dot_chased_50Hz.hdf5', 'camera'),
    'single_zf_freeswim_random_motion': ('0.1.4', 'single_zf_freeswim_random_motion.hdf5', 'camera'),
    'zf_optic_tectum_driven_activity_2Hz': ('0.1.4', 'zf_optic_tectum_driven_activity_2Hz.hdf5', 'imaging')
}

# List of all locally available (downloaded) example dataset keys
_local_datasets: List[str] = []


def require_dataset(key: str):
    """Check whether required dataset is locally available, if not attempt to download it
    """
    global _available_datasets, _local_datasets

    # Check if dataset key is valid
    if key not in _available_datasets:
        log.error(f'Requested dataset {key} not available')
        return

    # Update list
    _update_locals()

    if key not in _local_datasets:
        _download_dataset(key)


def load_dataset(key: str) -> h5py.File:
    """Get file handle for dataset key
    """
    global _local_datasets

    # Update
    _update_locals()

    # Download if not locally available
    if key not in _local_datasets:
        _download_dataset(key)

    # Get Info
    _version, _filename, _ = _available_datasets[key]

    # Return file handle
    return h5py.File(os.path.join(PATH_TEMP, _filename), 'r')


def get_available_dataset_names() -> List[str]:
    global _available_datasets
    return list(_available_datasets.keys())


def get_local_dataset_names() -> List[str]:
    global _local_datasets

    # Update
    _update_locals()

    return _local_datasets


def download_all_datasets():
    """Update all available exsample files
    """
    global _available_datasets, _local_datasets

    # Update
    _update_locals()

    for key in _available_datasets:
        if key in _local_datasets:
            continue
        _download_dataset(key)


def _download_dataset(key: str):
    """Download sample files
    """
    global _available_datasets

    log.info(f'Download dataset {key}')

    _version, _filename, _ = _available_datasets[key]

    # Check availability
    response = None
    source_urls = [f'https://github.com/thladnik/vxpy/releases/download/v{_version}/{_filename}',
                   f'https://github.com/thladnik/vxpy/releases/download/{_version}/{_filename}']
    for src_url in source_urls:

        log.info(f'Trying source {src_url}')

        # Connect
        response = requests.get(src_url, stream=True)

        # Check availability
        if response.status_code == 404:
            log.info(f'{src_url} unavailable')
            response.close()
            response = None
            continue

    if response is None:
        log.error(f'File {_filename} not available for release version {_version}')
        return

    local_path = os.path.join(PATH_TEMP, _filename)
    # Download, if it is available
    with open(local_path, 'wb') as f:
        log.info(f'Download {_filename} to {local_path}')

        total_length = response.headers.get('content-length')

        # If it is unknown
        if total_length is None:
            f.write(response.content)

        # Otherwise download in chunks
        else:
            total_length = int(total_length)

            log.info(f'Size of {_filename}: {total_length}')
            cur_length = 0
            for data in response.iter_content(chunk_size=2**int(np.log2(total_length/100))):
                cur_length += len(data)

                # Update progress
                ui.show_progress(cur_length, total_length, f'Download {src_url}')

                # Write
                f.write(data)

            ui.reset_progress()


def _update_locals():
    """Update list of locally available datasets
    """
    global _available_datasets, _local_datasets

    # Go through all files in sample folder
    for fn in os.listdir(PATH_TEMP):
        if os.path.isdir(os.path.join(PATH_TEMP, fn)):
            continue

        # Match filename to available online versions
        keys = [k for k, entry in _available_datasets.items() if fn == entry[1]]

        # Add if new key
        if len(keys) > 0 and keys[0] not in _local_datasets:
            _local_datasets.append(keys[0])
