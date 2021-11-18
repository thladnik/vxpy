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
from __future__ import annotations
import importlib
import os
from typing import List, Union

from vxpy import Def
from vxpy import Logging

_available_protocols: List[str] = []


def get_available_protocol_paths(reload=False) -> List[str]:
    global _available_protocols

    if len(_available_protocols) > 0 and not reload:
        return _available_protocols

    _available_protocols = []
    basepath = Def.Path.Protocol
    filelist = os.listdir(basepath)
    for filename in filelist:

        # Load protocol module
        path = '.'.join([*basepath.split(os.sep), filename.replace('.py', '')])
        try:
            mod = importlib.import_module(path)
        except Exception as exc:
            Logging.write(Logging.WARNING, f'Unable to load protocol {path}')
            import traceback
            print(traceback.print_exc())
            continue

        # Load protocols in module
        for s in dir(mod):
            # Skip everything that's not a protocol class
            obj = getattr(mod, s)
            if not isinstance(obj, type) or not issubclass(obj, AbstractProtocol):
                continue
            # Skip all base classses
            if obj == StaticPhasicProtocol:
                continue

            fullpath = f'{path}.{s}'

            _available_protocols.append(fullpath)

    return _available_protocols


def get_protocol(path) -> Union[StaticPhasicProtocol, None]:
    if path not in get_available_protocol_paths():
        Logging.write(Logging.write, f'Cannot get protocol {path}')
        return

    # Return protocol class object
    parts = path.split('.')
    mod = importlib.import_module('.'.join(parts[:-1]))
    return getattr(mod, parts[-1])


class AbstractProtocol:
    pass


# class StaticProtocol(AbstractProtocol):
#


class StaticPhasicProtocol(AbstractProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    def __init__(self):
        self._phases = list()
        self._visuals = dict()

    def initialize_io(self):
        pass

    def initialize_visuals(self, canvas):
        for visual_name, visual_cls in self._visuals.items():
            self._visuals[visual_name] = visual_cls(canvas)

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

        return visual, parameters

