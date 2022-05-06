"""
MappApp ./definitions.py
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
import os
from enum import Enum
from typing import Dict


################################
# Environment settings

# Number of bytes reserved for array attribute buffers
DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE = 2 * 10**8  # Default ~200MB


class EnvTypes(Enum):
    PRODUCTION = 1
    DEBUG = 2
    DEV = 3


Env = EnvTypes.DEV

PATH_PACKAGE = 'vxpy'
PATH_CONFIG = 'configurations'
PATH_GUI = 'addons'
PATH_DLL = os.path.join('lib', 'dll')
PATH_LOG = 'logs'
PATH_VISUALS = 'visuals'
PATH_PROTOCOL = 'protocols'
PATH_RECORDING_OUTPUT = 'recordings'
PATH_TEMP = 'temp'
PATH_SAMPLE = 'samples'
PATH_DEVICE = 'devices'
PATH_ROUTINES = 'routines'
PATH_SHADERS = 'shaders'
PATH_TASKS = 'tasks'

PROCESS_CAMERA = 'Camera'
PROCESS_CONTROLLER = 'Controller'
PROCESS_DISPLAY = 'Display'
PROCESS_GUI = 'Gui'
PROCESS_IO = 'Io'
PROCESS_WORKER = 'Worker'

CMD_PATCHDIR = 'patchdir'
CMD_SETUP = 'setup'
CMD_GETSAMPLES = 'getsamples'
CMD_CONFIGURE = 'configure'
CMD_CALIBRATE = 'calibrate'
CMD_MIGRATE = 'migrate'
CMD_HELP = 'help'

CMD_MOD_NOSAMPLES = '--nosamples'


# Process states
class State(Enum):
    NA = 0
    SYNC = 1
    STOPPED = 99
    STARTING = 10
    PREPARE_PROTOCOL = 30
    WAIT_FOR_PHASE = 31
    PREPARE_PHASE = 32
    READY = 33
    PHASE_END = 37
    PROTOCOL_ABORT = 38
    PROTOCOL_END = 39
    IDLE = 20
    RUNNING = 41
    STANDBY = 42


# IPC signals
class Signal(Enum):
    update_property = 10
    rpc = 20
    query = 30
    post_event = 40
    shutdown = 99
    confirm_shutdown = 100


# Device types
class DeviceType(Enum):
    Camera = 1
    Io = 2


# Controls

# General

class GenCtrl:
    min_sleep_time = 'min_sleep_time'
    # process_null_time = 'process_null_time'
    process_syn_barrier = 'process_sync_barrier'


# Recording

class RecCtrl:
    enabled = 'recording_enable'
    active = 'recording_active'
    folder = 'current_folder'
    use_compression = 'use_compression'
    compression_method = 'compression_method'
    compression_opts = 'compression_opts'
    record_group_counter = 'record_group_counter'


# Protocol

class ProtocolCtrl:
    name = 'current_protocol'
    phase_id = 'current_phase'
    phase_start = 'phase_start_time'
    phase_stop = 'phase_stop_time'
