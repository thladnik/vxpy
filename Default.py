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
        Definition.DisplayConfig.use                    : True,

        Definition.DisplayConfig.fps                    : 60,

        Definition.DisplayConfig.window_screen_id       : 0,
        Definition.DisplayConfig.window_fullscreen      : False,
        Definition.DisplayConfig.window_width           : 900,
        Definition.DisplayConfig.window_height          : 600,
        Definition.DisplayConfig.window_pos_x           : 400,
        Definition.DisplayConfig.window_pos_y           : 400,

        Definition.DisplayConfig.pos_glob_x_pos         : 0.0,
        Definition.DisplayConfig.pos_glob_y_pos         : 0.0,
        Definition.DisplayConfig.pos_glob_radial_offset : 1.0,

        Definition.DisplayConfig.view_elev_angle        : 0.0,
        Definition.DisplayConfig.view_azim_angle        : 0.0,
        Definition.DisplayConfig.view_distance          : 5.0,
        Definition.DisplayConfig.view_scale             : 1.0,
    },

    Definition.CameraConfig.name : {
        Definition.CameraConfig.use                     : True,
        Definition.CameraConfig.manufacturer            : 'virtual',
        Definition.CameraConfig.model                   : 'cam01',
        Definition.CameraConfig.format                  : 'RGB (600, 400)',
        Definition.CameraConfig.resolution_x            : 600,
        Definition.CameraConfig.resolution_y            : 400
    },

    Definition.GuiConfig.name : {
        Definition.GuiConfig.use                        : True
    }
}