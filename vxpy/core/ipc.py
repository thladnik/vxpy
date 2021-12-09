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
from enum import Enum
from multiprocessing.managers import SyncManager

from vxpy.Def import *
from vxpy import Def
from vxpy import Logging

# Type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, Dict, Tuple
    from vxpy.core.process import AbstractProcess, ProcessProxy

# Manager for shared objects
Manager: SyncManager

# Local modules reference
Process: AbstractProcess

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


# Proxies
Controller: ProcessProxy
Camera: ProcessProxy
Display: ProcessProxy
Gui: ProcessProxy
Io: ProcessProxy
Worker: ProcessProxy


def set_state(new_state: Enum):
    """Set state of local modules to new_state"""
    getattr(State, Process.name).value = new_state


def get_state(process_name: str = None):
    """Get state of modules.

    By default, if process_name is None, the local modules's name is used
    """
    if process_name is None:
        process_name = Process.name

    return getattr(State, process_name).value


def in_state(state: Enum, process_name: str = None):
    """Check if modules is in the given state.

    By default, if process_name is None, the local modules's name is used
    """
    if process_name is None:
        process_name = Process.name

    return get_state(process_name) == state


# Pipes
# TODO: pipes have *limited buffer size*. This means if processes send
#  messages more quickly than the consumer can sort them out, this will crash
#  the producer modules (can happen e.g. for very frequent event triggered signals)
#  ----
#  -> One solution may be an arbitrary limit on how often a pipe can be used to send
#  messages in a given time window. Although this would disregard the size of messages:
#  Another proposal which checks the buffer size against a maxsize:
#  https://stackoverflow.com/questions/45318798/how-to-detect-multiprocessing-pipe-is-full
#  Question: Overhead?

Pipes: Dict[str, Tuple[mp.connection.Connection, mp.connection.Connection]] = dict()


def set_process(instance):
    global Process
    Process = instance


def build_pipes(pipes):
    if pipes is None:
        return

    global Pipes
    Pipes.update(pipes)


def send(process_name: str, signal: int, *args, _send_verbosely=True, **kwargs) -> None:
    """Send a message to another modules via pipe.

    Convenience function for sending messages to modules with process_name.
    All messages have the format [Signal code, Argument list, Keyword argument dictionary]

    @param process_name:
    @param signal:
    @param args:
    @param kwargs:

    """
    if _send_verbosely:
        Logging.write(Logging.DEBUG,
                      f'Send to modules {process_name} with signal {signal} > args: {args} > kwargs: {kwargs}')

    kwargs.update(_send_verbosely=_send_verbosely)

    Pipes[process_name][0].send([signal, args, kwargs])


def rpc(process_name: str, function: Callable, *args, **kwargs) -> None:
    """Send a remote procedure call of given function to another modules.

    @param process_name:
    @param function:
    @param args:
    @param kwargs:
    """
    if not (isinstance(function, str)):
        function = function.__qualname__
    send(process_name, Def.Signal.rpc, function, *args, **kwargs)


class Log:
    File = None
    Queue = None
    History = None


########
# Controls

class Control:
    General = None
    Recording = None
    Protocol = None
