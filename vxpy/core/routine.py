"""Routine core module
"""
from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from multiprocessing.managers import DictProxy
from typing import Callable, List, Type, Union, Dict, Any

from deprecation import deprecated

from vxpy.definitions import *
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


def get_routine(routine_path: str) -> Union[None, Type[Routine]]:
    parts = routine_path.split('.')
    module = importlib.import_module('.'.join(parts[:-1]))
    routine_cls = getattr(module, parts[-1])

    if routine_cls is None:
        log.error(f'Routine {routine_path} not found.')

    return routine_cls


class Routine(ABC):
    """Abstract routine base class - to be inherited by all routines.
    """

    process_name: str = None
    _instance: Routine = None
    callback_ops: List[Callable] = None
    default_parameters: Dict[str, Any] = None
    parameters: DictProxy[str, Any] = None

    def __init__(self, *args, **kwargs):

        # Create shared dictionary for setting routine parameters
        self.parameters = vxipc.Manager.dict()

        # Set defaults
        if self.default_parameters is not None:
            self.parameters.update(self.default_parameters)

        # Update parameters based on configuration
        for key, val in kwargs.items():
            self.parameters[key] = val

        # List of methods open to rpc calls
        if self.callback_ops is None:
            self.callback_ops = []

    def __new__(cls, *args, **kwargs):
        """Ensure each routine can only be used as Singleton"""
        if cls._instance is None:
            cls._instance = super(Routine, cls).__new__(cls)

        return cls._instance

    @classmethod
    def instance(cls):
        return cls._instance

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

