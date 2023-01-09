"""
MappApp ./core/ipc.py - Inter-modules-communication placeholders and functions.
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
import multiprocessing as mp
import time
from multiprocessing.managers import SyncManager

import vxpy.core.logger as vxlogger
from vxpy.definitions import *

# Type hinting
from typing import TYPE_CHECKING, Union, Any

if TYPE_CHECKING:
    from typing import Callable, Dict, Tuple
    from vxpy.core.process import AbstractProcess


log = vxlogger.getLogger(__name__)

# Manager for shared objects
Manager: SyncManager

# Local modules reference
LocalProcess: AbstractProcess

# Callback routing


########
# States

class State:
    Camera: mp.Value = None
    Controller: mp.Value = None
    Display: mp.Value = None
    Gui: mp.Value = None
    Io: mp.Value = None
    Logger: mp.Value = None
    Worker: mp.Value = None


class ProcessProxy:
    def __init__(self, name):
        self.name = name

    @property
    def state(self):
        return get_state(self.name)

    def in_state(self, state):
        return in_state(state, self.name)

    def rpc(self, function: Callable, *args, **kwargs) -> None:
        rpc(self.name, function, *args, **kwargs)


# Proxies
Controller: ProcessProxy = ProcessProxy(PROCESS_CONTROLLER)
Camera: ProcessProxy = ProcessProxy(PROCESS_CAMERA)
Display: ProcessProxy = ProcessProxy(PROCESS_DISPLAY)
Gui: ProcessProxy = ProcessProxy(PROCESS_GUI)
Io: ProcessProxy = ProcessProxy(PROCESS_IO)
Worker: ProcessProxy = ProcessProxy(PROCESS_WORKER)


def set_state(new_state: STATE):
    """Set state of local modules to new_state"""
    log.debug(f'Set state from {get_state()} to {new_state}')
    getattr(State, LocalProcess.name).value = new_state


def get_state(process_name: str = None):
    """Get state of modules.

    By default, if process_name is None, the local modules's name is used
    """
    if process_name is None:
        process_name = LocalProcess.name

    return getattr(State, process_name).value


def in_state(state: STATE, process_name: str = None):
    """Check if modules is in the given state.

    By default, if process_name is None, the local modules's name is used
    """
    if process_name is None:
        process_name = LocalProcess.name

    return get_state(process_name) == state


Pipes: Dict[str, Tuple[mp.connection.Connection, mp.connection.Connection]] = dict()


def init(local_instance, pipes, proxies, states, control, controls):
    global LocalProcess
    LocalProcess = local_instance

    # Reset logger to include process_name
    global log
    log = vxlogger.getLogger(f'{__name__}[{LocalProcess.name}]')

    if pipes is not None:
        global Pipes
        Pipes.update(pipes)

    if proxies is not None:
        for pkey, proxy in proxies.items():
            locals()[pkey] = proxy

    # Set states
    if states is not None:
        for skey, state in states.items():
            locals()[skey] = state

    # Set controls
    # New
    if control is not None:
        globals()['CONTROL'] = control

    # OLD CONTROLS
    if controls is not None:
        for ckey, ctrl in controls.items():
            setattr(Control, ckey, ctrl)
    # OLD CONTROLS


def send(process_name: str, signal: Enum, *args, _send_verbosely=True, **kwargs) -> None:
    """Send a message to another modules via pipe.

    Convenience function for sending messages to modules with process_name.
    All messages have the format [Signal code, Argument list, Keyword argument dictionary]

    @param process_name:
    @param signal:
    @param args:
    @param kwargs:

    """
    if _send_verbosely:
        log.debug(f'Send to modules {process_name} with signal {signal} > args: {args} > kwargs: {kwargs}')

    kwargs.update(_send_verbosely=_send_verbosely)

    Pipes[process_name][0].send([signal, LocalProcess.name, args, kwargs])


def rpc(process_name: str, function: Callable, *args, **kwargs) -> None:
    """Send a remote procedure call of given function to another modules.

    @param process_name:
    @param function:
    @param args:
    @param kwargs:
    """
    if not (isinstance(function, str)):
        function = function.__qualname__
    send(process_name, Signal.rpc, function, *args, **kwargs)


class Log:
    File = None
    Queue = None
    History = None


########
# Controls

CONTROL: Dict[str, Any]


def get_recording_path():
    return os.path.join(CONTROL[CTRL_REC_BASE_PATH], CONTROL[CTRL_REC_FLDNAME])


class Control:
    General = None
    Recording = None
    Protocol = None


_local_time = 0.0


def update_time():
    global _local_time
    _local_time = time.time() - LocalProcess.program_start_time


def get_time():
    global _local_time
    return _local_time


def camera_rpc(function, *args, **kwargs):
    rpc(PROCESS_CAMERA, function, *args, **kwargs)


def controller_rpc(function, *args, **kwargs):
    rpc(PROCESS_CONTROLLER, function, *args, **kwargs)


def display_rpc(function, *args, **kwargs):
    rpc(PROCESS_DISPLAY, function, *args, **kwargs)


def gui_rpc(function, *args, **kwargs):
    rpc(PROCESS_GUI, function, *args, **kwargs)


def worker_rpc(function, *args, **kwargs):
    rpc(PROCESS_WORKER, function, *args, **kwargs)


def io_rpc(function, *args, **kwargs):
    rpc(PROCESS_IO, function, *args, **kwargs)
