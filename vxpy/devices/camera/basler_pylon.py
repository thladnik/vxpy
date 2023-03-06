"""
vxPy ./devices/camera/basler_pylon.py
Copyright (C) 2022 Tim Hladnik

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
from collections import OrderedDict
from typing import List, Dict, Tuple, Any, Union, Type

import numpy as np
from pypylon import pylon

import vxpy.core.devices.camera as vxcamera
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class BaslerCamera(vxcamera.CameraDevice):

    def __init__(self, *args, **kwargs):
        vxcamera.CameraDevice.__init__(self, *args, **kwargs)

        self.next_time_get_image = vxipc.get_time()

        self.settings = {}
        self.metadata = {}

    def get_metadata(self) -> Dict[str, Any]:
        return self.metadata

    def get_settings(self) -> Dict[str, Any]:
        return self.settings

    @property
    def frame_rate(self) -> float:
        return self.properties['frame_rate']

    @property
    def width(self) -> float:
        return self.properties['width']

    @property
    def height(self) -> float:
        return self.properties['height']

    @classmethod
    def get_camera_list(cls) -> List[vxcamera.CameraDevice]:
        camera_list = []
        for cam_info in pylon.TlFactory.GetInstance().EnumerateDevices():
            props = {'serial': cam_info.GetSerialNumber(), 'model': cam_info.GetModelName()}
            cam = BaslerCamera(**props)
            camera_list.append(cam)

        return camera_list

    def _open(self) -> bool:
        camera = None
        for cam_info in pylon.TlFactory.GetInstance().EnumerateDevices():
            serial = cam_info.GetSerialNumber()
            model = cam_info.GetModelName()

            # Search for camera matching serial number and model name
            if str(serial) == str(self.properties['serial']) and model == self.properties['model']:
                camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(cam_info))
                break

        # Check if camera was found
        if camera is None:
            log.error(f'Unable to connect to {self}. Device not found')
            return False

        # Open camera device
        self._device = camera
        self._device.Open()

        return True

    def _read_pfs_file(self, path: str) -> Tuple[List, Dict[str, Any]]:
        """Read a persistence file with Basler camera properties

        Persistence files (*.pfs) can be exported/saved in the pylon Viewer under Camera > Save features...
        """
        meta = []
        ops = {}
        i = 0
        with open(path, 'r') as pfs_file:
            for line in pfs_file:
                line = line.strip('\n')
                if i < 3:
                    meta.append(line)
                    i += 1
                    continue

                key, val = line.split('\t')
                ops[key] = val

        return meta, ops

    def get_prop(self, key: str) -> Union[Any, None]:
        if self._device is None:
            return

        try:
            value = self._device.__getattr__(key).GetValue()
        except Exception as exc:
            log.error(f'Unable to get camera property {key}')
        else:
            return value
        return None

    def get_prop_type(self, key: str) -> Union[Type, None]:
        if self._device is None:
            return

        value = self.get_prop(key)
        if value is not None:
            return type(value)
        return None

    def set_prop(self, key: str, value: Any):
        if self._device is None:
            return

        log.debug(f'Set property {key}: {value}')
        try:
            # Fix off/on false/true pyyaml/pylon issue
            if key in ['GainAuto', 'ExposureAuto']:
                value = 'On' if value else 'Off'
            # Set property
            self._device.__getattr__(key).SetValue(value)
        except Exception as exc:
            log.error(f'Unable to set camera property {key} to {value}')

    def _start_stream(self) -> bool:

        # Set acquisition parameters
        settings = OrderedDict({})

        # TODO:
        #  PyYAML (very smartly) by default, parses Off/On values as False/True booleans
        #  Pylon (again, very smartly), uses Off/On string values for flags like GainAuto/ExposureAuto
        #  > Fix this someday, but not today

        # Look for full persistance file
        if 'pfs_file' in self.properties:
            meta, props = self._read_pfs_file(self.properties['pfs_file'])
            # Properties from pfs file need to be cast to correct type
            for key, value in props.items():
                prop_type = self.get_prop_type(key)
                if prop_type is None:
                    continue
                settings[key] = prop_type(value)

        # Update with directly configures props
        if 'basler_props' in self.properties:
            settings.update(self.properties['basler_props'])

        # Make sure right dimensions are used
        settings.update({'Width': self.width,
                         'Height': self.height})

        # Save settings
        self.settings = settings

        # Set all
        for key, value in self.settings.items():
            self.set_prop(key, value)

        # Set frame rate
        self._device.AcquisitionFrameRateEnable.SetValue(True)
        self._device.AcquisitionFrameRate.SetValue(self.frame_rate)

        # Start grabbing
        self._device.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        return True

    def next_snap(self) -> bool:
        return False

    def snap_image(self) -> bool:
        pass

    def next_image(self) -> bool:
        return vxipc.get_time() >= self.next_time_get_image

    def get_image(self) -> np.ndarray:

        # Grab what's available
        grab_result = self._device.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)

        # Check result
        frame = None
        if grab_result.GrabSucceeded():
            frame = grab_result.Array
        else:
            log.error(f'Unable to grab frame from {self} // {grab_result.ErrorCode}, {grab_result.ErrorDescription}')

        # Release resource
        grab_result.Release()

        # Set next image time
        self.next_time_get_image = vxipc.get_time() + 1. / self.frame_rate

        # Return frame
        return frame

    def _end_stream(self) -> bool:
        self._device.StopGrabbing()
        self._device.Close()

    def _close(self) -> bool:
        pass
