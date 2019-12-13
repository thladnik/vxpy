from glumpy import app, glm
import numpy as np

from process.Base import BaseProcess
import MappApp_Definition as madef

######
# Worker processes

# Set Glumpy to use qt5 backend
app.use('qt5')

class Display(BaseProcess):

    _name = madef.Process.Display.name

    def __init__(self, _configuration, **kwargs):
        self._glWindow = app.Window(width=800, height=600, color=(1, 1, 1, 1), title='Display')
        self._configuration = _configuration
        BaseProcess.__init__(self, **kwargs)
        self.protocol = None

        ## Apply event wrapper
        self.on_draw = self._glWindow.event(self.on_draw)
        self.on_resize = self._glWindow.event(self.on_resize)
        self.on_init = self._glWindow.event(self.on_init)

        self.run()

    def on_init(self):
        pass

    def on_draw(self, dt):
        print(dt)
        if self.protocol is None:
            return

        # Clear window
        self._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))  # black

        # Call draw
        self.protocol.draw(dt)

    def on_resize(self, width, height):
        if self.protocol is None:
            return

        ## Update viewport (center local viewport with aspect = 1)
        if height > width:
            length = width
            x_offset = 0
            y_offset = (height - length) // 2
        else:
            length = height
            x_offset = (width - length) // 2
            y_offset = 0
        self.protocol.program['viewport']['global'] = (0, 0, width, height)
        self.protocol.program['viewport']['local'] = (x_offset, y_offset, length, length)

    def _startNewStimulationProtocol(self, protocol_cls):
        ## Initialize new stimulus protocol
        print('Start new procotol %s' % str(protocol_cls))
        self.protocol = protocol_cls(self)


    def _updateConfiguration(self, **kwargs):
        if self.protocol is None:
            return

        for key, value in kwargs.items():
            if key in self._configuration:
                self._configuration = value

        self._updateUniforms()

    def _updateUniforms(self):
        if self.protocol is None:
            return

        ## Set default image channel parameters
        std_trans_distance = -10.
        std_fov = 30.
        std_elevation_rot = 90.
        std_radial_offset = 0.5
        std_tangent_offset = 0.

        elevation_rot_sw = 0.
        elevation_rot_se = 0.
        elevation_rot_ne = 0.
        elevation_rot_nw = 0.

        azimuth_rot_sw = 0.
        azimuth_rot_se = 0.
        azimuth_rot_ne = 0.
        azimuth_rot_nw = 0.

        ## SOUTH WEST
        # Non-linear transformations
        rot_axis_sw = (-1, 1, 0)
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
        rot_axis_se = (-1, -1, 0)
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

        rot_axis_ne = (1, -1, 0)
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

        rot_axis_nw = (1, 1, 0)
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

    def _start_shutdown(self):
        self._glWindow.close()
        BaseProcess._start_shutdown(self)

    def main(self):
        self._updateUniforms()

        # Schedule glumpy to check for new inputs (keep this as INfrequent as possible, rendering has priority)
        app.clock.schedule_interval(self._handlePipe, 0.01)

        # Run Glumpy event loop
        app.run(framerate=60)
