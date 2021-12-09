"""
MappApp ./routines/io/__init__.py
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
import time
from typing import Any, Dict
import numpy as np

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.api.attribute import ArrayAttribute, ArrayType, write_attribute
from vxpy.core import routine, ipc
from vxpy.routines.camera import zf_tracking
from vxpy.api.ui import register_with_plotter


class ReadAll(routine.IoRoutine):

    def setup(self):

        # Read all pins
        self.pin_configs: Dict[str, Dict] = {}
        for did, pins in config.Io[definitions.IoCfg.pins].items():
            for pid, pconf in pins.items():
                pconf.update(dev=did)
                self.pin_configs[pid] = pconf

        # Set up buffer attributes
        self.attributes: Dict[str, ArrayAttribute] = {}
        for pid, pconf in self.pin_configs.items():
            if pconf['type'] in ('do', 'ao'):
                continue
            if pconf['type'] == 'di':
                attr = ArrayAttribute(pid, (1,), ArrayType.uint8)
            else:
                attr = ArrayAttribute(pid, (1,), ArrayType.float64)
            self.attributes[pid] = attr

    def initialize(self):
        for pid, attr in self.attributes.items():
            axis = self.pin_configs[pid]['type']
            # Plot in ui
            register_with_plotter(attr.name, axis=axis)
            # Add pin to be written to file
            attr.add_to_file()

    def main(self, **pins):
        for pid, pin in pins.items():
            if pid not in self.attributes:
                continue
            write_attribute(pid, pin.read())
