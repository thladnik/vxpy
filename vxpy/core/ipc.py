"""Inter-modules-communication placeholders and functions.

This module holds module-level references to the local process instance, shared
control/state dictionaries, inter-process pipes, and convenience RPC helpers.
"""
from __future__ import annotations
import multiprocessing as mp
import time
from multiprocessing.managers import SyncManager, ValueProxy

import vxpy.core.logger as vxlogger
from vxpy.definitions import *

# Type hinting
from typing import TYPE_CHECKING, Union, Any

if TYPE_CHECKING:
    from typing import Callable, Dict, Tuple
    from vxpy.core.process import AbstractProcess


log = vxlogger.getLogger(__name__)

# Main manager for shared objects
Manager: SyncManager
_sub_managers: Dict[str, SyncManager] = {}


def get_manager(sub_name: str):
    """Get manager.
    
    Parameters
    ----------
    sub_name : str
        Description.
    """
    if sub_name not in _sub_managers:
        _sub_managers[sub_name] = mp.Manager()
    return _sub_managers[sub_name]


# Local modules reference
LocalProcess: AbstractProcess

# Controls
CONTROL: Dict[str, Any]

# States
STATE: Dict[str, Enum]

# Pipes
Pipes: Dict[str, Tuple[mp.connection.Connection, mp.connection.Connection]] = dict()


def init(local_instance, pipes, states, controls):
    """Init.
    
    Parameters
    ----------
    local_instance : Any
        Description.
    pipes : Any
        Description.
    states : Any
        Description.
    controls : Any
        Description.
    """
    global LocalProcess
    LocalProcess = local_instance

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{LocalProcess.name}]')

    if pipes is not None:
        globals()['Pipes'] = pipes

    # Set states
    if states is not None:
        globals()['STATE'] = states

    # Set controls
    if controls is not None:
        globals()['CONTROL'] = controls


def set_state(new_state: STATE):
    """Set state.
    
    Parameters
    ----------
    new_state : STATE
        Description.
    """
    log.debug(f'Set state from {get_state()} to {new_state}')
    STATE[LocalProcess.name] = new_state


def get_state(process_name: str = None):
    """Get state.
    
    Parameters
    ----------
    process_name : str
        Description.
    """
    if process_name is None:
        process_name = LocalProcess.name

    return STATE[process_name]


def in_state(state: STATE, process_name: str = None):
    """In state.
    
    Parameters
    ----------
    state : STATE
        Description.
    process_name : str
        Description.
    """
    if process_name is None:
        process_name = LocalProcess.name

    return get_state(process_name) == state


def send(process_name: str, signal: Enum, *args, _send_verbosely=True, **kwargs) -> None:
    """Send IPC message
    
    Parameters
    ----------
    process_name : str
        Description.
    signal : Enum
        Description.
    *args : Any
        Description.
    _send_verbosely : Any
        Description.
    **kwargs : Any
        Description.
    """
    if _send_verbosely:
        log.debug(f'Send to modules {process_name} with signal {signal} > args: {args} > kwargs: {kwargs}')

    kwargs.update(_send_verbosely=_send_verbosely)
    try:
        Pipes[process_name][0].send([signal, LocalProcess.name, args, kwargs])
    except Exception as _exc:
        log.warning(f'Failed to send message to process {process_name}')


def rpc(process_name: str, function: Union[Callable, str], *args, **kwargs) -> None:
    """Rpc.
    
    Parameters
    ----------
    process_name : str
        Description.
    function : Union[Callable, str]
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    if not (isinstance(function, str)):
        function = function.__qualname__
    send(process_name, SIGNAL.rpc, function, *args, **kwargs)


def get_recording_path():
    """Get recording path.
    """
    return os.path.join(CONTROL[CTRL_REC_BASE_PATH], CONTROL[CTRL_REC_FLDNAME])


_local_time = 0.0


def update_time():
    """Update time.
    """
    global _local_time
    _local_time = time.time() - LocalProcess.program_start_time


def get_time():
    """Get time.
    """
    global _local_time
    return _local_time


def camera_rpc(function, *args, **kwargs):
    """Camera RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_CAMERA, function, *args, **kwargs)


def controller_rpc(function, *args, **kwargs):
    """Controller RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_CONTROLLER, function, *args, **kwargs)


def display_rpc(function, *args, **kwargs):
    """Display RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_DISPLAY, function, *args, **kwargs)


def gui_rpc(function, *args, **kwargs):
    """Gui RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_GUI, function, *args, **kwargs)


def worker_rpc(function, *args, **kwargs):
    """Worker RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_WORKER, function, *args, **kwargs)


def io_rpc(function, *args, **kwargs):
    """Io RPC call
    
    Parameters
    ----------
    function : Any
        Description.
    *args : Any
        Description.
    **kwargs : Any
        Description.
    """
    rpc(PROCESS_IO, function, *args, **kwargs)
