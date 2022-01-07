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
PATH_CONFIG = 'configs'
PATH_GUI = 'gui'
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
    shutdown = 99
    confirm_shutdown = 100


# Device types
class DeviceType(Enum):
    Camera = 1
    Io = 2


class Cfg:
    name = None

    use = 'bool_use'


# Camera
class CameraCfg(Cfg):
    name = PROCESS_CAMERA.lower()

    # Camera configuration
    device_id = 'json_device_id'
    manufacturer = 'json_manufacturer'
    model = 'json_model'
    format = 'json_format'
    res_x = 'json_resolution_x'
    res_y = 'json_resolution_y'
    fps = 'int_fps'
    exposure = 'json_exposure'
    gain = 'json_gain'
    devices = 'json_devices'

    # Buffers
    routines = 'json_routines'


# Display
class DisplayCfg(Cfg):
    name = PROCESS_DISPLAY.lower()

    # Configuration settings
    type = 'str_type'
    fps = 'int_fps'
    window_backend = 'str_window_backend'
    gl_version_major = 'int_gl_version_major'
    gl_version_minor = 'int_gl_version_minor'
    gl_profile = 'str_gl_profile'
    routines = 'json_routines'

    # Calibration settings

    # Window settings
    window_screen_id = 'int_window_screen_id'
    window_fullscreen = 'bool_window_fullscreen'
    window_width = 'int_window_width'
    window_height = 'int_window_height'
    window_pos_x = 'int_window_pos_x'
    window_pos_y = 'int_window_pos_y'

    # Calibration settings
    # General
    glob_x_pos = 'float_glob_x_pos'
    glob_y_pos = 'float_glob_y_pos'

    # Spherical
    sph_view_azim_orient = 'float_sph_view_azim_orient'
    sph_view_elev_angle = 'json_sph_view_elev_angle'
    sph_view_azim_angle = 'json_sph_view_azim_angle'
    sph_view_distance = 'json_sph_view_origin_distance'
    sph_view_fov = 'json_sph_view_fov'
    sph_view_scale = 'json_sph_view_scale'
    sph_pos_glob_radial_offset = 'json_sph_pos_glob_radial_offset'
    sph_pos_glob_lateral_offset = 'json_sph_pos_glob_lateral_offset'
    sph_lat_lum_offset = 'json_sph_lat_lum_offset'
    sph_lat_lum_gradient = 'json_sph_lat_lum_gradient'

    # Planar
    pla_xextent = 'float_pla_xextent'
    pla_yextent = 'float_pla_yextent'
    pla_small_side = 'float_pla_small_side'


# GUI
class GuiCfg(Cfg):
    name = PROCESS_GUI.lower()

    # Addons
    addons = 'json_addons'


# IO
class IoCfg(Cfg):
    name = PROCESS_IO.lower()

    device = 'json_device'
    max_sr = 'int_max_sr'
    pins = 'json_pins'

    routines = 'json_routines'


# Worker
class WorkerCfg(Cfg):
    name = PROCESS_WORKER.lower()

    routines = 'json_routines'


# Recording
class RecCfg(Cfg):
    name = 'recording'

    enabled = 'bool_enabled'

    output_folder = 'str_output_folder'

    # Active routines
    attributes = 'json_attributes'
    routines = 'json_routines'


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
