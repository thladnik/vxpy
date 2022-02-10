"""
vxPy ./devices/camera/tis_linux_gst.py
Copyright (C) 2022 Tim Hladnik

Based on TIS' tiscamera usage examples for Python
at https://github.com/TheImagingSource/Linux-tiscamera-Programming-Samples

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
from contextlib import contextmanager

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Tcam', '0.1')
from gi.repository import GLib, GObject, Gst, Tcam
import re
import time
from typing import List, Type, Tuple, Union
import numpy as np

from vxpy.core import camera_device, logger
from vxpy.core.camera_device import AbstractCameraDevice, CameraFormat

log = logger.getLogger(__name__)


class CameraDevice(camera_device.AbstractCameraDevice):
    # TODO: fix bug where some randomly occurring problem during the closing of the gstreamer pipeline
    #  results in an inaccessible TIS camera (until re-plugging the cammera)

    manufacturer = 'TIS'

    _exposure_unit = camera_device.ExposureUnit.microseconds

    sink_formats = {'GRAY16_LE': (1, np.uint16),
                    'GRAY8': (1, np.uint8),
                    'BGRx': (4, np.uint8)}

    def __init__(self, *args, **kwargs):
        camera_device.AbstractCameraDevice.__init__(self, *args, **kwargs)

        Gst.init([])
        self.frame: np.ndarray = None
        self.sample: Gst.Sample = None
        self.new_sample: bool = False
        self.sample_locked: bool = False
        self._available_formats: list = []

    def _set_property(self, property_name: str, value: Union[int, float]):
        try:
            _property = self.source.get_tcam_property(property_name)
            if type(value) is int and _property.type == 'double':
                value = float(value)
            elif type(value) is float and _property.type == 'integer':
                value = int(value)
            log.debug(f'Set property value of property {property_name} to {value} on device {self}')

            result = self.source.set_tcam_property(property_name, GObject.Value(type(value), value))

            if not result:
                log.warning(f'Failed to set property {property_name} to {value} on device {self}. '
                            f'Value type is {type(value)} and property type is {_property.type}. '
                            f'Value {value} range {_property.min}-{_property.max}')

        except Exception as error:
            log.warning(f'Error setting property {property_name} to {value} on device {self}// {error}')

    def _set_property_switch(self, property_name: str, switch_name: str, value: bool):
        try:
            value = bool(value)

            log.debug(f'Set property switch {property_name}:{switch_name} to {value} on device {self}')
            result = self.source.set_tcam_property(f'{property_name} {switch_name}', GObject.Value(type(value), value))
            if not result:
                log.warning(f'Failed to set property switch {property_name}:{switch_name} '
                            f'to {value} on device {self}.')

        except Exception as error:
            log.warning(f'Error setting property switch {property_name}:{switch_name} to {value} on device {self}// {error}')
            raise

    def _print_property_list(self):
        for name in self.source.get_tcam_property_names():
            print(name)

    @contextmanager
    def _capture_from_source(self):
        # Open device
        source = Gst.ElementFactory.make('tcambin')
        source.set_property('serial', self.serial)
        source.set_state(Gst.State.READY)
        caps = source.get_static_pad('src').query_caps()

        try:
            yield caps

        finally:
            # Close device
            source.set_state(Gst.State.NULL)
            source.set_property('serial', '')
            source = None

    def get_format_list(self) -> List[CameraFormat]:

        if bool(self._available_formats):
            return self._available_formats

        with self._capture_from_source() as caps:

            # Read all available formats
            for x in range(caps.get_size()):
                structure = caps.get_structure(x)
                f = structure.get_value('format')
                width = structure.get_value('width')
                height = structure.get_value('height')

                self._available_formats.append(camera_device.CameraFormat(f, width, height, ))

        return self._available_formats

    def _framerate_list(self, _format: CameraFormat) -> List[float]:

        log.debug(f'Read framerates for format {_format} on device {self}')
        framerates = []
        with self._capture_from_source() as caps:

            # Go through all available formats until we find _format
            for x in range(caps.get_size()):
                structure = caps.get_structure(x)
                f = structure.get_value('format')
                width = structure.get_value('width')
                height = structure.get_value('height')

                if _format != camera_device.CameraFormat(f, width, height):
                    continue

                # Get framerates
                try:
                    rates = structure.get_value('framerate')
                except TypeError:
                    # Workaround for missing GstValueList support in GI
                    substr = structure.to_string()[structure.to_string().find('framerate='):]
                    # try for frame rate lists
                    field, values, remain = re.split('{|}', substr, maxsplit=3)
                    rates = [x.strip() for x in values.split(',')]

                framerates = [int(rate.split('/')[0]) for rate in rates]

        if not bool(framerates):
            log.warning(f'No framerates available for format {_format} on device {self}')

        framerates = list(set(framerates))
        framerates.sort()

        return framerates

    def _reset_source(self):
        # Open device
        source = Gst.ElementFactory.make('tcambin')
        source.set_property('serial', self.serial)
        source.set_state(Gst.State.READY)

        # Close device
        source.set_state(Gst.State.NULL)
        source.set_property('serial', '')
        source = None

    @classmethod
    def get_camera_list(cls) -> List[AbstractCameraDevice]:
        source = Gst.ElementFactory.make('tcamsrc')
        serials = source.get_device_serials()

        devices = []

        for sn in serials:
            return_value, model, identifier, connection_type = source.get_device_info(sn)
            devices.append(CameraDevice(serial=sn, model=model))

        return devices

    def _start_stream(self) -> bool:
        # Create pipeline
        p = 'tcambin name=source ! capsfilter name=caps ! appsink name=sink'

        log.debug(f'Create pipeline for device {self}: {p}')
        try:
            self.pipeline = Gst.parse_launch(p)
        except GLib.Error as code:
            log.error(f'Error creating pipeline for device {self}: {code}')
            return False

        # Query sink
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.set_property('max-buffers', 5)
        self.appsink.set_property('drop', 1)
        self.appsink.set_property('emit-signals', 1)

        # Query and set the source module
        self.source = self.pipeline.get_by_name('source')
        self.source.set_property('serial', self.serial)

        # Set capture
        caps = Gst.Caps.new_empty()
        fmt_str = f'video/x-raw,' \
                  f'format={self.format.dtype},' \
                  f'width={self.format.width},' \
                  f'height={self.format.height},' \
                  f'framerate={int(self.framerate)}/1'
        log.debug(f'Set capture on pipeline for device {self}: {fmt_str}')
        structure = Gst.Structure.new_from_string(fmt_str)
        caps.append_structure(structure)
        structure.free()
        capsfilter = self.pipeline.get_by_name('caps')
        capsfilter.set_property('caps', caps)

        # Start pipeline
        log.debug(f'Start pipeline for device {self}')
        try:
            self.pipeline.set_state(Gst.State.PLAYING)
            code = self.pipeline.get_state(5000000000)
            if code[1] != Gst.State.PLAYING:
                log.error(f'Unable to start pipeline for device {self}: {code}')
                return False

        except Exception as error:  # GError as error:
            log.error(f'Error starting pipeline for device {self}: {error}')
            return False

        log.debug(f'Pipeline started for device {self}')

        # Set properties
        self._set_property_switch('Gain', 'Auto', False)
        self._set_property_switch('Exposure', 'Auto', False)
        self._set_property('Exposure Time (us)', self.exposure)
        self._set_property('Gain', self.gain)
        # self._set_property('Gain (dB/100)', 1000)

        return True

    def snap_image(self) -> bool:
        return True

    def get_image(self) -> np.ndarray:
        self.new_sample = True
        if self.sample_locked is False:
            try:
                self.sample = self.appsink.get_property('last-sample')

                self.sample_locked = True
                buf = self.sample.get_buffer()
                mem = buf.get_all_memory()
                success, info = mem.map(Gst.MapFlags.READ)
                if success:
                    data = info.data
                    mem.unmap(info)

                    dtype = self.format.dtype
                    plane_num = self.sink_formats[dtype][0]
                    np_dtype = self.sink_formats[dtype][1]

                    self.frame = np.ndarray((self.format.height, self.format.width, plane_num),
                                            buffer=data,
                                            dtype=np_dtype)

                    self.new_sample = False
                    self.sample_locked = False

            except GLib.Error as error:
                log.error(f'Error on get_image from pipeline: {error}')
                raise

        return self.frame

    def end_stream(self) -> bool:

        # Close device
        # state = self.source.set_state(Gst.State.NULL)
        log.debug(f'Close pipeline for camera {self}')
        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.set_state(Gst.State.NULL)
        # self.source.set_property('serial', '')
        # self.source = None

        return True


if __name__ == '__main__':
    import yaml
    from vxpy.core import camera_device

    data = yaml.safe_load(
        '''
        api: vxpy.devices.camera.tis_linux_gst
        serial: 49410244
        model: DMK 23U618
        dtype: GRAY8
        width: 640
        height: 480
        framerate: 100
        exposure: 1.5
        gain: 64
        '''
    )
    c1 = camera_device.get_camera(data)
    fmts = c1.get_format_list()
    framerates = c1._framerate_list(fmts[0])
    print(fmts[0], framerates)
