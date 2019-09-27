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

class DisplayGrating(Stimulus):

    def __init__(self):
        self.fps = 20
        self.frametime = 1.0 / self.fps
        self.time = 0.0
        self.movie = h5py.File('teststim.h5', 'r')['stimulus'][:]
        self.endtime = self.movie.shape[0] / self.fps

    def frame(self, dt):
        self.time += dt

        # Just for now: loop
        if self.time > self.endtime:
            self.time = 0.0

        return self.movie[int(self.time//self.frametime),:,:,:]


class DisplayCheckerboard(Stimulus):

    def __init__(self, rows=5, cols=5):
        self.fps = 20
        self.frametime = 1.0 / self.fps
        self.time = 0.0

        # Generate primitive
        primitive = np.append(np.ones((5,5)), np.zeros((5,5)), axis=0)
        primitive = np.append(primitive, np.flipud(primitive), axis=1)

        # Construct rows
        checker = primitive.copy()
        for i in range(rows-1):
            checker = np.append(checker, primitive, axis=0)

        # Construct columns
        primitive = checker.copy()
        for i in range(cols-1):
            checker = np.append(checker, primitive, axis=1)

        # Construct checkerboard frame (RGBA)
        self.checkerboard = np.repeat(checker[:, :, np.newaxis], 3, axis=2)  # Triple for RGB
        self.checkerboard = np.append(self.checkerboard, np.ones(self.checkerboard.shape[:2])[:, :, np.newaxis], axis=2)  # Add alpha

    def frame(self, dt):
        return self.checkerboard