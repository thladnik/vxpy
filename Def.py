"""
MappApp ./Def.py - Definitions required to run the program.
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

################################
# Environment settings

class EnvTypes:
    Dev        = 'dev'
    Production = 'production'

Env = EnvTypes.Production

Display_backend = 'qt5'

################################
# Subfolder definitions

class Path:
    Config   = 'configs'
    Libdll   = os.path.join('lib', 'dll')
    Log      = 'logs'
    Model    = 'models'
    Output   = 'output'
    Protocol = 'protocols'
    Routines = 'routines'
    Sample   = 'samples'
    Shader   = 'shaders'
    Task     = 'tasks'


################################
# Process names

class Process:
    Camera     = 'Camera'
    Controller = 'Controller'
    Display    = 'Display'
    GUI        = 'Gui'
    Io         = 'Io'
    Logger     = 'Logger'
    Worker     = 'Worker'


################################
# Process states

class State:
    NA               = 0
    SYNC             = 1
    STOPPED          = 99
    STARTING         = 10
    PREPARE_PROTOCOL = 30
    WAIT_FOR_PHASE   = 31
    PREPARE_PHASE    = 32
    READY            = 33
    PHASE_END        = 37
    PROTOCOL_ABORT   = 38
    PROTOCOL_END     = 39
    IDLE             = 20
    RUNNING          = 41
    STANDBY          = 42

MapStateToStr = {State.NA : 'N\A',
                 State.SYNC : 'Synchronizing',
                 State.STOPPED : 'Stopped',
                 State.STARTING : 'Starting',
                 State.PREPARE_PROTOCOL : 'Prepare protocol',
                 State.WAIT_FOR_PHASE : 'Wait for phase',
                 State.PREPARE_PHASE : 'Preparing phase',
                 State.READY : 'Ready',
                 State.PHASE_END : 'Phase ended',
                 State.PROTOCOL_ABORT : 'Abort protocol',
                 State.PROTOCOL_END : 'Protocol ended',
                 State.IDLE : 'Idle',
                 State.RUNNING : 'Running',
                 State.STANDBY : 'Standby',}

################################
# IPC signals

class Signal:
    UpdateProperty  = 10
    RPC             = 20
    Query           = 30
    Shutdown        = 99
    ConfirmShutdown = 100


################################
# Configuration key definitions

########
# Camera

class Cfg:
    name = None

    use = 'bool_use'

class CameraCfg(Cfg):
    name = Process.Camera.lower()

    # Camera configuration
    manufacturer = 'str_manufacturer'
    model        = 'str_model'
    format       = 'str_format'
    res_x        = 'int_resolution_x'
    res_y        = 'int_resolution_y'
    fps          = 'int_prop_fps'
    exposure     = 'float_prop_exposure'
    gain         = 'float_prop_gain'

    # Buffers
    routines      = 'json_routines'


########
# Display

class DisplayCfg(Cfg):
    name = Process.Display.lower()

    type                   = 'str_type'
    fps                    = 'int_fps'

    # Window settings
    window_screen_id       = 'int_window_screen_id'
    window_fullscreen      = 'bool_window_fullscreen'
    window_width           = 'int_window_width'
    window_height          = 'int_window_height'
    window_pos_x           = 'int_window_pos_x'
    window_pos_y           = 'int_window_pos_y'

    ## Calibration settings
    # General
    glob_x_pos         = 'float_glob_x_pos'
    glob_y_pos         = 'float_glob_y_pos'

    # Spherical
    sph_pos_glob_radial_offset = 'float_sph_pos_glob_radial_offset'

    sph_view_elev_angle        = 'float_sph_view_elev_angle'
    sph_view_azim_angle        = 'float_sph_view_azim_angle'
    sph_view_distance          = 'float_sph_view_origin_distance'
    sph_view_scale             = 'float_sph_view_scale'

    # Planar
    pla_xextent                = 'float_pla_xextent'
    pla_yextent                = 'float_pla_yextent'
    pla_small_side             = 'float_pla_small_side'

    routines                   = 'json_routines'

########
# GUI

class GuiCfg(Cfg):
    name = Process.GUI.lower()

    # Addons
    addons      = 'json_addons'


########
# IO

class IoCfg(Cfg):
    name = Process.Io.lower()

    device_type  = 'str_device_type'
    device_model = 'str_device_model'
    device_port  = 'str_device_comport'
    sample_rate  = 'int_sample_rate'
    pins         = 'json_pins'
    analog_pins  = 'json_analog_pins'

    routines = 'json_routines'


########
# Recording

class RecCfg(Cfg):
    name = 'recording'

    enabled         = 'bool_enabled'

    output_folder   = 'str_output_folder'

    # Active routines
    routines         = 'json_routines'


################################
# Controls

########
# General

class GenCtrl:
    min_sleep_time      = 'min_sleep_time'
    process_null_time   = 'process_null_time'
    process_syn_barrier = 'process_sync_barrier'

########
# Recording

class RecCtrl:
    active    = 'recording_active'
    folder    = 'current_folder'

################################
# Protocol

class ProtocolCtrl:
    name             = 'current_protocol'
    phase_id         = 'current_phase'
    phase_start      = 'phase_start_time'
    phase_stop       = 'phase_stop_time'

