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
    Protocol = 'protocols'
    Sample   = 'samples'
    Shader   = 'shaders'

class Process:
    Camera     = 'camera'
    Controller = 'controller'
    Display    = 'display'
    GUI        = 'gui'
    Logger     = 'logger'

class DisplayConfig:
    name = 'display'

    bool_use                     = 'bool_use'

    # Window settings
    int_window_screen_id         = 'int_window_screen_id'
    bool_window_fullscreen       = 'bool_window_fullscreen'
    int_window_width             = 'int_window_width'
    int_window_height            = 'int_window_height'
    int_window_pos_x             = 'int_window_pos_x'
    int_window_pos_y             = 'int_window_pos_y'

    # Calibration settings
    float_pos_glob_x_pos         = 'float_pos_glob_x_pos'
    float_pos_glob_y_pos         = 'float_pos_glob_y_pos'
    float_pos_glob_radial_offset = 'float_pos_glob_radial_offset'

    float_view_elev_angle        = 'float_view_elev_angle'
    float_view_axis_offset       = 'float_view_axis_offset'
    float_view_origin_distance   = 'float_view_origin_distance'
    float_view_fov               = 'float_view_fov'

class CameraConfig:
    name = 'camera'

    bool_use         = 'bool_use'

    str_manufacturer = 'str_manufacturer'
    str_model        = 'str_model'
    str_format       = 'str_format'
    int_resolution_x = 'int_resolution_x'
    int_resolution_y = 'int_resolution_y'

class GuiConfig:
    name = 'gui'

    bool_use         = 'bool_use'
