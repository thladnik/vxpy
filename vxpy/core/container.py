"""
vxPy ./core/container.py
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

import cv2
import ffmpeg
import h5py
import numpy as np

from vxpy.definitions import *
import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)

# Dictionary of valid file types for main file container
_file_types: Dict[str, Type[H5File]] = {}

# Handle of currently opened file container class
_instance: Union[H5File, None] = None

# Dictionary of open video stream containers
_video_writers: Dict[str, VideoWriter] = {}


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

    log.debug(f'Create phase dataset {dataset_name}, '
              f'shape {shape}, dtype {data_type}, '
              f'phase_id {vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]}')

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


def create_video_stream(recording_path: str, attribute: vxattribute.VideoStreamAttribute, codec):
    global _video_writers
    if attribute.name in _video_writers:
        log.error(f'Tried creating video stream {attribute.name}, which is already open')
        return

    log.info(f'Open video stream for {attribute} on path {recording_path}')
    if codec in ['h264', 'h265']:
        _video_writers[attribute.name] = MPEGVideoWriter(recording_path, attribute, codec)
    elif codec in ['i420', 'xvid', 'mjpg']:
        _video_writers[attribute.name] = AVIVideoWriter(recording_path, attribute, codec)


def add_to_video_stream(name: str, frame_data: np.ndarray):
    global _video_writers
    if name not in _video_writers:
        return

    _video_writers[name].add_frame(frame_data)


def close_video_streams():
    global _video_writers
    for stream_name in list(_video_writers.keys()):
        stream = _video_writers.get(stream_name)
        if stream is None:
            continue

        log.info(f'Close video stream for {stream.attribute}')
        stream.close()

        del _video_writers[stream_name]


class VideoWriter:

    container_ext: str = None

    def __init__(self, recording_path: str, attribute: vxattribute.VideoStreamAttribute, codec: str):
        self.attribute: vxattribute.VideoStreamAttribute = attribute
        self._filepath = os.path.join(recording_path, f'{self.attribute.name}.{self.container_ext}')
        self.codec = codec


class MPEGVideoWriter(VideoWriter):

    container_ext = 'mp4'

    def __init__(self, *args, **kwargs):
        VideoWriter.__init__(self, *args, **kwargs)

        # Select codec
        vcodec = 'libx264'
        if self.codec == 'h264':
            vcodec = 'libx264'
        elif self.codec == 'h265':
            vcodec = 'libx265'

        w, h = self.attribute.shape[:2]
        # Set pixel format based on attribute shape
        pix_fmt = 'gray'
        if len(self.attribute.shape) > 2 and self.attribute.shape[2] == 3:
            pix_fmt = 'rgb24'

        log.info(f'FFMPEG write to {self._filepath}')

        # Create encoder pipe
        self.process = (
            ffmpeg
            .input('pipe:', format='rawvideo', pix_fmt=pix_fmt, s=f'{w}x{h}')
            .output(self._filepath, pix_fmt='yuv420p',
                    vcodec=vcodec, r=str(self.attribute.target_framerate),
                    video_bitrate=f'{self.attribute.bitrate}')
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )

    def add_frame(self, frame_data: np.ndarray):
        self.process.stdin.write(frame_data.astype(np.uint8).T.tobytes())

    def close(self):
        self.process.stdin.close()
        self.process.wait()


class AVIVideoWriter(VideoWriter):

    container_ext = 'avi'

    def __init__(self, *args, **kwargs):
        VideoWriter.__init__(self, *args, **kwargs)

        self.dsample = 2

        # Select codec
        vcodec = 'XVID'
        if self.codec == 'xvid':
            vcodec = 'XVID'
        elif self.codec == 'i420':
            vcodec = 'I420'
        elif self.codec == 'mjpg':
            vcodec = 'MJPG'

        self.width, self.height = self.attribute.shape[:2]

        log.info(f'AVI write to {self._filepath}')

        # Create encoder pipe
        self.writer = cv2.VideoWriter(self._filepath,
                                      cv2.VideoWriter_fourcc(*vcodec),
                                      float(self.attribute.target_framerate),
                                      (self.width // self.dsample, self.height // self.dsample))

    def add_frame(self, frame_data: np.ndarray):
        self.writer.write(cv2.cvtColor(
            cv2.resize(frame_data.T, (self.width // self.dsample, self.height // self.dsample)),
            cv2.COLOR_GRAY2RGB))

    def close(self):
        self.writer.release()
