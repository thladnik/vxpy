"""
MappApp ./core/container.py
Custom file container formats to facilitate save builtin save-to-disk operations.
Copyright (C) 2020 Tim Hladnik

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
from __future__ import annotations

import abc
from typing import Union, Type, Any, Tuple

import h5py
import numpy as np

from vxpy.definitions import *
from vxpy import definitions
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
from vxpy import modules

log = vxlogger.getLogger(__name__)

_file_types: Dict[str, Type[H5File]] = {}

# Handle of currently opened file container class
_instance: Union[H5File, None] = None


def init():
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')


def _noinstance():
    return _instance is None


def register_file_type(type_name: str, type_class):
    _file_types[type_name] = type_class


def new(file_type: str, file_path: str):
    global _instance, _file_types

    assert file_type in _file_types, f'Unregistered file type {file_type}'

    if not _noinstance():
        _instance.close()

    _instance = _file_types[file_type](file_path)


def close():
    global _instance

    if _noinstance():
        return

    # Close instance
    _instance.close()
    _instance = None


def create_dataset(dataset_name: str, shape: Tuple[int, ...], data_type: Any):
    global _instance
    if _noinstance():
        return

    log.debug(f'Create dataset {dataset_name}, shape {shape}, dtype {data_type}')

    # Call on instance
    _instance.create_dataset(dataset_name, shape, data_type)


def create_phase_dataset(dataset_name: str, shape: Tuple[int, ...], data_type: Any):
    global _instance
    if _noinstance():
        return

    log.debug(f'Create phase dataset {dataset_name}, shape {shape}, dtype {data_type}')

    # Call on instance
    _instance.create_phase_dataset(dataset_name, shape, data_type)


def add_attributes(attributes: Dict[str, Any]):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_attributes(attributes)


def add_protocol_attributes(attributes: Dict[str, Any]):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_protocol_attributes(attributes)


def add_phase_attributes(attributes: Dict[str, Any]):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_phase_attributes(attributes)


def add_to_phase_dataset(dataset_name: str, data: Any):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_to_phase_dataset(dataset_name, data)


def add_to_dataset(dataset_name: str, data: Any):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_to_dataset(dataset_name, data)


class H5File:
    _protocol_prefix = 'protocol'
    _phase_prefix = 'phase'
    _h5_handle: h5py.File

    def __init__(self, file_path):

        # Open new hdf5 file
        self._file_path = f'{file_path}.hdf5'
        log.info(f'Open HDF5 file {self._file_path}')
        self._h5_handle = h5py.File(self._file_path, 'w')

    @property
    def _phase_str(self):
        return f'{self._phase_prefix}{vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]}'

    @property
    def _protocol_str(self):
        return f'{self._protocol_prefix}{vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID]}'

    def create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        self._create_dataset(dataset_name, shape, data_type)

    def create_phase_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        dataset_name = f'{self._phase_str}/{dataset_name}'
        self._create_dataset(dataset_name, shape, data_type)

    def _create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        self._h5_handle.create_dataset(dataset_name, shape=(0, *shape,),
                                       dtype=data_type,
                                       maxshape=(None, *shape,),
                                       chunks=(1, *shape,))

    @staticmethod
    def _add_attributes(grp: h5py.Group, attributes: Dict[str, Any]):
        log.debug(f'Write attributes to group {grp}')
        grp.attrs.update(attributes)

    def add_attributes(self, attributes: Dict[str, Any]):
        self._add_attributes(self._h5_handle['/'], attributes)

    def add_protocol_attributes(self, attributes: Dict[str, Any]):
        # Get group path from current record_protocol_group_id
        grp = self._h5_handle.require_group(self._protocol_str)

        # Update protocol group attributes
        self._add_attributes(grp, attributes)

    def add_phase_attributes(self, attributes: Dict[str, Any]):
        # Get group path from current record_group_id
        grp = self._h5_handle.require_group(self._phase_str)

        # Update phase group attributes
        self._add_attributes(grp, attributes)

    def add_to_dataset(self, dataset_name: str, data: Any):
        self._add_to_dataset(dataset_name, data)

    def add_to_phase_dataset(self, dataset_name: str, data: Any):
        dataset_name = f'{self._phase_str}/{dataset_name}'
        self._add_to_dataset(dataset_name, data)

    def _add_to_dataset(self, path: str, data: Any):
        try:
            # Get dataset
            dataset = self._h5_handle[path]
            # Increase time dimension (0) size by 1
            dataset.resize((dataset.shape[0] + 1, *dataset.shape[1:]))
            # Write new value
            dataset[dataset.shape[0] - 1] = data

        except Exception as exc:
            log.error(f'Encountered problem while adding data to dataset {path}')
            import traceback
            traceback.print_exc()
            quit()

    def close(self):

        log.info(f'Close HDF5 file {self._file_path}')

        # Close hdf5 file
        self._h5_handle.close()
