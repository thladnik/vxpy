# from __future__ import annotations
#
# from abc import ABC, abstractmethod
# from typing import Any, Union, List
#
# from vxpy.core import logging
#
# log = logging.getLogger(__name__)
#
#
# def get_camera(device_config):
#     pass
#
#
# class AbstractCameraDevice(ABC):
#     def __init__(self):
#         self._type = None
#         self._exposure = None
#         self._format = None
#         self._gain = None
#
#     def __repr__(self):
#         return f'{self._type} {self._format}'
#
#     @abstractmethod
#     @property
#     def exposure(self) -> float:
#         return self._exposure
#
#     @exposure.setter
#     def exposure(self, value) -> None:
#         self._exposure = value
#
#     @abstractmethod
#     @property
#     def gain(self) -> float:
#         return self._gain
#
#     @gain.setter
#     def gain(self, value: float) -> None:
#         self._gain = value
#
#     @abstractmethod
#     @property
#     def format(self) -> CameraFormat:
#         return self._format
#
#     @format.setter
#     def format(self, value: Union[CameraFormat, str]) -> None:
#         if isinstance(value, str):
#             self._format = CameraFormat.from_str(fmt_str=value)
#             return
#         self._format = value
#
#     @abstractmethod
#     def get_format_list(self) -> List[CameraFormat]:
#         pass
#
#     @abstractmethod
#     def get_camera_list(self) -> List[AbstractCameraDevice]:
#         pass
#
#
# class CameraFormat:
#
#     def __init__(self, dtype: Any, width: int, height: int, rate: float):
#         self.dtype = dtype
#         self.width = width
#         self.height = height
#         self.rate = rate
#
#     @staticmethod
#     def from_str(fmt_str: str) -> CameraFormat:
#         substr = fmt_str.split('@')
#         r = float(substr[-1])
#         substr = substr[0].split('(')
#         f = substr[0]
#         w, h = [int(i) for i in substr[-1].strip(')').split('x')]
#
#         return CameraFormat(f, w, h, r)
#
#     def __repr__(self):
#         return f'{self.dtype}({self.width}x{self.height})@{self.rate}'