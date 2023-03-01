"""
vxpy ./core/routine.py
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
from typing import Callable, List

from deprecation import deprecated

from vxpy.definitions import *
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class Routine(ABC):
    """Abstract routine base class - to be inherited by all routines.
    """

    process_name: str = None
    instance: Routine = None
    callback_ops: List[Callable] = None

    def __init__(self, *args, **kwargs):
        self._triggers = dict()

        self._trigger_callbacks = dict()

        # List of methods open to rpc calls
        if self.callback_ops is None:
            self.callback_ops = []

    def __new__(cls, *args, **kwargs):
        """Ensure each routine can only be used as Singleton"""
        if cls.instance is None:
            cls.instance = super(Routine, cls).__new__(cls)

        return cls.instance


    @classmethod
    def callback(cls, fun: Callable):
        if cls.callback_ops is None:
            cls.callback_ops = []

        if fun in cls.callback_ops:
            return

        cls.callback_ops.append(fun)

        return fun

    def require(self) -> bool:
        return True

    @deprecated(details='Use require method instead', deprecated_in='0.1.0', removed_in='0.2.0')
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


class CameraRoutine(Routine, ABC):

    process_name = PROCESS_CAMERA

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class DisplayRoutine(Routine, ABC):

    process_name = PROCESS_DISPLAY

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class IoRoutine(Routine, ABC):

    process_name = PROCESS_IO

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)


class WorkerRoutine(Routine, ABC):

    process_name = PROCESS_WORKER

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)

