"""Global definitions module
"""
import os
from enum import Enum

from vxpy import config


# Environment settings

# Max number of bytes reserved for array attribute buffers
#  This number determines the maximum memory size a shared attribute
#  may get allotted to it
DEFAULT_ARRAY_ATTRIBUTE_BUFFER_SIZE = 2 * 10**8  # Default ~200MB


# Default paths
PATH_PACKAGE = 'vxpy'
PATH_CONFIG = 'configurations'
PATH_GUI = 'extras'
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

# Process names
PROCESS_CAMERA = 'Camera'
PROCESS_CONTROLLER = 'Controller'
PROCESS_DISPLAY = 'Display'
PROCESS_GUI = 'Gui'
PROCESS_IO = 'Io'
PROCESS_WORKER = 'Worker'

# Setup commands
CMD_RUN = 'run'
CMD_PATCHDIR = 'patchdir'
CMD_SETUP = 'setup'
CMD_GETSAMPLES = 'getsamples'
CMD_CONFIGURE = 'configure'
CMD_CALIBRATE = 'calibrate'
CMD_MIGRATE = 'migrate'
CMD_HELP = 'help'
CMD_MOD_NOSAMPLES = '--nosamples'

# Session controls
CTRL_TIME_PRECISION = 'CTRL_TIME_PRECISION'
CTRL_MIN_SLEEP_TIME = 'CTRL_MIN_SLEEP_TIME'
CTRL_REC_ACTIVE = 'CTRL_REC_ACTIVE'
CTRL_REC_BASE_PATH = 'CTRL_REC_BASE_PATH'
CTRL_REC_FLDNAME = 'CTRL_REC_FLDNAME'
CTRL_REC_PRCL_GROUP_ID = 'CTRL_REC_PRCL_GROUP_ID'
CTRL_REC_PHASE_GROUP_ID = 'CTRL_REC_GROUP_ID'
CTRL_PRCL_ACTIVE = 'CTRL_PRCL_ACTIVE'
CTRL_PRCL_IMPORTPATH = 'CTRL_PRCL_IMPORTPATH'
CTRL_PRCL_TYPE = 'CTRL_PRCL_TYPE'
CTRL_PRCL_PHASE_ACTIVE = 'CTRL_PRCL_PHASE_ACTIVE'
CTRL_PRCL_PHASE_ID = 'CTRL_PRCL_PHASE_ID'
CTRL_PRCL_PHASE_INFO = 'CTRL_PRCL_PHASE_INFO'
CTRL_PRCL_PHASE_START_TIME = 'CTRL_PRCL_PHASE_START_TIME'
CTRL_PRCL_PHASE_END_TIME = 'CTRL_PRCL_PHASE_END_TIME'


class STATE(Enum):
    """Process states"""
    NA = 0
    STARTING = 1
    IDLE = 2
    REC_START_REQ = 10
    REC_START = 11
    REC_START_SUCCESS = 12
    REC_START_FAIL = 13
    REC_STOP_REQ = 17
    REC_STOP = 18
    REC_STOPPED = 19
    PRCL_START_REQ = 20
    PRCL_START = 21
    PRCL_STARTED = 22
    PRCL_IN_PROGRESS = 23
    PRCL_STOP_REQ = 27
    PRCL_STOP = 28
    PRCL_STOPPED = 29
    PRCL_STC_WAIT_FOR_PHASE = 30
    PRCL_STC_PHASE_READY = 31
    PRCL_IN_PHASE = 32
    SHUTDOWN = 90
    STOPPED = 99


class SIGNAL(Enum):
    """IPC signals"""
    rpc = 20
    query = 30
    post_event = 40
    shutdown = 99
    confirm_shutdown = 100


# Device types
class DeviceType(Enum):
    Camera = 1
    Io = 2


def get_sample_path():
    """Return path for example files, based on configuration"""
    if len(config.PATH_EXAMPLES) > 0:
        return config.PATH_EXAMPLES
    return PATH_SAMPLE
