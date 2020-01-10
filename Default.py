"""
MappApp ./Default.py - Default values and settings required to run program.
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

import Definition

Configuration = {
    Definition.DisplayConfig.name : {
        Definition.DisplayConfig.bool_use  : True,

        Definition.DisplayConfig.float_pos_glob_x_pos         : 0.0,
        Definition.DisplayConfig.float_pos_glob_y_pos         : 0.0,
        Definition.DisplayConfig.float_pos_glob_radial_offset : 1.0,

        Definition.DisplayConfig.float_view_elev_angle        : 0.0,
        Definition.DisplayConfig.float_view_axis_offset       : 0.0,
        Definition.DisplayConfig.float_view_origin_distance   : 5.0,
        Definition.DisplayConfig.float_view_fov               : 25.0,

        Definition.DisplayConfig.int_disp_screen_id           : 0,
        Definition.DisplayConfig.bool_disp_fullscreen         : False
    },

    Definition.CameraConfig.name : {
        Definition.CameraConfig.bool_use                     : True,
        Definition.CameraConfig.str_manufacturer             : 'virtual',
        Definition.CameraConfig.str_model                    : 'cam01',
        Definition.CameraConfig.str_format                   :'str_format',
        Definition.CameraConfig.int_resolution_x             : 600,
        Definition.CameraConfig.int_resolution_y             : 400
    },

    Definition.GuiConfig.name : {
        Definition.GuiConfig.bool_use                        : True
    }
}