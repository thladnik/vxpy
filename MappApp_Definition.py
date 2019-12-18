
class Path:
    Config   = 'configs'
    Log      = 'logs'
    Model    = 'models'
    Protocol = 'protocols'
    Shader   = 'shaders'

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
        # RPC bindings
        pass

    class DataCruncher:
        name = 'data_cruncher'
        # RPC bindings
        pass

    class Display:
        name = 'display'
        # RPC bindings
        startNewStimulationProtocol = '_startNewStimulationProtocol'
        updateConfiguration         = '_updateConfiguration'

    class GUI:
        name = 'gui'
        # RPC bindings
        pass

    class IO:
        name = 'io'
        # RPC bindings
        pass

    class Logger:
        name = 'logger'
        # RPC bindings
        pass

    class FrameGrabber:
        name = 'frame_grabber'
        # RPC bindings
        toggleVideoRecording   = '_toggleVideoRecording'
        startVideoRecording    = '_startVideoRecording'
        stopVideoRecording     = '_stopVideoRecording'
        updateBufferEvalParams = '_updateBufferEvalParams'

class DisplayConfig:
    _name = 'display'

    float_pos_glob_x_pos         = 'float_pos_glob_x_pos'
    float_pos_glob_y_pos         = 'float_pos_glob_y_pos'
    float_pos_glob_radial_offset = 'float_pos_glob_radial_offset'

    float_view_elev_angle        = 'float_view_elev_angle'
    float_view_axis_offset       = 'float_view_axis_offset'
    float_view_origin_distance   = 'float_view_origin_distance'
    float_view_fov               = 'float_view_fov'

    int_disp_screen_id           = 'int_disp_screen_id'
    bool_disp_fullscreen         = 'bool_disp_fullscreen'

class CameraConfiguration:
    _name = 'camera'

    str_manufacturer = 'str_manufacturer'
    str_model        = 'str_model'
    str_format       = 'str_format'
    int_resolution_x = 'int_resolution_x'
    int_resolution_y = 'int_resolution_y'
