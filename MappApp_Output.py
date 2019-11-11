from glumpy import app, gl, glm, gloo, transforms
import numpy as np

from MappApp_Geometry import SphericalArena
import MappApp_Communication as macom
import MappApp_Definition as madef
from devices import Arduino

from IPython import embed

# Set Glumpy to use qt5 backend
app.use('qt5')

class IO:
    """
    Handles analogue/digital IO
    """

    def __init__(self):

        ## Setup listener
        ipc = macom.IPC()
        ipc.loadConnections()
        self.listener = ipc.getMetaListener(madef.Processes.IO)
        # Wait for clients
        self.listener.acceptClients()

        ## Setup serial connection
        self.serialConn = Arduino.getSerialConnection()

        self.data = list()

        self.serialbit = 0

    def start(self):
        while True:

            line = self.serialConn.readline()
            if line.decode('ascii') != '':
                self.data.append(line.decode('ascii'))

            if len(self.data) == 2000:
                with open('your_file.txt', 'w') as f:
                    for item in self.data:
                        f.write("%s" % item)

            obj = self.listener.receive()

            if obj is None:
                continue

            if obj[0] == macom.IO.Code.DO_NextFrame:
                # Write 1 to serial device
                self.serialConn.write(b'1')
            elif obj[0] == macom.IO.Code.Close:
                print('Closing IO')
                # Close serial connection
                self.serialConn.close()
                # Close listener connections
                import time
                time.sleep(4)
                self.listener.close()

                break

def runIO():
    io = IO()
    io.start()



# Define sphere
sphere = SphericalArena(theta_lvls=100, phi_lvls=50, upper_phi=45.0, radius=1.0)

