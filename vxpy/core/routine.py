"""
MappApp ./core/routine.py
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

from vxpy.definitions import *
import vxpy.core.attribute as vxattribute
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class Routine(ABC):
    """AbstractRoutine to be subclassed by all implementations of routines.
    """

    name: str = None

    def __init__(self, *args, **kwargs):

        self._triggers = dict()

        self._trigger_callbacks = dict()

        # List of methods open to rpc calls
        self.exposed = []

    @abstractmethod
    def setup(self):
        pass

    def initialize(self):
        """Called in forked modules"""
        pass

    @abstractmethod
    def main(self, *args, **kwargs):
        """Method is called on every iteration of the producer.

        Compute method is called on data updates (in the producer modules).
        Every buffer needs to implement this method and it's used to set all buffer attributes"""
        pass

    def add_trigger(self, trigger_name):
        self._triggers[trigger_name] = Trigger(self)

    def emit_trigger(self, trigger_name):
        if trigger_name in self._triggers:
            self._triggers[trigger_name].emit()
        else:
            log.warning(f'Cannot emit trigger "{trigger_name}". Does not exist.')

    def connect_to_trigger(self, trigger_name, routine, callback):
        self.exposed.append(callback)

        if routine.name not in self._trigger_callbacks:
            self._trigger_callbacks[routine.name] = dict()

        if routine.__qualname__ not in self._trigger_callbacks[routine.name]:
            self._trigger_callbacks[routine.name][routine.__qualname__] = dict()

        self._trigger_callbacks[routine.name][routine.__qualname__][trigger_name] = callback

    def _connect_triggers(self, _routines):
        for process_name, routines in self._trigger_callbacks.items():
            for routine_name, callbacks in routines.items():
                for trigger_name, callback in callbacks.items():
                    _routines[process_name][routine_name]._triggers[trigger_name].add_callback(self.name, callback)


class Trigger:
    _registered = []

    def __init__(self, routine):
        self.routine = routine

    def add_callback(self, process_name, callback):
        self._registered.append((process_name, callback))

    def emit(self):
        for process_name, callback in self._registered:
            vxipc.rpc(process_name, callback)


class CameraRoutine(Routine, ABC):

    name = PROCESS_CAMERA

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class DisplayRoutine(Routine, ABC):

    name = PROCESS_DISPLAY

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class IoRoutine(Routine, ABC):

    name = PROCESS_IO

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class WorkerRoutine(Routine, ABC):

    name = PROCESS_WORKER

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)

