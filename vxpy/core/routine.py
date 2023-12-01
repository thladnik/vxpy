"""Routine core module
"""
from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from multiprocessing.managers import ValueProxy
from typing import Callable, List, Type, Union, Dict, Any

from vxpy.definitions import *
import vxpy.core.devices.serial as vxserial
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

    def __init__(self, *args, **kwargs):
        self.mp_manager()

        # Create interprocess syncs
        self._synchronize_attributes()

        for key, value in kwargs.items():
            log.info(f'Set {key} to {value} in routine {self.__class__.__name__}')
            setattr(self, key, value)

        # List of methods open to rpc calls
        if self.callback_ops is None:
            self.callback_ops = []

    def __new__(cls, *args, **kwargs):
        """Ensure each routine can only be used as Singleton
        """
        if cls._instance is None:
            cls._instance = super(Routine, cls).__new__(cls)

        return cls._instance

    def mp_manager(self):
        """Get multiprocessing manager for this routine
        ---
        NOTE to future self:
            This is a Windows thing. You may not keep a reference to
            a SyncManager when pickling an object during process *spawn*ing.
            Linux' *clone* doesn't have an issue here.
            -> Just leave the sync managers in ipc module.
        """
        return vxipc.get_manager(self.__class__.__name__)

    def _synchronize_attributes(self):
        """Iterate through all public class attributes and create remote proxies
        """
        for name in dir(self):
            if name.startswith('_'):
                continue

            val = self.__getattribute__(name)
            self._create_proxy_value(name, val)
            self._create_proxy_methods()

    def _create_proxy_value(self, name, val):
        _type = type(val)
        if _type in [int, str, float, bool]:
            log.debug(f'Create ValueProxy for {self.__class__.__name__}.{name} ({_type})')
            self.__setattr__(name, self.mp_manager().Value(_type, val))
            return True
        elif _type == dict:
            log.debug(f'Create DictProxy for {self.__class__.__name__}.{name}')
            self.__setattr__(name, self.mp_manager().dict(val))
            return True
        elif _type == list:
            log.debug(f'Create ListProxy for {self.__class__.__name__}.{name}')
            self.__setattr__(name, self.mp_manager().list(val))
            return True
        return False

    def _create_proxy_methods(self):
        # TODO: implement remote method calls (including return values)
        pass

    def __getattribute__(self, item):

        attr = super().__getattribute__(item)
        if type(attr) == ValueProxy:
            return attr.value
        return attr

    def __setattr__(self, key, value):
        try:
            attr = super().__getattribute__(key)

            if type(attr) == ValueProxy:
                attr.value = value
            else:
                super().__setattr__(key, value)
        except:
            if not self._create_proxy_value(key, value):
                super().__setattr__(key, value)

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

    @abstractmethod
    def main(self, **pins: Dict[str, vxserial.DaqPin]):
        pass


class WorkerRoutine(Routine, ABC):

    process_name = PROCESS_WORKER

    def __init__(self, *args, **kwargs):
        Routine.__init__(self, *args, **kwargs)

