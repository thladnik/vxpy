"""
MappApp ./routines/Display.py - Custom processing routine implementations for the display process.
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

from Routine import AbstractRoutine, BufferDTypes


class ParameterRoutine(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        ### Set up shared variables
        self.buffer.parameters = (BufferDTypes.dictionary, )

    def _compute(self, data):
        ### Here data == visual

        self.buffer.parameters = data.params

    def _out(self):
        if self.buffer.parameters is None:
            return
        for k, p in self.buffer.parameters.items():
            yield k, p