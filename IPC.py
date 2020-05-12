"""
MappApp ./IPC.py - Inter-process-communication placeholders and functions.
all stimulus implementations in ./stimulus/.
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

import ctypes
import logging
from multiprocessing import managers

import Def
import Logging

Manager : managers.SyncManager

########
# States

class State:
    localName  : str = None

    Camera     : int = None
    Controller : int = None
    Display    : int = None
    Gui        : int = None
    Io         : int = None
    Logger     : int = None
    Worker     : int = None

def setState(new_state):
    getattr(State, State.localName).value = new_state

def getState(process_name=None):
    if process_name is None:
        process_name = State.localName

    return getattr(State, process_name).value

def inState(state, process_name=None):
    if process_name is None:
        process_name = State.localName

    return getState(process_name) == state


########
# Pipes

Pipes : dict = dict()

def send(processName, signal, *args, **kwargs):
    """Convenience function for sending messages to other Processes.
    All messages have the format [Signal code, Argument list, Keyword argument dictionary]
    """
    Logging.write(logging.DEBUG, 'Send to process {} with signal {} > args: {} > kwargs: {}'
                  .format(processName, signal, args, kwargs))
    Pipes[processName][0].send([signal, args, kwargs])

def rpc(processName, function, *args, **kwargs):
    send(processName, Def.Signal.RPC, function. __qualname__, *args, **kwargs)


########
# Buffer objects

class Routines:
    Camera   = None
    Io       = None
    Display  = None

class Log:
    File     = None
    Queue    = None
    History  = None

########
# Controls

class Control:
    General   = None
    Recording = None
    Protocol  = None
