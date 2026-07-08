"""Routine core module.

Routines are singleton worker objects that are attached to processes and
called once per event loop iteration.  They synchronize their public
attributes across process boundaries using multiprocessing manager proxies.
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


def get_routine(routine_path: str) -> Union[None, Type['Routine']]:
    """Get routine.
    
    Parameters
    ----------
    routine_path : str
        Dotted import path to a routine class.

    Returns
    -------
    Union[None, Type['Routine']]
        Imported routine class, or ``None`` if it cannot be resolved.
    """
    parts = routine_path.split('.')
    module = importlib.import_module('.'.join(parts[:-1]))
    routine_cls = getattr(module, parts[-1])

    if routine_cls is None:
        log.error(f'Routine {routine_path} not found.')

    return routine_cls


class Routine(ABC):
    """Routine class."""

    process_name: str = None
    _instance: 'Routine' = None
    callback_ops: List[Callable] = None

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Positional arguments accepted for subclass compatibility.
        **kwargs : Any
            Attribute overrides applied after synchronization setup.
        """
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
        """  new  .
        
        Parameters
        ----------
        *args : Any
            Positional arguments accepted for subclass compatibility.
        **kwargs : Any
            Keyword arguments accepted for subclass compatibility.
        """
        if cls._instance is None:
            cls._instance = super(Routine, cls).__new__(cls)

        return cls._instance

    def mp_manager(self):
        """Mp manager.
        """
        return vxipc.get_manager(self.__class__.__name__)

    def _synchronize_attributes(self):
        """ synchronize attributes.
        """
        for name in dir(self):
            if name.startswith('_'):
                continue

            val = self.__getattribute__(name)
            self._create_proxy_value(name, val)
            self._create_proxy_methods()

    def _create_proxy_value(self, name, val):
        """ create proxy value.
        
        Parameters
        ----------
        name : str
            Attribute name to synchronize through the multiprocessing manager.
        val : Any
            Attribute value used to infer the proxy type.
        """
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
        """ create proxy methods.
        """
        pass

    def __getattribute__(self, item):
        """  getattribute  .
        
        Parameters
        ----------
        item : str
            Attribute name being accessed.
        """

        attr = super().__getattribute__(item)
        if type(attr) == ValueProxy:
            return attr.value
        return attr

    def __setattr__(self, key, value):
        """  setattr  .
        
        Parameters
        ----------
        key : str
            Attribute name being set.
        value : Any
            New attribute value or proxy value content.
        """
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
        """Instance.
        """
        return cls._instance

    @classmethod
    def callback(cls, fun: Callable):
        """Callback.
        
        Parameters
        ----------
        fun : Callable
            Routine method exposed for process-level RPC callback registration.
        """
        if cls.callback_ops is None:
            cls.callback_ops = []

        if fun in cls.callback_ops:
            return

        cls.callback_ops.append(fun)

        return fun

    def require(self) -> bool:
        """Require.
        
        Returns
        -------
        bool
            ``True`` when this routine should be started.
        """
        return True

    def setup(self):
        """Setup.
        """
        pass

    def initialize(self):
        """Initialize.
        """
        pass

    @abstractmethod
    def main(self, *args, **kwargs):
        """Main.
        
        Parameters
        ----------
        *args : Any
            Per-iteration positional inputs provided by the owning process.
        **kwargs : Any
            Per-iteration keyword inputs provided by the owning process.
        """
        pass


class CameraRoutine(Routine, ABC):
    """CameraRoutine class."""

    process_name = PROCESS_CAMERA

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`Routine`.
        **kwargs : Any
            Forwarded to :class:`Routine`.
        """
        Routine.__init__(self, *args, **kwargs)


class DisplayRoutine(Routine, ABC):
    """DisplayRoutine class."""

    process_name = PROCESS_DISPLAY

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`Routine`.
        **kwargs : Any
            Forwarded to :class:`Routine`.
        """
        Routine.__init__(self, *args, **kwargs)


class IoRoutine(Routine, ABC):
    """IoRoutine class."""

    process_name = PROCESS_IO

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`Routine`.
        **kwargs : Any
            Forwarded to :class:`Routine`.
        """
        Routine.__init__(self, *args, **kwargs)

    @abstractmethod
    def main(self, **pins: Dict[str, vxserial.DaqPin]):
        """Main.
        
        Parameters
        ----------
        **pins : Dict[str, vxserial.DaqPin]
            Named DAQ pin objects available to the I/O routine iteration.
        """
        pass


class WorkerRoutine(Routine, ABC):
    """WorkerRoutine class."""

    process_name = PROCESS_WORKER

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`Routine`.
        **kwargs : Any
            Forwarded to :class:`Routine`.
        """
        Routine.__init__(self, *args, **kwargs)

