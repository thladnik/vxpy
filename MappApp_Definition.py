class Processes:
    """
    Process names have to be exclusively LOWER CASE
    """
    CONTROL = 'control'
    DISPLAY = 'display'
    IO = 'io'

class DisplaySettings:
    _name = 'DisplaySettings'

    float_glob_x_pos = 'float_glob_x_pos'
    float_glob_y_pos = 'float_glob_y_pos'
    float_vp_center_offset = 'float_vp_center_offset'
    float_view_axis_offset = 'float_view_axis_offset'
    float_elev_angle = 'float_elev_angle'
    float_vp_fov = 'float_vp_fov'
    int_disp_screen_id = 'int_disp_screen_id'
    bool_disp_fullscreen = 'bool_disp_fullscreen'