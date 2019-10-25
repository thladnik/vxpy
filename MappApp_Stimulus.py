import h5py
import numpy as np

class Stimulus:

    vertex_shader = """
        uniform mat4   u_rot;         // Model matrix
        uniform mat4   u_trans;          // View matrix
        uniform mat4   u_projection;    // Projection matrix
        attribute vec3 a_position;      // Vertex position
        attribute vec2 a_texcoord;      // Vertex texture coordinates
        varying vec2   v_texcoord;      // Interpolated fragment texture coordinates (out)
        void main()
        {
            // Assign varying variables
            v_texcoord  = a_texcoord;
            // Final position
            gl_Position = u_projection * u_trans * u_rot * vec4(a_position,1.0);
            <viewport.transform>;
        }
    """

    fragment_shader = """
        uniform sampler2D u_texture;  // Texture 
        varying vec2      v_texcoord; // Interpolated fragment texture coordinates (in)
        void main()
        {
            <viewport.clipping>;
            // Get texture color
            vec4 t_color = texture2D(u_texture, v_texcoord);
            // Final color
            gl_FragColor = t_color;
        }
    """

    def frame(self, dt):
        """
        Re-implemented by stimulus class
        """
        pass


class DisplayMovingGrating(Stimulus):

    def __init__(self):
        self.fps = 20
        self.frametime = 1.0 / self.fps
        self.movementVelocity = 3

        self.time = 0.0

    def frame(self, dt):
        self.time += dt

        shift = self.time*self.movementVelocity

        _frame = np.ones((400, 800))
        _frame *= np.sin(2 * np.pi * np.linspace(0, 20, _frame.shape[1]) + shift).reshape((1, -1))
        _frame = np.repeat(_frame[:, :, np.newaxis], 4, axis=2)
        _frame[_frame >= 0.] = 1.
        _frame[_frame < 0.] = 0.
        _frame[:, :, -1] = 1.

        return _frame

class DisplayMovingSinusoid(Stimulus):

    def __init__(self):
        self.fps = 20
        self.frametime = 1.0 / self.fps
        self.movementVelocity = 3

        self.time = 0.0

    def frame(self, dt):
        self.time += dt

        shift = self.time*self.movementVelocity

        _frame = np.ones((400, 800))
        _frame *= np.sin(2 * np.pi * np.linspace(0, 20, _frame.shape[1]) + shift).reshape((1, -1))
        _frame = np.repeat(_frame[:,:,np.newaxis], 4, axis=2)
        _frame[:,:,-1] = 1.

        return _frame

class DisplayCheckerboard(Stimulus):

    def __init__(self, rows=5, cols=5):
        self.fps = 20
        self.frametime = 1.0 / self.fps
        self.time = 0.0

        # Construct checkerboard
        sr = 20
        checker = np.ones((sr*rows, sr*cols))
        checker = (checker * np.sin(np.linspace(0., np.pi*cols, sr*cols))).T
        checker = (checker * np.sin(np.linspace(0., np.pi*rows, sr*rows))).T
        checker[checker > 0.] = 1.
        checker[checker <= 0] = 0.

        checker = np.repeat(checker[:,:,np.newaxis], 4, axis=2)
        checker[:,:,-1] = 1

        self.checkerboard = checker

    def frame(self, dt):
        # Color inverse flickering
        #self.checkerboard = (self.checkerboard.astype(bool) == False).astype(float)
        #self.checkerboard[:,:,-1] = 1.
        return self.checkerboard


