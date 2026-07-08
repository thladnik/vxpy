# -*- coding: utf-8 -*-
"""Custom file container formats for vxPy save-to-disk operations.

Provides the :class:`H5File` container, video writer classes
(:class:`MP4VideoWriter`, :class:`AVIVideoWriter`), a :class:`TextWriter`,
and a collection of module-level helper functions that delegate to the
currently open file container instance.  Also includes utilities for dumping
data to a temporary folder.
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
    """Init.
    """
    global log
    log = vxlogger.getLogger(f'{__name__}[{vxipc.LocalProcess.name}]')


def _noinstance():
    """ noinstance.
    """
    return _instance is None


def register_file_type(type_name: str, type_class):
    """Register file type.
    
    Parameters
    ----------
    type_name : str
        Public key used to select this container type in :func:`new`.
    type_class : Any
        Container class implementing the expected file API (create/add/close).
    """
    _file_types[type_name] = type_class


def new(file_type: str, file_path: str):
    """Create new container instance
    
    Parameters
    ----------
    file_type : str
        Registered file container type name.
    file_path : str
        Output path without extension; container-specific extension is appended.
    """
    global _instance, _file_types

    assert file_type in _file_types, f'Unregistered file type {file_type}'

    if not _noinstance():
        _instance.close()

    _instance = _file_types[file_type](file_path)


def set_fallback_phase_id(phase_id: str):
    """Set fallback phase id.
    
    Parameters
    ----------
    phase_id : str
        Group name used when no positive phase id is available.
    """
    if _noinstance():
        return

    _instance.fallback_phase_id = phase_id


def close():
    """Close.
    """
    global _instance

    if _noinstance():
        return

    # Close instance
    _instance.close()
    _instance = None


def create_dataset(dataset_name: str, shape: Tuple[int, ...], data_type: Any):
    """Create dataset.
    
    Parameters
    ----------
    dataset_name : str
        Name of the root-level dataset to create.
    shape : Tuple[int, ...]
        Per-sample data shape (excluding the leading time axis).
    data_type : Any
        Numpy dtype of dataset values.
    """
    global _instance
    if _noinstance():
        return

    log.debug(f'Create dataset {dataset_name}, shape {shape}, dtype {data_type}')

    # Call on instance
    _instance.create_dataset(dataset_name, shape, data_type)


def create_phase_dataset(dataset_name: str, shape: Tuple[int, ...], data_type: Any):
    """Create phase dataset.
    
    Parameters
    ----------
    dataset_name : str
        Dataset name under the current phase group.
    shape : Tuple[int, ...]
        Per-sample data shape (excluding the leading time axis).
    data_type : Any
        Numpy dtype of dataset values.
    """
    global _instance
    if _noinstance():
        return

    log.debug(f'Create phase dataset {dataset_name}, '
              f'shape {shape}, dtype {data_type}, '
              f'phase_id {vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]}')

    # Call on instance
    _instance.create_phase_dataset(dataset_name, shape, data_type)


def add_attributes(attributes: Dict[str, Any]):
    """Add attributes.
    
    Parameters
    ----------
    attributes : Dict[str, Any]
        Root-level file attributes to persist.
    """
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_attributes(attributes)


def add_protocol_attributes(attributes: Dict[str, Any]):
    """Add protocol attributes.
    
    Parameters
    ----------
    attributes : Dict[str, Any]
        Attributes written to the active protocol group.
    """
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_protocol_attributes(attributes)


def add_phase_attributes(attributes: Dict[str, Any]):
    """Add phase attributes.
    
    Parameters
    ----------
    attributes : Dict[str, Any]
        Attributes written to the active phase group.
    """
    global _instance
    if _noinstance():
        return

    # There are no negative phase ids
    # if vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] < 0:
    #     return

    # Call on instance
    _instance.add_phase_attributes(attributes)


def add_to_phase_dataset(dataset_name: str, data: Any):
    """Add to phase dataset.
    
    Parameters
    ----------
    dataset_name : str
        Dataset name under the active phase group.
    data : Any
        Single sample appended along the dataset time axis.
    """
    global _instance
    if _noinstance():
        return

    # There are no negative phase ids
    # if vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] < 0:
    #     return

    # Call on instance
    _instance.add_to_phase_dataset(dataset_name, data)


def add_to_dataset(dataset_name: str, data: Any):
    """Add to dataset.
    
    Parameters
    ----------
    dataset_name : str
        Root-level dataset name.
    data : Any
        Single sample appended along the dataset time axis.
    """
    global _instance
    if _noinstance():
        return

    # Call on instance
    _instance.add_to_dataset(dataset_name, data)


def dump(data, group: str = None):
    """Dump arbitrary data into the current container instance
    
    Parameters
    ----------
    data : Any
        Mapping of values to serialize into attributes and numeric array datasets.
    group : str
        Optional HDF5 group prefix where dumped content is written.
    """

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
    """Dump data to a temporary file
    
    Parameters
    ----------
    name : str
        Temporary entry name used to build the file path.
    data : Any
        Data object to persist in ``PATH_TEMP``.
    """

    if isinstance(data, np.ndarray):
        np.save(os.path.join(PATH_TEMP, f'{name}.temp.npy'), data)
        return

    log.error(f'Failed to dump data {name} to file. Unknown data type {type(data)}')


def temporary_dump(**data: Dict[str, Any]):
    """Dump multiple data to a temporary file
    
    Parameters
    ----------
    **data : Dict[str, Any]
        Named values forwarded to :func:`_temporary_dump`.
    """

    for name, d in data.items():
        _temporary_dump(name, d)


def temporary_exists(*keys):
    """Check if temporary data for key in keys exists
    
    Parameters
    ----------
    *keys : Any
        Temporary entry names to check in ``PATH_TEMP``.
    """

    contained = []
    for k in keys:
        contained.append(any([True for name in os.listdir(PATH_TEMP) if name.startswith(f'{k}.temp.')]))

    return all(contained)


def _temporary_load(file_path: str) -> Any:
    """Load temporary data from file path
    
    Parameters
    ----------
    file_path : str
        Full path to a temporary data file.
    """

    ext = file_path.split('.')[-1]

    if ext == 'npy':
        return np.load(file_path)
    elif ext == 'txt':
        return ''  # TODO: implement

    return None


def temporary_load(*names: List[str]) -> List[Any]:
    """Load temporary data from key in names
    
    Parameters
    ----------
    *names : List[str]
        Temporary entry names to resolve and load.

    Returns
    -------
    List[Any]
        Loaded objects in the same order as ``names``.
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
    """Temporary dump group.
    
    Parameters
    ----------
    name : str
        Folder name under ``PATH_TEMP`` for grouped temporary entries.
    data : Dict[str, Any]
        Mapping of entry names to values stored inside the group.
    """
    group_path = os.path.join(PATH_TEMP, name)
    if not os.path.exists(group_path):
        os.mkdir(group_path)

    temporary_dump(**{os.path.join(name, key): value for key, value in data.items()})


