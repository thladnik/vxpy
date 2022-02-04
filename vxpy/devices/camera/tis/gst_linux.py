"""
MappApp ./devices/camera/tis/gst_linux.py
Copyright (C) 2020 Tim Hladnik

Code based on ./python-common/TIS.py
@ https://github.com/TheImagingSource/Linux-tiscamera-Programming-Samples/

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
import re
import time

import gi

from vxpy.core.camera import AbstractCameraDevice
from vxpy.core import logging

gi.require_version("Gst", "1.0")
gi.require_version("Tcam", "0.1")
from gi.repository import GLib, Gst
import numpy as np
from typing import Dict, List, Union

from vxpy.core import camera

log = logging.getLogger(__name__)


Gst.init([])


def get_connected_devices() -> Dict[str, AbstractCameraDevice]:
    source = Gst.ElementFactory.make("tcamsrc")
    serials = source.get_device_serials()

    devices: Dict[str, AbstractCameraDevice] = dict()

    for sn in serials:
        (return_value, model, identifier, connection_type) = source.get_device_info(sn)
        devices[sn] = CameraDevice(serial=sn, model=model, identifier=identifier, connection_type=connection_type)

    return devices


def get_image_props(fmt: Union[str, camera.Format]) -> tuple:
    if isinstance(fmt, str):
        fmt = camera.Format.from_str(fmt)

    bpp = 4
    dtype = np.uint8
    if fmt.name == 'GRAY16_LE':
        bpp = 1
        dtype = np.uint16
    elif fmt.name == 'GRAY8':
        bpp = 1
    elif fmt.name == 'BGRx':
        bpp = 4

    return dtype, fmt.rate, fmt.width, fmt.height, bpp


class CameraDevice(camera.AbstractCameraDevice):

    def __init__(self, *args, **kwargs):
        camera.AbstractCameraDevice.__init__(self, *args, **kwargs)

        self.img_mat = None
        self.newsample = False
        self.samplelocked = False
        self.sample = None
        self.source = None
        self.appsink = None

    def open(self):
        """Function to make sure selected device works """
        # Try to open device
        source = Gst.ElementFactory.make('tcambin')
        try:
            source.set_property('serial', self.serial)
            state = source.set_state(Gst.State.READY)

            if state is Gst.StateChangeReturn.SUCCESS:
                return True
            else:
                return False
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return False
        # else:
        #     return True
        finally:
            state = source.set_state(Gst.State.NULL)
            source.set_property('serial', '')
            source = None

    def start_stream(self):
        # Create pipeline
        p = 'tcambin name=source ! capsfilter name=caps ! appsink name=sink'
        try:
            self.pipeline = Gst.parse_launch(p)
        except GLib.Error as code:
            print(f'Error creating pipeline: {code}')
            raise

        self.samplelocked = False

        # Query the source module.
        self.source = self.pipeline.get_by_name('source')

        # Query a pointer to the appsink, so we can assign the callback function.
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.set_property('max-buffers', 5)
        self.appsink.set_property('drop', 1)
        self.appsink.set_property('emit-signals', 1)

        self.source.set_property('serial', self.serial)

        caps = Gst.Caps.new_empty()
        fmt_str = f'video/x-raw,format={self._fmt.name},' \
                  f'width={self._fmt.width},' \
                  f'height={self._fmt.height},' \
                  f'framerate={int(self._fmt.rate)}/1'
        structure = Gst.Structure.new_from_string(fmt_str)

        caps.append_structure(structure)

        structure.free()
        capsfilter = self.pipeline.get_by_name('caps')
        capsfilter.set_property('caps', caps)

        try:
            self.pipeline.set_state(Gst.State.PLAYING)
            code = self.pipeline.get_state(5000000000)
            # code = self.pipeline.get_state(1000000000)
            if code[1] != Gst.State.PLAYING:
                print(f"Error starting pipeline. {code}")
                return False

        except:  # GError as error:
            print("Error starting pipeline: {0}".format("unknown too"))
            raise
        return True

    def end_stream(self):
        pass
        # print(f'End stream from camera device {self.id}')
        # self.pipeline.set_state(Gst.State.PAUSED)
        # self.pipeline.set_state(Gst.State.READY)
        # self.pipeline.set_state(Gst.State.NULL)
        #
        # while True:
        #     code = self.pipeline.get_state(5000000000)
        #     if code[1] == Gst.State.NULL:
        #         self.source.set_state(Gst.State.PAUSED)
        #         self.source.set_state(Gst.State.READY)
        #         self.source.set_state(Gst.State.NULL)
        #         while True:
        #             code = self.source.get_state(5000000000)
        #             if code[1] == Gst.State.NULL:
        #                 break
        #             print('Source', code)
        #             time.sleep(0.1)
        #
        #             self.appsink.set_state(Gst.State.PAUSED)
        #             self.appsink.set_state(Gst.State.READY)
        #             self.appsink.set_state(Gst.State.NULL)
        #             while True:
        #                 code = self.appsink.get_state(5000000000)
        #                 if code[1] == Gst.State.NULL:
        #                     break
        #                 print('Appsink', code)
        #                 time.sleep(0.1)
        #
        #         break
        #     print('Pipe', code)
        #     time.sleep(0.1)

    def get_formats(self) -> List[camera.Format]:
        """Return formats for given device
        """

        if bool(self._avail_formats):
            return self._avail_formats

        # Open device
        source = Gst.ElementFactory.make("tcambin")
        source.set_property("serial", self.serial)
        source.set_state(Gst.State.READY)
        caps = source.get_static_pad("src").query_caps()

        # Read all available formats
        for x in range(caps.get_size()):
            structure = caps.get_structure(x)
            f = structure.get_value("format")
            # name = structure.get_name()

            width = structure.get_value("width")
            height = structure.get_value("height")

            try:
                rates = structure.get_value("framerate")
            except TypeError:
                # Workaround for missing GstValueList support in GI
                substr = structure.to_string()[structure.to_string().find("framerate="):]
                # try for frame rate lists
                field, values, remain = re.split("{|}", substr, maxsplit=3)
                rates = [x.strip() for x in values.split(",")]

            for rate in rates:
                self._avail_formats.append(camera.Format(f, width, height, rate.split('/')[0]))

        # Close device
        source.set_state(Gst.State.NULL)
        source.set_property('serial', '')
        source = None

        return self._avail_formats

    def snap_image(self, *args, **kwargs):
        pass

    def get_image(self):

        self.newsample = True
        if self.samplelocked is False:
            try:
                self.sample = self.appsink.get_property('last-sample')

                self.samplelocked = True
                buf = self.sample.get_buffer()
                mem = buf.get_all_memory()
                success, info = mem.map(Gst.MapFlags.READ)
                if success:
                    data = info.data
                    mem.unmap(info)

                    dtype, rate, w, h, bpp = get_image_props(self._fmt)

                    self.img_mat = np.ndarray((h, w, bpp), buffer=data, dtype=dtype)

                    self.newsample = False
                    self.samplelocked = False

            except GLib.Error as error:
                print('Error on_new_buffer pipeline: {0}'.format(error))
                raise

        return self.img_mat

    def set_exposure(self, e):
        # TODO: set exposure
        pass

    def set_gain(self, g):
        # TODO: set gain
        pass
