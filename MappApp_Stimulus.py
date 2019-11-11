from glumpy import gl
import h5py
import imageio
import numpy as np

class Stimulus:
    base_vertex_shader = """
        const float pi = 3.14;

        // Transforms SOUTH WEST
        uniform mat4   u_rot_sw; 
        uniform mat4   u_trans_sw;   
        uniform mat4   u_projection_sw;
        uniform float  u_radial_offset_sw;
        uniform float  u_tangent_offset_sw;

        // Transforms SOUTH EAST
        uniform mat4   u_rot_se;
        uniform mat4   u_trans_se;
        uniform mat4   u_projection_se;
        uniform float  u_radial_offset_se;
        uniform float  u_tangent_offset_se;

        // Transforms NORTH EAST
        uniform mat4   u_rot_ne;
        uniform mat4   u_trans_ne;
        uniform mat4   u_projection_ne;
        uniform float  u_radial_offset_ne;
        uniform float  u_tangent_offset_ne;

        // Transforms NORTH WEST
        uniform mat4   u_rot_nw;
        uniform mat4   u_trans_nw;
        uniform mat4   u_projection_nw;
        uniform float  u_radial_offset_nw;
        uniform float  u_tangent_offset_nw;

        // Vertex attributes
        attribute vec3 a_cart_pos;      // Cartesian vertex position
        attribute vec2 a_sph_pos;       // Spherical vertex position
        attribute vec2 a_channel;       // Image channel id (1: SW, 2: SE, 3: NE, 4: NW)

        // Variables
        varying vec4 v_cart_pos_transformed;
        varying vec3   v_cart_pos;      // Cartesian vertex position
        varying vec2   v_sph_pos;       // Spherical vertex position

        vec4 channelPosition() {
            // SOUTH WEST
            if (a_channel == 1) {
                // First: non-linear projection
                vec4 pos =  u_projection_sw * u_trans_sw * u_rot_sw * vec4(a_cart_pos, 1.0);
                //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
                // Radial offset
                pos.xy -= u_radial_offset_sw * pos.w;
                // Rangential offset
                pos.x += u_tangent_offset_sw * pos.w;
                pos.y -= u_tangent_offset_sw * pos.w;
                // Last: return position for vertex
                return pos;
            }
            // SOUTH EAST
            else if (a_channel == 2) {
               // First: non-linear projection
                vec4 pos = u_projection_se * u_trans_se * u_rot_se * vec4(a_cart_pos, 1.0);
                //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
                // Radial offset
                pos.x += u_radial_offset_se * pos.w;
                pos.y -= u_radial_offset_se * pos.w;
                // Tangential offset
                pos.xy += u_tangent_offset_se * pos.w;
                // Last: return position for vertex
                return pos;
            }
            // NORTH EAST
            else if (a_channel == 3) {
               // First: non-linear projection
                vec4 pos = u_projection_ne * u_trans_ne * u_rot_ne * vec4(a_cart_pos, 1.0);
                //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
                // Radial offset
                pos.xy += u_radial_offset_ne * pos.w;
                // Tangential offset
                pos.x -= u_tangent_offset_ne * pos.w;
                pos.y += u_tangent_offset_ne * pos.w;
                // Last: return position for vertex
                return pos;
            }
            // NORTH WEST
            else if (a_channel == 4) {
               // First: non-linear projection
                vec4 pos = u_projection_nw * u_trans_nw * u_rot_nw * vec4(a_cart_pos, 1.0);
                //// Second: linear transformations in image plane (shifting/scaling/rotating 2d image)
                // Radial offset
                pos.x -= u_radial_offset_nw * pos.w;
                pos.y += u_radial_offset_nw * pos.w;
                // Tangential offset
                pos.xy -= u_tangent_offset_nw * pos.w;
                // Last: return position for vertex
                return pos;
            }
        }"""

    vertex_shader = """
        void main()
        {
          v_cart_pos = a_cart_pos;
          v_sph_pos = a_sph_pos;

          // Final position
          v_cart_pos_transformed = channelPosition();
          gl_Position = v_cart_pos_transformed;

          <viewport.transform>;
        }
    """

    fragment_shader = """
        const float pi = 3.14;

        varying vec3 v_cart_pos;
        varying vec2 v_sph_pos;

        void main()
        {
            <viewport.clipping>;

            // Checkerboard
            float c = sin(10.0 * v_sph_pos.x) * sin(8.0 * v_sph_pos.y);
            if (c > 0) {
               c = 1.0;
            } else {
                 c = 0.0;
            }

            // Final color
            gl_FragColor = vec4(c, c, c, 1.0);

        }
    """

    def __init__(self, _program):
        self.program = _program

        self.time = 0.0

    def _constructSphere(self):
        pass

    def draw(self, dt):
        """
        METHOD CAN BE RE-IMPLEMENTED
        :param dt: time since last call
        :return:
        """
        self.time += dt

        self.program.draw(gl.GL_TRIANGLES, self.indices)


class Checkerboard(Stimulus):

    fragment_shader = """
        const float pi = 3.14;

        varying vec3 v_cart_pos;
        varying vec2 v_sph_pos;

        void main()
        {
            <viewport.clipping>;

            // Checkerboard
            float c = sin(10.0 * v_sph_pos.x) * sin(8.0 * v_sph_pos.y);
            if (c > 0) {
               c = 1.0;
            } else {
                 c = 0.0;
            }

            // Final color
            gl_FragColor = vec4(c, c, c, 1.0);

        }
    """

    def __init__(self, _program):
        super().__init__(_program)

        if not(hasattr(self, 'constructSphere')):
            self._constructSphere()


    def draw(self, dt):