def temporary_group_exists(name: str) -> bool:
    """Temporary group exists.
    
    Parameters
    ----------
    name : str
        Temporary group folder name.

    Returns
    -------
    bool
        ``True`` when the temporary group folder exists.
    """
    group_path = os.path.join(PATH_TEMP, name)
    return os.path.exists(group_path) and os.path.isdir(group_path)


def temporary_load_group(name: str) -> Dict[str, Any]:
    """Temporary load group.
    
    Parameters
    ----------
    name : str
        Temporary group folder name.

    Returns
    -------
    Dict[str, Any]
        Mapping of stored entry names to loaded values for the group.
    """
    if not temporary_group_exists(name):
        return {}

    group_path = os.path.join(PATH_TEMP, name)
    return {file_path.split('.temp.')[0]: _temporary_load(os.path.join(group_path, file_path))
            for file_path in os.listdir(group_path)}


class H5File:
    """H5File class."""

    _protocol_prefix = 'protocol'
    _phase_prefix = 'phase'
    _h5_handle: h5py.File

    def __init__(self, file_path):
        """  init  .
        
        Parameters
        ----------
        file_path : Any
            Output file base path; ``.hdf5`` is appended automatically.
        """

        # Open new hdf5 file
        self._file_path = f'{file_path}.hdf5'
        log.info(f'Open HDF5 file {self._file_path}')
        self._h5_handle = h5py.File(self._file_path, 'w')

        self.fallback_phase_id = None

    @property
    def _phase_str(self):
        """ phase str.
        """
        phase_id = vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]

        if phase_id < 0 and self.fallback_phase_id is not None:
            return self.fallback_phase_id

        return f'{self._phase_prefix}{phase_id}'

    @property
    def _protocol_str(self):
        """ protocol str.
        """
        return f'{self._protocol_prefix}{vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID]}'

    def create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        """Create dataset.
        
        Parameters
        ----------
        dataset_name : str
            Dataset path under the root group.
        shape : Tuple[int, ...]
            Per-sample shape (excluding time axis).
        data_type : Any
            Numpy dtype used for the dataset.
        """
        self._create_dataset(dataset_name, shape, data_type)

    def create_phase_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        """Create phase dataset.
        
        Parameters
        ----------
        dataset_name : str
            Dataset name inside the current phase group.
        shape : Tuple[int, ...]
            Per-sample shape (excluding time axis).
        data_type : Any
            Numpy dtype used for the dataset.
        """
        dataset_name = f'{self._phase_str}/{dataset_name}'
        self._create_dataset(dataset_name, shape, data_type)

    def _create_dataset(self, dataset_name: str, shape: Tuple[int, ...], data_type):
        """ create dataset.
        
        Parameters
        ----------
        dataset_name : str
            Full dataset path to create.
        shape : Tuple[int, ...]
            Per-sample shape (excluding time axis).
        data_type : Any
            Numpy dtype used for the dataset.
        """
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
        """ add attributes.
        
        Parameters
        ----------
        grp : h5py.Group
            Target HDF5 group receiving attributes.
        attributes : Dict[str, Any]
            Attribute key/value pairs to write.
        """
        log.debug(f'Write attributes to group {grp}')
        for attr_name, value in attributes.items():
            try:
                grp.attrs[attr_name] = value
            except:
                log.warning(f'Failed to write attribute {attr_name} to file. Type: {type(value)}')

    def add_attributes(self, attributes: Dict[str, Any], group: str = None):
        """Add attributes.
        
        Parameters
        ----------
        attributes : Dict[str, Any]
            Attribute key/value pairs to write.
        group : str
            Optional group path; root is used when omitted.
        """
        if group is None:
            grp = self._h5_handle['/']
        else:
            grp = self._h5_handle.require_group(group)
        self._add_attributes(grp, attributes)

    def add_protocol_attributes(self, attributes: Dict[str, Any]):
        """Add protocol attributes.
        
        Parameters
        ----------
        attributes : Dict[str, Any]
            Attributes written to the current protocol group.
        """
        # Get group path from current record_protocol_group_id
        grp = self._h5_handle.require_group(self._protocol_str)

        # Update protocol group attributes
        self._add_attributes(grp, attributes)

    def add_phase_attributes(self, attributes: Dict[str, Any]):
        """Add phase attributes.
        
        Parameters
        ----------
        attributes : Dict[str, Any]
            Attributes written to the current phase group.
        """
        # Get group path from current record_group_id
        grp = self._h5_handle.require_group(self._phase_str)

        # Update phase group attributes
        self._add_attributes(grp, attributes)

    def add_to_dataset(self, dataset_name: str, data: Any):
        """Add to dataset.
        
        Parameters
        ----------
        dataset_name : str
            Dataset path under the root group.
        data : Any
            Single sample appended to the dataset.
        """
        self._add_to_dataset(dataset_name, data)

    def add_to_phase_dataset(self, dataset_name: str, data: Any):
        """Add to phase dataset.
        
        Parameters
        ----------
        dataset_name : str
            Dataset name inside the current phase group.
        data : Any
            Single sample appended to the dataset.
        """
        dataset_name = f'{self._phase_str}/{dataset_name}'
        self._add_to_dataset(dataset_name, data)

    def _add_to_dataset(self, path: str, data: Any):
        """ add to dataset.
        
        Parameters
        ----------
        path : str
            Full HDF5 dataset path.
        data : Any
            Single sample appended to the dataset.
        """
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
        """Close.
        """

        log.info(f'Close HDF5 file {self._file_path}')

        # Close hdf5 file
        self._h5_handle.close()


