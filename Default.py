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

import Def

Configuration = {

    Def.CameraCfg.name: {
        Def.CameraCfg.use                     : True,

        Def.CameraCfg.manufacturer            : 'virtual',
        Def.CameraCfg.model                   : 'cam01',
        Def.CameraCfg.format                  : 'RGB (600, 400)',
        Def.CameraCfg.res_y                   : 600,
        Def.CameraCfg.res_x                   : 400,
        Def.CameraCfg.fps                     : 60,
        Def.CameraCfg.exposure                : 2.0,
        Def.CameraCfg.gain                    : 1.0,
        Def.CameraCfg.routines                 : ''
    },

    Def.DisplayCfg.name : {
        Def.DisplayCfg.use                    : True,
        Def.DisplayCfg.type                   : 'spherical',

        Def.DisplayCfg.fps                    : 60,

        Def.DisplayCfg.window_screen_id       : 0,
        Def.DisplayCfg.window_fullscreen      : False,
        Def.DisplayCfg.window_width           : 900,
        Def.DisplayCfg.window_height          : 600,
        Def.DisplayCfg.window_pos_x           : 400,
        Def.DisplayCfg.window_pos_y           : 400,

        Def.DisplayCfg.pos_glob_x_pos         : 0.0,
        Def.DisplayCfg.pos_glob_y_pos         : 0.0,
        Def.DisplayCfg.pos_glob_radial_offset : 1.0,

        Def.DisplayCfg.view_elev_angle        : 0.0,
        Def.DisplayCfg.view_azim_angle        : 0.0,
        Def.DisplayCfg.view_distance          : 5.0,
        Def.DisplayCfg.view_scale             : 1.0,
    },

    Def.GuiCfg.name : {
        Def.GuiCfg.use                        : True,

        Def.GuiCfg.addons                     : ''
    },

    Def.RecCfg.name : {
        Def.RecCfg.enabled              : True,
        Def.RecCfg.routines              : []
    }
}