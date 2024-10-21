# -*- coding: utf-8 -*-
"""Custom file container formats to facilitate save builtin save-to-disk operations.
"""
from __future__ import annotations

import abc
import os.path
from typing import List, Union, Type, Any, Tuple, Dict

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
_text_writers: Dict[str, TextWriter] = {}


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


def set_fallback_phase_id(phase_id: str):
    if _noinstance():
        return

    _instance.fallback_phase_id = phase_id

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

    # There are no negative phase ids
    # if vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] < 0:
    #     return

    # Call on instance
    _instance.add_phase_attributes(attributes)


def add_to_phase_dataset(dataset_name: str, data: Any):
    global _instance
    if _noinstance():
        return

    # There are no negative phase ids
    # if vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] < 0:
    #     return

    # Call on instance
    _instance.add_to_phase_dataset(dataset_name, data)


def add_to_dataset(dataset_name: str, data: Any):
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_to_dataset(dataset_name, data)


def dump(data, group: str = None):
    """Dump arbitrary data into currently opened container"""

    if _noinstance():
        return

    if group is None:
        group = ''

    # Save anything with a simple Python type as attribute
    attributes = {k: d for k, d in data.items() if type(d) in (str, int, float, complex, bool, list, tuple, dict)}
    if len(attributes) > 0:
        try:
            log.info(f'Dump attributes {list(attributes.keys())} to file')
            _instance.add_attributes(attributes, group=group)
        except Exception as _exc:
            log.error(f'Failed to dump attributes {list(attributes.keys())} to file')

    # Safe arrays
    arrays = {k: d for k, d in data.items() if isinstance(d, np.ndarray) and np.issubdtype(d.dtype, np.number)}
    for k, d in arrays.items():

        saved = False
        i = 0
        while not saved:
            try:
                _instance.create_dataset(f'{group}/{k}_{i}', d.shape, d.dtype)
                _instance.add_to_dataset(f'{group}/{k}_{i}', d)
            except Exception as _exc:
                import traceback
                # print(traceback.print_exc())
            else:
                saved = True

            i += 1

            # Escape condition
            if i > 1000:
                log.error(f'Failed to dump data {k} of type {type(d)} to file')
                break


def _temporary_dump(name: str, data: Any):

    if isinstance(data, np.ndarray):
        np.save(os.path.join(PATH_TEMP, f'{name}.temp.npy'), data)
        return

    log.error(f'Failed to dump data {name} to file. Unknown data type {type(data)}')


def temporary_dump(**data: Dict[str, Any]):
    """Dump arbitrary data to temp folder
    """

    for name, d in data.items():
        _temporary_dump(name, d)


def temporary_exists(*keys):
    """Check if all names in keys list are in temp folder
    """

    contained = []
    for k in keys:
        contained.append(any([True for name in os.listdir(PATH_TEMP) if name.startswith(f'{k}.temp.')]))

    return all(contained)


def _temporary_load(file_path: str) -> Any:

    ext = file_path.split('.')[-1]

    if ext == 'npy':
        return np.load(file_path)
    elif ext == 'txt':
        return ''  # TODO: implement

    return None


def temporary_load(*names: List[str]) -> List[Any]:
    """Load data for names in keys list from temp folder
    """
    # TODO: checks for different types

    data = []

    for name in names:
        d = None
        for existing_file_name in os.listdir(PATH_TEMP):
            file_name = f'{name}.temp.'
            if not existing_file_name.startswith(file_name):
                continue

            d = _temporary_load(os.path.join(PATH_TEMP, existing_file_name))
            break

        data.append(d)

    return data


def temporary_dump_group(name: str, data: Dict[str, Any]):
    group_path = os.path.join(PATH_TEMP, name)
    if not os.path.exists(group_path):
        os.mkdir(group_path)

    temporary_dump(**{os.path.join(name, key): value for key, value in data.items()})


def temporary_group_exists(name: str) -> bool:
    group_path = os.path.join(PATH_TEMP, name)
    return os.path.exists(group_path) and os.path.isdir(group_path)


