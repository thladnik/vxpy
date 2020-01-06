from glumpy import app, glm
import logging
import numpy as np

import Controller
import Definition
import Logging
import StaticProtocol

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class Main(Controller.BaseProcess):
    name = Definition.Process.Display

    _config   : dict              = dict()
    _glWindow : app.window.Window = None
    protocol  : StaticProtocol    = None

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        ### Set Glumpy to use pyglet backend
        app.use('pyglet') # TODO: problem with pyglet backend on some systems? Perhaps version issue?

        ### Open OpenGL window
        self._glWindow = app.Window(width=1200, height=700, color=(1, 1, 1, 1), title='Display')
        self._glWindow.set_position(400, 400)

        ### Apply event wrapper
        self.on_draw = self._glWindow.event(self.on_draw)
        self.on_resize = self._glWindow.event(self.on_resize)
        self.on_init = self._glWindow.event(self.on_init)

        ### Register display configuration with controller
        self.registerPropertyWithController('_config_Display')

        ### Run event loop
        self.run()

    ################
    ### Properties

    @property
    def _config_Display(self):
        return self._config
    @_config_Display.setter
    def _config_Display(self, config):
        self._config.update(config)

        self._updateDisplayUniforms()

        if self._glWindow is not None:
            self._glWindow.dispatch_event('on_resize', self._glWindow._width, self._glWindow._height)

    def on_init(self):
        """Glumpy on_init event
        """
        pass

    def on_draw(self, dt):
        """Glumpy on_draw event

        :param dt: elapsed time since last call in [s]
        :return:
        """

        ### Clear window
        self._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))

        ### Check if protocol is set yet
        if self.protocol is None:
            return

        ### Call draw of protocol class
        self.protocol.draw(dt)

    def on_resize(self, width: int, height: int):
        """Glumpy on_resize event

        :param width: new pixel width of window
        :param height: new pixel height of window
        :return:
        """

        ### Fix for (many different) glumpy backends:
        self._glWindow._width = width
        self._glWindow._height = height

        ### Check if protocol is set yet
        if self.protocol is None:
            return

        ### Update viewport (center local viewport with aspect = 1 )
        x_add = int(width * self._config_Display[Definition.DisplayConfig.float_pos_glob_x_pos])
        y_add = int(height * self._config_Display[Definition.DisplayConfig.float_pos_glob_y_pos])
        if height > width:
            length = width
            x_offset = x_add
            y_offset = (height - length) // 2 + y_add
        else:
            length = height
            x_offset = (width - length) // 2 + x_add
            y_offset = y_add
        self.protocol.program['viewport']['global'] = (0, 0, width, height)
        self.protocol.program['viewport']['local'] = (x_offset, y_offset, length, length)

    def _toggleFullscreen(self):
        """Toggle the fullscreen state of the OpenGL window
        """
        if self._glWindow.get_fullscreen() != self._config_Display[Definition.DisplayConfig.bool_disp_fullscreen]:
            self._glWindow.set_fullscreen(self._config_Display[Definition.DisplayConfig.bool_disp_fullscreen],
                                          screen=self._config_Display[Definition.DisplayConfig.int_disp_screen_id])

    def startNewStimulationProtocol(self, protocol_cls):
        """Start the presentation of a new stimulation protocol

        :param protocol_cls: class object of the stimulation protocol
        :return:
        """

        ### Initialize new stimulus protocol
        Logging.logger.log(logging.INFO, 'Start new stimulation procotol {}'.
                           format(str(protocol_cls)))
        self.protocol = protocol_cls(self)


    def _updateDisplayUniforms(self):
        if self.protocol is None:
            return

        ## Set default image channel parameters
        std_trans_distance = -self._config_Display[Definition.DisplayConfig.float_view_origin_distance]
        std_fov = self._config_Display[Definition.DisplayConfig.float_view_fov]
        std_azimuth_rot = 180.
        std_elevation_rot = 90.
        std_radial_offset = self._config_Display[Definition.DisplayConfig.float_pos_glob_radial_offset]
        std_tangent_offset = 0.

        elevation_rot_sw = self._config_Display[Definition.DisplayConfig.float_view_elev_angle]
        elevation_rot_se = self._config_Display[Definition.DisplayConfig.float_view_elev_angle]
        elevation_rot_ne = self._config_Display[Definition.DisplayConfig.float_view_elev_angle]
        elevation_rot_nw = self._config_Display[Definition.DisplayConfig.float_view_elev_angle]

        azimuth_rot_sw = std_azimuth_rot + 0.
        azimuth_rot_se = std_azimuth_rot + 0.
        azimuth_rot_ne = std_azimuth_rot + 0.
        azimuth_rot_nw = std_azimuth_rot + 0.

        ## SOUTH WEST
        # Non-linear transformations
        rot_axis_sw = (1, -1, 0)
        u_projection = glm.perspective(std_fov, 1.0, 0.01, 1000.0)
        u_rot = np.eye(4, dtype=np.float32)
        glm.rotate(u_rot, azimuth_rot_sw, 0, 0, 1)  # Rotate around equator
        glm.rotate(u_rot, std_elevation_rot - elevation_rot_sw,
                   *rot_axis_sw)  # Rotate around current azim. major circle
        u_trans = glm.translation(0., 0., std_trans_distance)
        self.protocol.program['u_trans_sw'] = u_trans
        self.protocol.program['u_rot_sw'] = u_rot
        self.protocol.program['u_projection_sw'] = u_projection
        # Linear image plane transformations
        self.protocol.program['u_radial_offset_sw'] = std_radial_offset
        self.protocol.program['u_tangent_offset_sw'] = std_tangent_offset

        ## SOUTH EAST
        # Non-linear transformations
        rot_axis_se = (1, 1, 0)
        u_projection = glm.perspective(std_fov, 1.0, 0.01, 1000.0)
        u_rot = np.eye(4, dtype=np.float32)
        glm.rotate(u_rot, azimuth_rot_se, 0, 0, 1)  # Rotate around equator
        glm.rotate(u_rot, std_elevation_rot - elevation_rot_se,
                   *rot_axis_se)  # Rotate around current azim. major circle
        u_trans = glm.translation(0., 0., std_trans_distance)
        self.protocol.program['u_trans_se'] = u_trans
        self.protocol.program['u_rot_se'] = u_rot
        self.protocol.program['u_projection_se'] = u_projection
        # Linear image plane transformations
        self.protocol.program['u_radial_offset_se'] = std_radial_offset
        self.protocol.program['u_tangent_offset_se'] = std_tangent_offset

        rot_axis_ne = (-1, 1, 0)
        u_projection = glm.perspective(std_fov, 1.0, 0.01, 1000.0)
        u_rot = np.eye(4, dtype=np.float32)
        glm.rotate(u_rot, azimuth_rot_ne, 0, 0, 1)  # Rotate around equator
        glm.rotate(u_rot, std_elevation_rot - elevation_rot_ne,
                   *rot_axis_ne)  # Rotate around current azim. major circle
        u_trans = glm.translation(0., 0., std_trans_distance)
        self.protocol.program['u_trans_ne'] = u_trans
        self.protocol.program['u_rot_ne'] = u_rot
        self.protocol.program['u_projection_ne'] = u_projection
        # Linear image plane transformations
        self.protocol.program['u_radial_offset_ne'] = std_radial_offset
        self.protocol.program['u_tangent_offset_ne'] = std_tangent_offset

        rot_axis_nw = (-1, -1, 0)
        u_projection = glm.perspective(std_fov, 1.0, 0.01, 1000.0)
        u_rot = np.eye(4, dtype=np.float32)
        glm.rotate(u_rot, azimuth_rot_nw, 0, 0, 1)  # Rotate around equator
        glm.rotate(u_rot, std_elevation_rot - elevation_rot_nw,
                   *rot_axis_nw)  # Rotate around current azim. major circle
        u_trans = glm.translation(0., 0., std_trans_distance)
        self.protocol.program['u_trans_nw'] = u_trans
        self.protocol.program['u_rot_nw'] = u_rot
        self.protocol.program['u_projection_nw'] = u_projection
        # Linear image plane transformations
        self.protocol.program['u_radial_offset_nw'] = std_radial_offset
        self.protocol.program['u_tangent_offset_nw'] = std_tangent_offset

    def _startShutdown(self):
        self._glWindow.close()
        Controller.BaseProcess._startShutdown(self)

    def main(self):
        self._updateDisplayUniforms()

        # Schedule glumpy to check for new inputs (keep this as INfrequent as possible, rendering has priority)
        app.clock.schedule_interval(self._handleCommunication, 0.01)

        # Run Glumpy event loop
        app.run(framerate=60)
