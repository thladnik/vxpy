
class Path:
    config = 'config'

class Process:

    # Default signals
    class Signal:
        rpc = '_rpc'
        query = '_query'

        setProperty = 'set_property'

        shutdown = '_start_shutdown'
        confirm_shutdown = '_confirm_shutdown'

    # Default states
    class State:
        stopped = 99

    # Processes
    class Controller:
        name = 'controller'
    class Display:
        name = 'display'
    class IO:
        name = 'io'
    class DataCruncher:
        name = 'data_cruncher'
    class GUI:
        name = 'gui'
    class FrameGrabber:
        name = 'video_grabber'

        toggleVideoRecording = '_toggleVideoRecording'
        startVideoRecording = '_startVideoRecording'
        stopVideoRecording = '_stopVideoRecording'
        updateBufferEvalParams = '_updateBufferEvalParams'


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