def temporary_load_group(name: str) -> Dict[str, Any]:
    if not temporary_group_exists(name):
        return {}

    group_path = os.path.join(PATH_TEMP, name)
    return {file_path.split('.temp.')[0]: _temporary_load(os.path.join(group_path, file_path))
            for file_path in os.listdir(group_path)}


class H5File:
    _protocol_prefix = 'protocol'
    _phase_prefix = 'phase'
    _h5_handle: h5py.File

    def __init__(self, file_path):

        # Open new hdf5 file
        self._file_path = f'{file_path}.hdf5'
        log.info(f'Open HDF5 file {self._file_path}')
        self._h5_handle = h5py.File(self._file_path, 'w')

        self.fallback_phase_id = None

    @property
    def _phase_str(self):
        phase_id = vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]

        if phase_id < 0 and self.fallback_phase_id is not None:
            return self.fallback_phase_id

        return f'{self._phase_prefix}{phase_id}'

    @property
    def _protocol_str(self):
        return f'{self._protocol_prefix}{vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID]}'

    def create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        self._create_dataset(dataset_name, shape, data_type)

    def create_phase_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        dataset_name = f'{self._phase_str}/{dataset_name}'
        self._create_dataset(dataset_name, shape, data_type)

    def _create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        # Set chunk size to approx 1MB
        itemsize = np.prod(shape) * np.dtype(data_type).itemsize
        chunksize = (round(np.ceil(10**6/itemsize)),) + shape

        #
        self._h5_handle.create_dataset(dataset_name, shape=(0,) + shape,
                                       dtype=data_type,
                                       maxshape=(None,) + shape,
                                       chunks=chunksize)

    @staticmethod
    def _add_attributes(grp: h5py.Group, attributes: Dict[str, Any]):
        log.debug(f'Write attributes to group {grp}')
        for attr_name, value in attributes.items():
            try:
                grp.attrs[attr_name] = value
            except:
                log.warning(f'Failed to write attribute {attr_name} to file. Type: {type(value)}')

    def add_attributes(self, attributes: Dict[str, Any], group: str = None):
        if group is None:
            grp = self._h5_handle['/']
        else:
            grp = self._h5_handle.require_group(group)
        self._add_attributes(grp, attributes)

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
        if path not in self._h5_handle:
            return

        try:
            # Get dataset
            dataset = self._h5_handle[path]
            # Increase time dimension (0) size by 1
            dataset.resize(dataset.shape[0] + 1, axis=0)
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


def create_video_stream(recording_path: str, attribute: vxattribute.ArrayAttribute,
                        videoformat: str, codec: str, **kwargs):
    global _video_writers
    if attribute.name in _video_writers:
        log.error(f'Tried creating video stream {attribute.name}, which is already open')
        return

    # Define available codec
    # TODO: in future this list should be compiled based on installed deps
    avi_codecs = ['xvid', 'i420', 'mjpg']
    mpeg_codecs = ['h264', 'h265']

    # Determine format and codec and create writer
    log.info(f'Open video stream for {attribute} on path {recording_path}')
    unknown_codec = False
    use_codec = codec
    if videoformat == 'mpeg':
        if codec not in mpeg_codecs:
            unknown_codec = True
            use_codec = mpeg_codecs[0]

        # Create writer
        _writer = MP4VideoWriter(recording_path, attribute, use_codec, **kwargs)

    elif videoformat == 'avi':
        if codec not in avi_codecs:
            unknown_codec = True
            use_codec = avi_codecs[0]

        # Create writer
        _writer = AVIVideoWriter(recording_path, attribute, use_codec, **kwargs)

    else:
        log.error(f'Video format {videoformat} not available. Attribute {attribute.name} is not written to file.')
        return

    if unknown_codec:
        log.warning(f'Video codec {codec} not available for format {videoformat}. Set to default {use_codec}')

    # Add writer to dict
    _video_writers[attribute.name] = _writer


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


