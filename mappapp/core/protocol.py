"""
MappApp ./core/protocol.py
Copyright (C) 2020 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.l

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""


class AbstractProtocol:
    pass


class StaticProtocol(AbstractProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    def __init__(self, canvas):
        self.canvas = canvas
        self._phases = list()
        self._visuals = dict()

    def initialize(self):
        for visual_name, visual_cls in self._visuals.items():
            self._visuals[visual_name] = visual_cls(self.canvas)

    def add_visual(self, visual_cls: type):
        if visual_cls.__qualname__ not in self._visuals:
            self._visuals[visual_cls.__qualname__] = visual_cls

    def add_phase(self, visual_cls, duration, parameters):
        self.add_visual(visual_cls)
        self._phases.append((visual_cls.__qualname__, duration, parameters))

    def phase_count(self):
        return len(self._phases)

    def fetch_phase_duration(self, phase_id):
        visual_name, duration, parameters = self._phases[phase_id]
        return duration

    def fetch_phase_visual(self, phase_id):
        visual_name, duration, parameters = self._phases[phase_id]
        visual = self._visuals[visual_name]
        visual.update(**parameters)

        return visual

