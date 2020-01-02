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