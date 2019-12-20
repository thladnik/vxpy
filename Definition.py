
class Path:
    Config   = 'configs'
    Log      = 'logs'
    Model    = 'models'
    Protocol = 'protocols'
    Shader   = 'shaders'

class Process:
    Camera = 'camera'
    Controller = 'controller'
    Display = 'display'
    GUI = 'gui'
    Logger = 'logger'

class DisplayConfig:
    name = 'display'

    bool_use                     = 'bool_use'

    float_pos_glob_x_pos         = 'float_pos_glob_x_pos'
    float_pos_glob_y_pos         = 'float_pos_glob_y_pos'
    float_pos_glob_radial_offset = 'float_pos_glob_radial_offset'

    float_view_elev_angle        = 'float_view_elev_angle'
    float_view_axis_offset       = 'float_view_axis_offset'
    float_view_origin_distance   = 'float_view_origin_distance'
    float_view_fov               = 'float_view_fov'

    int_disp_screen_id           = 'int_disp_screen_id'
    bool_disp_fullscreen         = 'bool_disp_fullscreen'

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

    bool_use         = True
