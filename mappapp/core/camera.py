"""
MappApp ./core/camera.py
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
from abc import ABC, abstractmethod
from typing import Dict, List, Union
from dataclasses import dataclass

_use_apis = []
_devices = {}


def get_devices(reload=False):
    global _devices

    if bool(_devices) and not reload:
        return _devices

    _devices = {}
    for api in _use_apis:
        for serial, device in api.get_connected_devices().items():
            device._api = api
            _devices[serial] = device

    return _devices


def open_device(config):
    global _use_apis
    _use_apis_str = [a.__name__ for a in _use_apis]
    print(_use_apis)
    if config['api'] not in _use_apis_str:
        raise f'Camera API {config["api"]} not available'

    api = _use_apis[_use_apis_str.index(config['api'])]

    camera = api.CameraDevice(config['serial'])

    if camera.open():
        camera.set_api(api)
        camera.set_format(Format.from_str(config['format']))
        camera.set_id(config['id'])
        camera.set_exposure(config['exposure'])
        camera.set_gain(config['gain'])

        return camera
    else:
        raise Exception(f'Camera {config["serial"]} could not be opened')


class AbstractCameraDevice(ABC):

    def __init__(self, serial, **info):
        self.serial = serial
        self.info: Dict = info
        self._avail_formats: List[Format] = []
        self._fmt: Format = None
        self._api = None
        self.id = None

        self.exposure = None
        self.gain = None

    def __repr__(self):
        return f'CameraDevice {self._api.__name__}.{self.id} (SN{self.serial}) ({self.display_info()})'

    def set_id(self, id):
        self.id = id

    def set_format(self, fmt: Union[str, Format]) -> None:
        if isinstance(fmt, str):
            fmt = Format.from_str(fmt)
        if fmt in self.get_formats():
            self._fmt = fmt
        else:
            raise Exception(f'Trying to set unsupported format {fmt} on camera device {self}')

    def display_info(self):
        return ''

    def set_api(self, api):
        self._api = api

    def get_config(self):
        return {'api': self._api,
                'serial': self.serial,
                'id': self.id,
                'format': str(self._fmt),
                'exposure': self.exposure,
                'gain': self.gain}

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def start_stream(self):
        pass

    @abstractmethod
    def snap_image(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_image(self):
        pass

    @abstractmethod
    def get_formats(self):
        pass

    @abstractmethod
    def set_exposure(self, e):
        pass

    @abstractmethod
    def set_gain(self, g):
        pass


@dataclass
class Format(ABC):

    def __init__(self, name: str, width: int, height: int, rate: int):
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.rate = int(rate)

    @staticmethod
    def from_str(fmt_str: str) -> Format:
        substr = fmt_str.split('@')
        r = substr[-1]
        substr = substr[0].split('(')
        f = substr[0]
        w, h = substr[-1].strip(')').split('x')
        # w, h = [int(s) for s in substr]

        return Format(f, w, h, r)

    def __repr__(self):
        return f'{self.name}({self.width}x{self.height})@{self.rate}'
