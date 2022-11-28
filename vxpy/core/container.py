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

    # Call on instance
    _instance.create_dataset(dataset_name, shape, data_type)


def add_to_dataset(dataset_name: str, data: Any):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_to_dataset(dataset_name, data)


class H5File:
    _h5_handle: h5py.File

    def __init__(self, file_path):

        # Open new hdf5 file
        self._file_path = f'{file_path}.hdf5'
        log.info(f'Open HDF5 file {self._file_path}')
        self._h5_handle = h5py.File(self._file_path, 'w')

    def create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        log.debug(f'Create record dataset {dataset_name}, shape {shape}, dtype {data_type}')
        self._h5_handle.create_dataset(dataset_name, shape=(0, *shape,),
                                       dtype=data_type,
                                       maxshape=(None, *shape,),
                                       chunks=(1, *shape,))

    def add_to_dataset(self, path, value):
        # Get dataset
        dataset = self._h5_handle[path]
        # Increase time dimension (0) size by 1
        try:
            dataset.resize((dataset.shape[0] + 1, *dataset.shape[1:]))
            # Write new value
            dataset[dataset.shape[0] - 1] = value
        except:
            import traceback
            traceback.print_exc()
            quit()

    def close(self):

        log.info(f'Close HDF5 file {self._file_path}')

        # Close hdf5 file
        self._h5_handle.close()

# class NpBufferedGroup:
#     # TODO: add cross check for require methods to avoid paths
#     #  being created as both datasets and groups
#
#     def __init__(self, file, parent, name):
#         self._name = name.strip('/')
#         self._groups = dict()
#         self._buffers = dict()
#         self._file = file
#         self._parent = parent
#         self.attrs = dict()
#
#     def __getitem__(self, path):
#         # Start at root?
#         if path.startswith('/'):
#             return self._file[path.strip('/')]
#
#         # Find correct group/dataset
#         path = path.strip('/')
#
#         if not(bool(path)):
#             return self
#
#         names = path.split('/')
#         g = self
#         for n in names[:-1]:
#             g = g._groups[n]
#
#         if names[-1] in g._groups:
#             return g._groups[names[-1]]
#         elif names[-1] in g._buffers:
#             return g._buffers[names[-1]]
#
#         raise KeyError(f'{path} not in {self}')
#
#     def __contains__(self, path):
#
#         if path.startswith('/'):
#             return path.strip('/') in self._file
#
#         names = path.split('/')
#         if len(names) == 1:
#             return names[0] in self._groups or names[0] in self._buffers
#         else:
#             if names[0] in self._groups:
#                 return '/'.join(names[1:]) in self._groups[names[0]]
#             return False
#
#     @property
#     def path(self):
#         if self._parent is None:
#             return '/'
#         else:
#             return f'{self._parent.path}{self._name}/'
#
#     def __repr__(self):
#         return f'Group "{self.path}"'
#
#     def require_group(self, path):
#         if path.startswith('/'):
#             self._file.require_group(path.strip('/'))
#
#         if not(bool(path)):
#             return self
#
#         names = path.split('/')
#
#         if names[0] not in self._groups and bool(names[0]):
#             self._groups[names[0]] = NpBufferedGroup(self._file, self, names[0])
#             return self._groups[names[0]]
#
#         return self._groups[names[0]].require_group('/'.join(names[1:]))
#
#     def create_dataset(self, path, *args, **kwargs):
#         pass
#
#     def append(self, path, data):
#         self._buffers[path].append(data)
#
#     def require_dataset(self, path, **kwargs):
#         names = path.strip('/').split('/')
#
#         if len(names) == 1 and bool(names[0]):
#             if names[0] not in self._buffers:
#                 self._buffers[names[0]] = NpBuffer(names[0], self, **kwargs)
#             return self._buffers[names[0]]
#
#         return self.require_group('/'.join(names[:-1])).require_dataset(names[-1], **kwargs)
#
#     def save(self, h5):
#         grp = h5.require_group(self.path)
#         grp.attrs.update(self.attrs)
#         for g in self._groups.values():
#             g.save(h5)
#
#         for b in self._buffers.values():
#             b.save(h5)
#
#
# class NpBuffer:
#
#     def __init__(self, name, parent, dtype, shape, **kwargs):
#         self._name = name
#         self._parent = parent
#         self.dtype = dtype
#         self.shape = shape
#         self.attrs = dict()
#
#         self.temp_filepath = os.path.join(ipc.Control.Recording[definitions.RecCtrl.folder], f'{self.path.replace("/", "_")}.dat')
#         self._memmap = None
#
#
#     def __repr__(self):
#         return f'Dataset "{self.path}"'
#
#     def _open(self):
#         if self._memmap is not None:
#             return
#
#         _size = np.prod(self.shape[1:]) * np.dtype(self.dtype).itemsize
#         if _size < 500:
#             _length = 10 ** 8
#         else:
#             _length = int(5 * 10 ** 9 / _size)
#
#         try:
#             self._memmap = np.memmap(self.temp_filepath, dtype=self.dtype, mode='w+', shape=(_length, *self.shape[1:]))
#         except Exception:
#             log.error(f'Unable to open temporary file {self.temp_filepath} for numpy buffered recording. '
#                          f'This is most likely because there is insufficient storage space to create temporary files. '
#                          f'Either make room on partition, use different partition or switch to standard H5.')
#             ipc.Controller.rpc(modules.Controller.stop_recording)
#
#         self.idx = 0
#
#     @property
#     def path(self):
#         return f'{self._parent.path}{self._name}'
#
#     def append(self, data):
#         self._open()
#
#         if self.idx >= self._memmap.shape[0]:
#             raise Exception('Oh come on, man! Did you forget to stop the recording?')
#
#         self._memmap[self.idx] = data
#         self.idx += 1
#
#     def save(self, h5):
#         try:
#             dset = h5.create_dataset(self.path, data=self._memmap[:self.idx], chunks=True)
#             dset.attrs.update(self.attrs)
#             del self._memmap
#             self._memmap = None
#             os.remove(self.temp_filepath)
#         except:
#             pass
#
#
# class NpBufferedH5File:
#
#     def __init__(self, *args, **kwargs):
#         self.h5 = h5py.File(*args, **kwargs)
#         self.root = NpBufferedGroup(self, None, '/')
#
#     def __getitem__(self, item):
#         return self.root[item]
#
#     def __contains__(self, item):
#         return item in self.root
#
#     def __repr__(self):
#         return f'NpBufferedH5File linked to {self.h5}'
#
#     def require_group(self, path):
#         return self.root.require_group(path)
#
#     def require_dataset(self, path, **kwargs):
#         return self.root.require_dataset(path, **kwargs)
#
#     def append(self, path, data):
#         self[path].append(data)
#
#     def save(self):
#         self.root.save(self.h5)
#
#     def close(self):
#         self.root.save(self.h5)
#
#         self.h5.close()
