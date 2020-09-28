"""
MappApp ./routines/DefaultIoRoutines.py - Custom processing routine implementations.
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

import Config
import Def

from Routine import AbstractRoutine

class ReadRoutine(AbstractRoutine):

    pins = ['test02_digin:6:i','test01_digin:9:i']

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        for digitPin in self.pins:
            name, num, ptype = digitPin.split(':')
            setattr(self.buffer, name, (name, ))

    def _compute(self, data):
        for pin_descr in self.pins:
            pin_name, pin_num, pin_type = pin_descr.split(':')
            setattr(self.buffer, pin_name, data[pin_name])

    def _out(self):
        ### Yield pin data
        for pin_descr in self.pins:
            pin_name, pin_num, pin_type = pin_descr.split(':')
            yield pin_name, getattr(self.buffer, pin_name)

class ReadRoutineSub(ReadRoutine):

    pins = ['test01_anin:3:i']

    def __init__(self, *args, **kwargs):
        ReadRoutine.__init__(self, *args, **kwargs)

    def _compute(self, data):
        ReadRoutine._compute(self, data)

    def _out(self):
        ### Yield data from pin directly
        yield from iter(ReadRoutine._out(self))

        yield 'extra', 1

