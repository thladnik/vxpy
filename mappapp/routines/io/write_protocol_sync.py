"""
MappApp ./routines/io/write_test_attributes.py
Copyright (C) 2021 Tim Hladnik

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
import numpy as np

from mappapp.api import get_time
from mappapp.api.io import set_digital_output
from mappapp.api.routine import IoRoutine
from mappapp.api.attribute import ArrayAttribute, ArrayType
from mappapp.api.ui import register_with_plotter
from mappapp.core import ipc


class WriteProtocolSync(IoRoutine):

    def __init__(self):
        super(WriteProtocolSync, self).__init__()

    def setup(self):
        self.protocol_active = ArrayAttribute('protocol_active', (1, ), ArrayType.bool)
        self.phase_active = ArrayAttribute('phase_active', (1, ), ArrayType.bool)

    def initialize(self):
        register_with_plotter('protocol_active', axis=WriteProtocolSync.__name__)
        register_with_plotter('phase_active', axis=WriteProtocolSync.__name__)
        set_digital_output('protocol_active', 'protocol_active')
        set_digital_output('phase_active', 'phase_active')

    def main(self, *args, **kwargs):
        self.phase_active.write(ipc.Process.phase_is_active)