def create_video_stream(recording_path: str, attribute: vxattribute.ArrayAttribute,
                        videoformat: str, codec: str, **kwargs):
    """Create video stream.
    
    Parameters
    ----------
    recording_path : str
        Directory where encoded video files are created.
    attribute : vxattribute.ArrayAttribute
        Array attribute providing video frames.
    videoformat : str
        Output container family (e.g. ``'mpeg'`` or ``'avi'``).
    codec : str
        Requested codec identifier within the selected format.
    **kwargs : Any
        Optional writer-specific arguments such as ``fps`` or ``bitrate``.
    """
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
    """Add to video stream.
    
    Parameters
    ----------
    name : str
        Attribute/stream name used as writer lookup key.
    frame_data : np.ndarray
        Image frame appended to the open stream.
    """
    global _video_writers
    if name not in _video_writers:
        return

    _video_writers[name].add_frame(frame_data)


def close_video_streams():
    """Close video streams.
    """
    global _video_writers
    for stream_name in list(_video_writers.keys()):
        stream = _video_writers.get(stream_name)
        if stream is None:
            continue

        log.info(f'Close video stream for {stream.attribute}')
        stream.close()

        del _video_writers[stream_name]


class VideoWriter(abc.ABC):
    """VideoWriter class."""

    container_ext: str = None

    def __init__(self, recording_path: str, attribute: vxattribute.ArrayAttribute, codec: str, **kwargs):
        """  init  .
        
        Parameters
        ----------
        recording_path : str
            Directory where the output container file is written.
        attribute : vxattribute.ArrayAttribute
            Source attribute defining frame shape and stream name.
        codec : str
            Codec identifier used by the concrete writer implementation.
        **kwargs : Any
            Optional writer-specific constructor arguments.
        """
        self.attribute: vxattribute.ArrayAttribute = attribute
        self._filepath = os.path.join(recording_path, f'{self.attribute.name}.{self.container_ext}')
        self.codec = codec

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                log.warning(f'{self.__class__.__name__} received extraneous argument {k}:{v}')

    @abc.abstractmethod
    def add_frame(self, frame_data: np.ndarray):
        """Add frame.
        
        Parameters
        ----------
        frame_data : np.ndarray
            Video frame to encode and append.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """Close.
        """
        pass


class MP4VideoWriter(VideoWriter):
    """MP4VideoWriter class."""

    container_ext = 'mp4'

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`VideoWriter`.
        **kwargs : Any
            MP4 writer options such as ``fps`` and ``bitrate``.
        """
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
        """Add frame.
        
        Parameters
        ----------
        frame_data : np.ndarray
            Raw frame array written to the ffmpeg stdin pipe.
        """
        self.process.stdin.write(frame_data.astype(np.uint8).T.tobytes())

    def close(self):
        """Close.
        """
        self.process.stdin.close()
        self.process.wait()


