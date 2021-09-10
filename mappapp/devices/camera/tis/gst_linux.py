import re
import sys

import gi
gi.require_version("Gst", "1.0")
gi.require_version("Tcam", "0.1")
from gi.repository import GLib, GObject, Gst, Tcam
import numpy as np

from mappapp.core import camera

Gst.init([])

def get_connected_devices():
    source = Gst.ElementFactory.make("tcamsrc")
    serials = source.get_device_serials()

    devices = dict()

    for sn in serials:
        (return_value, model, identifier, connection_type) = source.get_device_info(sn)
        devices[sn] = CameraDevice(serial=sn, model=model, identifier=identifier, connection_type=connection_type)

    return devices


def get_image_props(fmt):
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

    def set_exposure(self, e):
        pass

    def set_gain(self, g):
        pass

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
            return False
        # else:
        #     return True
        finally:
            state = source.set_state(Gst.State.NULL)
            source.set_property('serial', '')
            source = None

    def get_formats(self):
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

    def start_stream(self):
        # Create pipeline
        p = 'tcambin name=source ! capsfilter name=caps ! appsink name=sink'
        try:
            self.pipeline = Gst.parse_launch(p)
        except GLib.Error as error:
            print(f'Error creating pipeline: {error}')
            raise

        self.samplelocked = False

        # Quere the source module.
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
            error = self.pipeline.get_state(5000000000)
            if error[1] != Gst.State.PLAYING:
                print("Error starting pipeline. {0}".format(""))
                return False

        except:  # GError as error:
            print("Error starting pipeline: {0}".format("unknown too"))
            raise

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

                    self.img_mat = np.ndarray(
                        (h,
                         w,
                         bpp),
                        buffer=data,
                        dtype=dtype)

                    self.newsample = False
                    self.samplelocked = False

            except GLib.Error as error:
                print('Error on_new_buffer pipeline: {0}'.format(error))
                raise

        return self.img_mat
