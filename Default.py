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

    Definition.Camera.name: {
        Definition.Camera.use                     : True,

        Definition.Camera.manufacturer            : 'virtual',
        Definition.Camera.model                   : 'cam01',
        Definition.Camera.format                  : 'RGB (600, 400)',
        Definition.Camera.res_y                   : 600,
        Definition.Camera.res_x                   : 400,
        Definition.Camera.fps                     : 60,
        Definition.Camera.exposure                : 2.0,
        Definition.Camera.buffers                 : ''
    },

    Definition.Display.name : {
        Definition.Display.use                    : True,
        Definition.Display.type                   : 'spherical',

        Definition.Display.fps                    : 60,

        Definition.Display.window_screen_id       : 0,
        Definition.Display.window_fullscreen      : False,
        Definition.Display.window_width           : 900,
        Definition.Display.window_height          : 600,
        Definition.Display.window_pos_x           : 400,
        Definition.Display.window_pos_y           : 400,

        Definition.Display.pos_glob_x_pos         : 0.0,
        Definition.Display.pos_glob_y_pos         : 0.0,
        Definition.Display.pos_glob_radial_offset : 1.0,

        Definition.Display.view_elev_angle        : 0.0,
        Definition.Display.view_azim_angle        : 0.0,
        Definition.Display.view_distance          : 5.0,
        Definition.Display.view_scale             : 1.0,
    },

    Definition.Gui.name : {
        Definition.Gui.use                        : True,

        Definition.Gui.addons                     : ''
    },

    Definition.Recording.name : {
        Definition.Recording.enabled              : True,
        Definition.Recording.active               : False,
        Definition.Recording.current_folder       : '',
        Definition.Recording.buffers              : []
    }
}