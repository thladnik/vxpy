import time
from typing import List

import numpy as np
from pypylon import pylon

from vxpy.core import camera_device, logger
from vxpy.core.camera_device import AbstractCameraDevice, CameraFormat

log = logger.getLogger(__name__)


class CameraDevice(camera_device.AbstractCameraDevice):

    _exposure_unit = camera_device.ExposureUnit.microseconds

    def get_format_list(self) -> List[CameraFormat]:
        pass

    def _framerate_list(self, _format: CameraFormat) -> List[float]:
        pass

    @classmethod
    def get_camera_list(cls) -> List[AbstractCameraDevice]:

        camera_list = []
        for cam_info in pylon.TlFactory.GetInstance().EnumerateDevices():
            cam = CameraDevice(cam_info.GetSerialNumber(), cam_info.GetModelName())
            camera_list.append(cam)

        return camera_list

    def _start_stream(self) -> bool:
        camera = None
        for cam_info in pylon.TlFactory.GetInstance().EnumerateDevices():
            serial = cam_info.GetSerialNumber()
            model = cam_info.GetModelName()

            if str(serial) == str(self.serial) and model == self.model:
                camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(cam_info))
                break

        # Check if camera was found
        if camera is None:
            log.error(f'Unable to connect to {self}. Device not found')
            return False

        # Open camera device
        self._device = camera
        self._device.Open()

        # Set acquisition parameters
        max_x = 3840
        max_y = 2160
        self._device.Width.SetValue(self.format.width)
        self._device.Height.SetValue(self.format.height)
        # self._device.Width.SetValue(max_x)
        # self._device.Height.SetValue(max_y)
        self._device.BinningHorizontalMode.SetValue('Average')
        self._device.BinningHorizontal.SetValue(max_x // self.format.width)
        self._device.BinningVerticalMode.SetValue('Average')
        self._device.BinningVertical.SetValue(max_y // self.format.height)
        self._device.GainAuto.SetValue('Off')
        self._device.Gain.SetValue(self.gain)
        self._device.ExposureAuto.SetValue('Off')
        self._device.ExposureTime.SetValue(self.exposure)
        self._device.AcquisitionFrameRateEnable.SetValue(True)
        self._device.AcquisitionFrameRate.SetValue(self.framerate)

        # Start grabbing
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        return True

    def snap_image(self) -> bool:
        pass

    def get_image(self) -> np.ndarray:
        t = time.perf_counter()
        grab_result = self._device.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        # print(self._device.ExposureTime.GetValue())
        # print(f'{time.perf_counter()-t:.3f}')
        # print(self._device.ExposureTime.GetValue())
        # print(self._device.Gain.GetValue())

        frame = None
        if grab_result.GrabSucceeded():
            frame = grab_result.Array
        else:
            log.error(f'Unable to grab frame from {self} // {grab_result.ErrorCode}, {grab_result.ErrorDescription}')
        grab_result.Release()

        return frame

    def end_stream(self) -> bool:
        self._device.StopGrabbing()
        self._device.Close()