class AVIVideoWriter(VideoWriter):
    """AVIVideoWriter class."""

    container_ext = 'avi'

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`VideoWriter`.
        **kwargs : Any
            AVI writer options such as ``fps`` and ``downsample``.
        """
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
                # TODO: this should probably raise an error.
                pass

        log.info(f'AVI write to {self._filepath}')

        # Create encoder pipe
        self.writer = cv2.VideoWriter(self._filepath,
                                      cv2.VideoWriter_fourcc(*vcodec),
                                      float(self.fps),
                                      (self.width // self.downsample, self.height // self.downsample),
                                      isColor=self.colorplanes == 3)

    def add_frame(self, frame_data: np.ndarray):
        """Add frame.
        
        Parameters
        ----------
        frame_data : np.ndarray
            Raw frame array resized and encoded by OpenCV.
        """
        shape = (self.width // self.downsample, self.height // self.downsample)
        self.writer.write(cv2.resize(np.swapaxes(frame_data, 0, 1), shape))

    def close(self):
        """Close.
        """
        self.writer.release()


class TextWriter:
    """TextWriter class."""

    container_ext: str = 'txt'

    def __init__(self, recording_path: str, attribute: vxattribute.ArrayAttribute, **kwargs):
        """  init  .
        
        Parameters
        ----------
        recording_path : str
            Directory where the text file is created.
        attribute : vxattribute.ArrayAttribute
            Source attribute defining stream name.
        **kwargs : Any
            Optional constructor arguments (currently ignored with warning).
        """
        self.attribute: vxattribute.ArrayAttribute = attribute
        self._filepath = os.path.join(recording_path, f'{self.attribute.name}.{self.container_ext}')

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                log.warning(f'{self.__class__.__name__} received extraneous argument {k}:{v}')

        self.textfile = open(self._filepath, 'w')

    @abc.abstractmethod
    def add_line(self, line: str):
        """Add line.
        
        Parameters
        ----------
        line : str
            Text line appended to the stream file.
        """
        self.textfile.write(f'{line}\n')

    @abc.abstractmethod
    def close(self):
        """Close.
        """
        self.textfile.close()


def create_text_stream(recording_path: str, attribute: vxattribute.ArrayAttribute):
    """Create text stream.
    
    Parameters
    ----------
    recording_path : str
        Directory where the text stream file is created.
    attribute : vxattribute.ArrayAttribute
        Attribute whose values are written to plaintext.
    """
    global _text_writers
    if attribute.name in _text_writers:
        log.error(f'Tried creating text stream {attribute.name}, which is already open')
        return

    # Create writer
    _writer = TextWriter(recording_path, attribute)

    _text_writers[attribute.name] = _writer


def add_to_text_stream(name: str, line: str):
    """Add to text stream.
    
    Parameters
    ----------
    name : str
        Stream name used as writer lookup key.
    line : str
        Text line appended to the stream.
    """
    global _text_writers
    if name not in _text_writers:
        return

    _text_writers[name].add_line(line)


def close_text_streams():
    """Close text streams.
    """
    global _text_writers
    for stream_name in list(_text_writers.keys()):
        stream = _text_writers.get(stream_name)
        if stream is None:
            continue

        log.info(f'Close text stream for {stream.attribute}')
        stream.close()

        del _text_writers[stream_name]