class Display:

    modelRotationAxes = {
        'ne' : ( 1,-1, 0),
        'nw' : ( 1, 1, 0),
        'sw' : (-1, 1, 0),
        'se' : (-1,-1, 0)
    }

    modelTranslationAxes = {
        'ne' : ( 1, 1, 0),
        'nw' : (-1, 1, 0),
        'sw' : (-1,-1, 0),
        'se' : ( 1,-1, 0)
    }

    modelZeroElevRotation = {
        'ne': -90.0,
        'nw': -90.0,
        'sw': -90.0,
        'se': -90.0
    }

    def __init__(self):

        ## Load client connections
        ipc = macom.IPC()
        ipc.loadConnections()
        self.clientToCtrl = ipc.getClientConnection(madef.Processes.CONTROL, madef.Processes.DISPLAY)
        self.clientToIO = ipc.getClientConnection(madef.Processes.IO, madef.Processes.DISPLAY)

        ## Setup window
        self.window = app.Window(width=800, height=600, color=(1, 1, 1, 1))

        self.program = None
        self.stimulus = None

        # Apply event wrapper
        self.on_draw = self.window.event(self.on_draw)
        self.on_resize = self.window.event(self.on_resize)
        self.on_init = self.window.event(self.on_init)

        # Wait to receive display settings
        obj = self.clientToCtrl.recv()
        if not(obj[0] == macom.Display.Code.NewDisplaySettings):
            print('ERROR: display requires initial message to be the display configuration.')
            self.window.close()
        self.displaySettings = obj[1]

        # Check fullscreen state and change if necessary
        self.checkFullscreen()

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
            #tex_coords = sphere.ortho2DTexture(vertices)

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
        if not(self.clientToCtrl.poll(timeout=.0001)):
            return

        ## Receive message
        obj = self.clientToCtrl.recv()

        ## App close event
        if obj[0] == macom.Display.Code.Close:
            print('Closing display')
            self.window.close()

        ## New display settings
        elif obj[0] == macom.Display.Code.NewDisplaySettings:

            if self.program is None:
                return

            # Update display settings
            self.displaySettings = obj[1]

            # Check fullscreen state and change if necessary
            self.checkFullscreen()

            # Dispatch resize event
            self.window.dispatch_event('on_resize', self.window.width, self.window.height)

        ## New stimulus
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

            # Setup new program
            self.setupProgram()

            # Dispatch resize event
            self.window.dispatch_event('on_resize', self.window.width, self.window.height)

    def checkFullscreen(self):
        if self.window.get_fullscreen() != self.displaySettings[madef.DisplaySettings.bool_disp_fullscreen]:
            self.window.set_fullscreen(self.displaySettings[madef.DisplaySettings.bool_disp_fullscreen],
                                       screen=self.displaySettings[madef.DisplaySettings.int_disp_screen_id])

    def on_draw(self, dt):
        ## Only draw a frame if both program and stimulus are set
        if self.program is None:
            return
        if self.stimulus is None:
            return

        ## Fetch texture for next frame
        frame = self.stimulus.frame(dt)

        ## Clear window
        self.window.clear(color=(0.0, 0.0, 0.0, 1.0))  # black
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # TODO: include possibility to construct stimuli directly in the shader
        #       This would require an option to not use texture mapping but to set uniforms as
        #       Specified by a uniforms attribute in the Stimulus class for example.
        ## Set texture and draw new frame
        for orient in self.program:
            self.program[orient]['u_texture'] = frame
            self.program[orient].draw(gl.GL_TRIANGLES, self.i[orient])

        ## Output frame sync signal via IO
        self.clientToIO.send([macom.IO.Code.DO_NextFrame])

    def on_resize(self, width, height):
        ## Only draw a frame if both program and stimulus are set
        if self.program is None:
            return
        if self.stimulus is None:
            return

        ## Fix for qt5 backend in glumpy:
        self.window._width = width
        self.window._height = height

        ## Calculate child viewport size
        if width > height:
            length = height
        elif height > width:
            length = width
        else:
            length = height
        halflength = length // 2

        ## Get current display settings
        view_axis_offset       = self.displaySettings[madef.DisplaySettings.float_view_axis_offset]
        view_fov               = self.displaySettings[madef.DisplaySettings.float_view_fov]
        view_elev_angle        = self.displaySettings[madef.DisplaySettings.float_view_elev_angle]
        pos_glob_x_pos         = self.displaySettings[madef.DisplaySettings.float_pos_glob_x_pos]
        pos_glob_y_pos         = self.displaySettings[madef.DisplaySettings.float_pos_glob_y_pos]
        pos_glob_center_offset = 1-self.displaySettings[madef.DisplaySettings.float_pos_glob_center_offset]
        origin_distance        = self.displaySettings[madef.DisplaySettings.float_view_origin_distance]

        xpos = int(width * pos_glob_x_pos)
        ypos = int(height * pos_glob_y_pos)

        ## Set uniforms for each part of the sphere
        for orient in self.program:

            ## Set translation
            self.program[orient]['u_trans'] = glm.translation(
                self.modelTranslationAxes[orient][0] * view_axis_offset,
                self.modelTranslationAxes[orient][1] * view_axis_offset,
                -origin_distance
            )

            ## Set rotation
            rot = np.eye(4, dtype=np.float32)
            glm.rotate(rot, 180, 0, 0, 1)
            glm.rotate(rot, self.modelZeroElevRotation[orient], *self.modelRotationAxes[orient])
            glm.rotate(rot, view_elev_angle, *self.modelRotationAxes[orient])
            self.program[orient]['u_rot'] = rot

        ## Set viewports
        # North-east
        offset = halflength*pos_glob_center_offset
        self.program['ne']['viewport']['global'] = (0, 0, width, height)
        x, y = halflength+xpos-int(offset), halflength+ypos-int(offset)
        self.program['ne']['viewport']['local'] = (x, y, halflength, halflength)
        # South-east
        self.program['se']['viewport']['global'] = (0, 0, width, height)
        x, y = halflength+xpos-int(offset), ypos+int(offset)
        self.program['se']['viewport']['local'] = (x, y, halflength, halflength)
        # South-west
        self.program['sw']['viewport']['global'] = (0, 0, width, height)
        x, y = xpos+int(offset), ypos+int(offset)
        self.program['sw']['viewport']['local'] = (x, y, halflength, halflength)
        # North-west
        self.program['nw']['viewport']['global'] = (0, 0, width, height)
        x, y = xpos+int(offset), halflength+ypos-int(offset)
        self.program['nw']['viewport']['local'] = (x, y, halflength, halflength)

        ## Set perspective projection
        self.program['ne']['u_projection'] = glm.perspective(view_fov, 1.0, 0.1, 10.0)
        self.program['se']['u_projection'] = glm.perspective(view_fov, 1.0, 0.1, 10.0)
        self.program['sw']['u_projection'] = glm.perspective(view_fov, 1.0, 0.1, 10.0)
        self.program['nw']['u_projection'] = glm.perspective(view_fov, 1.0, 0.1, 10.0)

        # Draw
        self.window.dispatch_event('on_draw', 0.0)

    def on_init(self):
        pass

def runDisplay(fps, *args, **kwargs):

    display = Display(*args, **kwargs)

    # Schedule glumpy to check for new inputs (keep this as INfrequent as possible, rendering has priority)
    app.clock.schedule_interval(display._handleCommunication, 0.1)
    #
    app.run(framerate=fps)