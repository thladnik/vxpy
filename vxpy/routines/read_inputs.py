"""
MappApp ./routines/io/display_calibration.py
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
from typing import Dict

from vxpy import config
from vxpy.definitions import *
from vxpy.api.attribute import ArrayAttribute, ArrayType, write_attribute
from vxpy.core import routine
from vxpy.core.ui import register_with_plotter


class ReadAll(routine.IoRoutine):

    def setup(self):

        # Read all pins
        self.pin_configs: Dict[str, Dict] = {}
        for pin_id, pin_config in config.IO_PINS.items():
            self.pin_configs[pin_id] = pin_config

        # Set up buffer attributes
        self.attributes: Dict[str, ArrayAttribute] = {}
        for pin_id, pin_config in self.pin_configs.items():
            if pin_config['type'] in ('do', 'ao'):
                continue
            if pin_config['type'] == 'di':
                attr = ArrayAttribute(pin_id, (1,), ArrayType.uint8)
            else:
                attr = ArrayAttribute(pin_id, (1,), ArrayType.float64)
            self.attributes[pin_id] = attr

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
