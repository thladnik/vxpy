from glumpy import app, gl, glm, gloo, transforms
import numpy as np
from multiprocessing import Pipe, Process
from multiprocessing.connection import Listener, Client
import time

from MappApp_Geometry import SphericalArena
import MappApp_Com as macom
import MappApp_Definition as madef


from IPython import embed

# Set Glumpy to use qt5 backend
app.use('qt5')

class IO:
    """
    Handles analogue/digital IO
    """
    pass

    def start(self):
        pass

def runIO():
    io = IO()
    io.start()



# Define sphere
sphere = SphericalArena(theta_lvls=100, phi_lvls=50, upper_phi=45.0, radius=1.0)

class Display:

    modelRotationAxes = {
        'ne' : (1, -1, 0),
        'nw' : (1, 1, 0),
        'sw' : (-1, 1, 0),
        'se' : (-1, -1, 0)
    }
    modelTranslationAxes = {
        'ne' : (1, 1, 0),
        'nw' : (-1, 1, 0),
        'sw' : (-1, -1, 0),
        'se' : (1, -1, 0)
    }

    modelTranslation = {
        'ne' : 0.0,
        'nw' : 0.0,
        'sw' : 0.0,
        'se' : 0.0
    }

    modelZeroElevRotation =  {
        'ne' : -90.0,
        'nw' : -90.0,
        'sw' : -90.0,
        'se' : -90.0
    }

    modelElevRotation = {
        'ne' : 0.0,
        'nw' : 0.0,
        'sw' : 0.0,
        'se' : 0.0
    }

    def __init__(self):

        ipc = macom.IPC()
        ipc.loadConnections()
        self.clientToMain = ipc.getClientConnection('main', 'display')

        self.window = app.Window(width=800, height=600, color=(1, 1, 1, 1))

        self.program = None
        self.stimulus = None
        self.vp_global_pos = (0., 0.)
        self.vp_global_size = 1.0
        self.disp_vp_center_dist = 0.0
        self.vp_fov = 50.
        self.elev_angle = 0.

        # Use event wrapper
        self.on_draw = self.window.event(self.on_draw)
        self.on_resize = self.window.event(self.on_resize)
        self.on_init = self.window.event(self.on_init)


    def setupProgram(self):
        self.program = dict()
        self.v = dict()
        self.i = dict()

        theta_range = 90.0
        for j, orient in enumerate(['ne', 'nw', 'sw', 'se']):
            theta_center = 45.0 + j * 90.0

            thetas, phis = sphere.getThetaSubset(theta_center - theta_range / 2, theta_center + theta_range / 2)

            # Vertices
            vertices = sphere.sph2cart(thetas, phis)
            tex_coords = sphere.mercator2DTexture(thetas, phis)
            indices = sphere.getFaceIndices(vertices)
            self.v[orient] = np.zeros(vertices.shape[0],
                         [('a_position', np.float32, 3),
                          ('a_texcoord', np.float32, 2)])
            self.v[orient]['a_position'] = vertices.astype(np.float32)
            self.v[orient]['a_texcoord'] = tex_coords.astype(np.float32).T
            self.v[orient] = self.v[orient].view(gloo.VertexBuffer)

            # Indices
            self.i[orient] = indices.astype(np.uint32)
            self.i[orient] = self.i[orient].view(gloo.IndexBuffer)

            ########
            # Program
            self.program[orient] = gloo.Program(self.stimulus.vertex_shader, self.stimulus.fragment_shader)
            self.program[orient].bind(self.v[orient])


            self.program[orient]['viewport'] = transforms.Viewport()


    def _handleCommunication(self, dt):

        # Receive data
        if not(self.clientToMain.poll(timeout=.0001)):
            return

        obj = self.clientToMain.recv()

        if obj is None:
            return

        # App close event
        if obj[0] == macom.Display.Code.Close:
            self.window.close()

        # New display settings
        elif obj[0] == macom.Display.Code.NewDisplaySettings:

            if self.program is None:
                return

            # Display parameters
            params = obj[1]

            # Set child viewport distance from center
            self.disp_vp_center_dist = params[madef.DisplaySettings.float_vp_center_dist]

            # Set global viewpoint position
            self.vp_global_pos = (params[madef.DisplaySettings.float_glob_x_pos], params[madef.DisplaySettings.float_glob_y_pos])

            if self.window.get_fullscreen() != params[madef.DisplaySettings.bool_disp_fullscreen]:
                print('Fullscreen state changed')
                self.window.set_fullscreen(params[madef.DisplaySettings.bool_disp_fullscreen], screen=params[madef.DisplaySettings.int_disp_screen_id])

            self.vp_fov = params[madef.DisplaySettings.float_vp_fov]

            self.elev_angle = params[madef.DisplaySettings.float_elev_angle]


            # Dispatch resize event
            self.window.dispatch_event('on_resize', self.window.width, self.window.height)

        # New stimulus to present
        elif obj[0] == macom.Display.Code.SetNewStimulus:
            stimcls = obj[1]

            args = []
            if len(obj) > 2:
                args = obj[2]
            kwargs = dict()
            if len(obj) > 3:
                kwargs = obj[3]


            # Create stimulus instance
            self.stimulus = stimcls(*args, **kwargs)

            self.setupProgram()

            # Dispatch resize event
            self.window.dispatch_event('on_resize', self.window.width, self.window.height)


    def on_draw(self, dt):

        if self.program is None:
            return

        if self.stimulus is None:
            return

        # Fetch texture frame
        frame = self.stimulus.frame(dt)

        # Clear
        self.window.clear(color=(0.0, 0.0, 0.0, 1.0))  # black
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Set texture and draw new frame
        for orient in self.program:
            self.program[orient]['u_texture'] = frame
            self.program[orient].draw(gl.GL_TRIANGLES, self.i[orient])

    def on_resize(self, width, height):

        if self.program is None:
            return

        # Fixes
        self.window._width = width
        self.window._height = height

        # Calculate child viewport size
        if width > height:
            length = height
        elif height > width:
            length = width
        else:
            length = height
        halflength = length // 2

        xpos = int(width * self.vp_global_pos[0])
        ypos = int(height * self.vp_global_pos[1])

        for orient in self.program:

            self.program[orient]['u_trans'] = glm.translation(
                self.modelTranslationAxes[orient][0] * self.disp_vp_center_dist,
                self.modelTranslationAxes[orient][1] * self.disp_vp_center_dist,
                -3
            )
            rot = np.eye(4, dtype=np.float32)
            glm.rotate(rot, 180, 0, 0, 1)
            glm.rotate(rot, self.modelZeroElevRotation[orient], *self.modelRotationAxes[orient])
            glm.rotate(rot, self.elev_angle, *self.modelRotationAxes[orient])
            self.program[orient]['u_rot'] = rot

        # Set viewports
        self.program['ne']['viewport']['global'] = (0, 0, width, height)
        self.program['ne']['viewport']['local'] = (halflength+xpos, halflength+ypos, halflength, halflength)

        self.program['se']['viewport']['global'] = (0, 0, width, height)
        self.program['se']['viewport']['local'] = (halflength+xpos, 0+ypos, halflength, halflength)

        self.program['sw']['viewport']['global'] = (0, 0, width, height)
        self.program['sw']['viewport']['local'] = (0+xpos, 0+ypos, halflength, halflength)

        self.program['nw']['viewport']['global'] = (0, 0, width, height)
        self.program['nw']['viewport']['local'] = (0+xpos, halflength+ypos, halflength, halflength)

        # Set projection
        self.program['ne']['u_projection'] = glm.perspective(self.vp_fov, 1.0, 0.1, 5.0)
        self.program['se']['u_projection'] = glm.perspective(self.vp_fov, 1.0, 0.1, 5.0)
        self.program['sw']['u_projection'] = glm.perspective(self.vp_fov, 1.0, 0.1, 5.0)
        self.program['nw']['u_projection'] = glm.perspective(self.vp_fov, 1.0, 0.1, 5.0)

        # Draw
        self.window.dispatch_event('on_draw', 0.0)
        self.window.swap()

    def on_init(self):
        if self.program is None:
            return

    def sendCloseInfo(self, fun):
        print('closing')
        fun()

def runDisplay(*args, **kwargs):

    display = Display(*args, **kwargs)

    # Schedule glumpy to check for new inputs (keep this as INfrequent as possible, rendering has priority)
    app.clock.schedule_interval(display._handleCommunication, 0.1)
    app.run(framerate=60)