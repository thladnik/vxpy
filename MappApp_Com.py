class Display:

    class Settings:
        glob_x_pos = 'glob_x_pos'
        glob_y_pos = 'glob_y_pos'
        glob_disp_size = 'disp_size_glob'
        elev_angle = 'elev_angle'
        vp_center_dist = 'vp_center_dist'
        disp_screen_id = 'disp_screen_id'
        disp_fullscreen = 'disp_fullscreen'

    class ToPresenter:
        range = [0, 100]
        Close = 199

    class ToDisplay:
        range = [100, 200]
        NewSettings = 100
        SetNewStimulus = 101
        Close = 199

    class ToMain:
        range = [200, 300]
        Ready = 200
        Close = 299
