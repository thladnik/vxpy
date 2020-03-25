"""
MappApp ./Definition.py - Definitions required to run the program.
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


class EnvTypes:
    Dev        = 'dev'
    Production = 'production'

Env = EnvTypes.Production

class Path:
    Config   = 'configs'
    Log      = 'logs'
    Model    = 'models'
    Output   = 'output'
    Protocol = 'protocols'
    Sample   = 'samples'
    Shader   = 'shaders'
    Task     = 'tasks'

class Process:
    Camera     = 'Camera'
    Controller = 'Controller'
    Display    = 'Display'
    GUI        = 'Gui'
    IO         = 'IO'
    Logger     = 'Logger'
    Worker     = 'Worker'

class State:
    stopped          = 99
    starting         = 10
    idle             = 20
    busy             = 30
    recording        = 50
    recording_paused = 55

class Camera:
    name = 'camera'

    # Use camera
    use          = 'bool_use'

    # Camera configuration
    manufacturer = 'str_manufacturer'
    model        = 'str_model'
    format       = 'str_format'
    res_x        = 'int_resolution_x'
    res_y        = 'int_resolution_y'
    fps          = 'int_prop_fps'
    exposure     = 'float_prop_exposure'

    # Buffers
    buffers      = 'list_buffers'

class Display:
    name = 'display'

    # Use display
    use                    = 'bool_use'
    type                   = 'str_type'

    fps                    = 'int_fps'

    # Window settings
    window_screen_id       = 'int_window_screen_id'
    window_fullscreen      = 'bool_window_fullscreen'
    window_width           = 'int_window_width'
    window_height          = 'int_window_height'
    window_pos_x           = 'int_window_pos_x'
    window_pos_y           = 'int_window_pos_y'

    # Calibration settings
    pos_glob_x_pos         = 'float_pos_glob_x_pos'
    pos_glob_y_pos         = 'float_pos_glob_y_pos'
    pos_glob_radial_offset = 'float_pos_glob_radial_offset'

    view_elev_angle        = 'float_view_elev_angle'
    view_azim_angle        = 'float_view_azim_angle'
    view_distance          = 'float_view_origin_distance'
    view_scale             = 'float_view_scale'

class Gui:
    name = 'gui'

    use         = 'bool_use'

    # Addons
    addons      = 'list_addons'

class IO:
    name = 'io'

    use     = 'bool_use'

    buffers = 'list_buffers'

class Recording:
    name = 'recording'

    enabled         = 'bool_enabled'
    active          = 'bool_active'
    current_folder  = 'str_current_folder'

    # Active buffers
    buffers         = 'list_buffers'