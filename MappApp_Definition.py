class Processes:
    """
    Process names have to be exclusively LOWER CASE
    """
    CONTROL = 'control'
    DISPLAY = 'display'
    STIMINSPECT = 'stimulus_inspector'
    IO = 'io'

class DisplaySettings:
    _name = 'DisplaySettings'

    float_pos_glob_x_pos         = 'float_pos_glob_x_pos'
    float_pos_glob_y_pos         = 'float_pos_glob_y_pos'
    float_pos_glob_center_offset = 'float_pos_glob_center_offset'

    float_view_elev_angle        = 'float_view_elev_angle'
    float_view_axis_offset       = 'float_view_axis_offset'
    float_view_origin_distance   = 'float_view_origin_distance'
    float_view_fov               = 'float_view_fov'

    int_disp_screen_id           = 'int_disp_screen_id'
    bool_disp_fullscreen         = 'bool_disp_fullscreen'

class Paths:

    Shader = 'shaders'
    Model = 'models'
    Protocol = 'protocols'