class VideoWriter(abc.ABC):

    container_ext: str = None

    def __init__(self, recording_path: str, attribute: vxattribute.ArrayAttribute, codec: str, **kwargs):
        self.attribute: vxattribute.ArrayAttribute = attribute
        self._filepath = os.path.join(recording_path, f'{self.attribute.name}.{self.container_ext}')
        self.codec = codec

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                log.warning(f'{self.__class__.__name__} received extraneous argument {k}:{v}')

    @abc.abstractmethod
    def add_frame(self, frame_data: np.ndarray):
        pass

    @abc.abstractmethod
    def close(self):
        pass


class MP4VideoWriter(VideoWriter):

    container_ext = 'mp4'

    def __init__(self, *args, **kwargs):
        VideoWriter.__init__(self, *args, **kwargs)

        # Set bitrate (usually 3000-5000)
        bitrate = kwargs.pop('bitrate', None)
        if bitrate is None:
            bitrate = 5000
        self.bitrate = bitrate

        # Set framerate
        fps = kwargs.pop('fps', None)
        if fps is None:
            fps = 20
        self.fps = fps

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
            .output(self._filepath,
                    pix_fmt='yuv420p',
                    vcodec=vcodec,
                    r=str(self.fps),
                    video_bitrate=f'{self.bitrate}')
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

        # Set framerate
        fps = kwargs.pop('fps', None)
        if fps is None:
            fps = 20
        self.fps = fps

        downsample = kwargs.pop('downsample', None)
        if downsample is None:
            downsample = 1
        self.downsample = downsample

        # Select codec
        vcodec = 'XVID'
        if self.codec == 'xvid':
            vcodec = 'XVID'
        elif self.codec == 'i420':
            vcodec = 'I420'
        elif self.codec == 'mjpg':
            vcodec = 'MJPG'

        self.width, self.height = self.attribute.shape[:2]

        self.colorplanes = 1
        if len(self.attribute.shape) > 2:
            if self.attribute.shape[2] == 3:
                self.colorplanes = 3
            else:
                # TODO: this should probably raise an error. Currently there's no way to check
                #  whether a file stream has been opened correctly...
                pass


        log.info(f'AVI write to {self._filepath}')

        # Create encoder pipe
        self.writer = cv2.VideoWriter(self._filepath,
                                      cv2.VideoWriter_fourcc(*vcodec),
                                      float(self.fps),
                                      (self.width // self.downsample, self.height // self.downsample),
                                      isColor=self.colorplanes == 3)

    def add_frame(self, frame_data: np.ndarray):
        shape = (self.width // self.downsample, self.height // self.downsample)
        self.writer.write(cv2.resize(np.swapaxes(frame_data, 0, 1), shape))


    def close(self):
        self.writer.release()


class TextWriter:

    container_ext: str = 'txt'

    def __init__(self, recording_path: str, attribute: vxattribute.ArrayAttribute, **kwargs):
        self.attribute: vxattribute.ArrayAttribute = attribute
        self._filepath = os.path.join(recording_path, f'{self.attribute.name}.{self.container_ext}')

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                log.warning(f'{self.__class__.__name__} received extraneous argument {k}:{v}')

        self.textfile = open(self._filepath, 'w')

    @abc.abstractmethod
    def add_line(self, line: str):
        self.textfile.write(f'{line}\n')

    @abc.abstractmethod
    def close(self):
        self.textfile.close()


def create_text_stream(recording_path: str, attribute: vxattribute.ArrayAttribute):
        global _text_writers
        if attribute.name in _text_writers:
            log.error(f'Tried creating text stream {attribute.name}, which is already open')
            return

        # Create writer
        _writer = TextWriter(recording_path, attribute)

        _text_writers[attribute.name] = _writer


def add_to_text_stream(name: str, line: str):
    global _text_writers
    if name not in _text_writers:
        return

    _text_writers[name].add_line(line)


def close_text_streams():
    global _text_writers
    for stream_name in list(_text_writers.keys()):
        stream = _text_writers.get(stream_name)
        if stream is None:
            continue

        log.info(f'Close text stream for {stream.attribute}')
        stream.close()

        del _text_writers[stream_name]
