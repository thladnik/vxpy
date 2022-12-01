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
from typing import List

import numpy as np
from pypylon import pylon

import vxpy.core.devices.camera as vxcamera
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class BaslerCamera(vxcamera.CameraDevice):

    def __init__(self, *args, **kwargs):
        vxcamera.CameraDevice.__init__(self, *args, **kwargs)

    @property
    def exposure(self) -> float:
        return self.properties['exposure']

    @property
    def gain(self) -> float:
        return self.properties['gain']

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

    def _start_stream(self) -> bool:

        frame_rate = self.properties['frame_rate']
        # Set acquisition parameters

        max_x, max_y = int(self._device.SensorWidth.GetValue()), int(self._device.SensorHeight.GetValue())

        # print(self._device.Width.GetInc(), self._device.Height.GetInc())
        self._device.Width.SetValue(self.width)
        self._device.Height.SetValue(self.height)
        self._device.BinningHorizontalMode.SetValue('Average')
        self._device.BinningHorizontal.SetValue(max_x // self.width)
        self._device.BinningVerticalMode.SetValue('Average')
        self._device.BinningVertical.SetValue(max_y // self.height)
        self._device.GainAuto.SetValue('Off')
        self._device.Gain.SetValue(self.gain)
        self._device.ExposureAuto.SetValue('Off')
        self._device.ExposureTime.SetValue(self.exposure)
        self._device.AcquisitionFrameRateEnable.SetValue(True)
        self._device.AcquisitionFrameRate.SetValue(frame_rate)

        # Start grabbing
        self._device.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        return True

    def snap_image(self) -> bool:
        pass

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

        # Return frame
        return frame

    def _end_stream(self) -> bool:
        self._device.StopGrabbing()
        self._device.Close()

    def _close(self) -> bool:
        pass
