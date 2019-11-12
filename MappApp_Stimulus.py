from glumpy import app, gl, glm, gloo, transforms
import h5py
import imageio
import numpy as np
import os
from scipy.spatial import Delaunay

import MappApp_Geometry as mageo

class Stimulus:
    base_vertex_shader = """
        const float pi = 3.14159265359;

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

        vec4 channelTransform() {
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
        }
    """

    vertex_shader = """
        void main()
        {
          v_cart_pos = a_cart_pos;
          v_sph_pos = a_sph_pos;

          // Final position
          v_cart_pos_transformed = channelTransform();
          gl_Position = v_cart_pos_transformed;

          <viewport.transform>;
        }
    """

    base_fragment_shader = """
    
        const float pi = 3.14159265359;

        varying vec3 v_cart_pos;
        varying vec2 v_sph_pos;
    """

    fragment_shader = """

        void main()
        {
            <viewport.clipping>;

            // Final color
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);

        }
    """

    def __init__(self, _useUV=True):

        self.program = None
        self.sphere = mageo.Sphere()
        self.time = 0.0

        ## Set up program
        self._setupProgram()

        ## Construct sphere
        if not(hasattr(self, 'constructSphere')):
            self._constructSphere(_useUV=_useUV)
        else:
            getattr(self, 'constructSphere')()


    def getVertexShader(self):
        return self.base_vertex_shader + self._constructShader('vertex_shader')

    def getFragmentShader(self):
        return self.base_fragment_shader + self.fragment_shader

    def _setupProgram(self):
        self.program = gloo.Program(vertex=self.getVertexShader(), fragment=self.getFragmentShader())

    def _constructSphere(self, _useUV):
        if _useUV:
            self.sphere = mageo.UVSphere(theta_lvls=80, phi_lvls=40)
        else:
            self.sphere = mageo.IcosahedronSphere(subdiv_lvl=5)

        self._prepareChannels(_useUV=_useUV)

        ## CREATE PROGRAM
        self.program.bind(self.vertexBuffer)
        self.program['viewport'] = transforms.Viewport()

    def _constructShader(self, shader):
        shader_program = getattr(self, shader)

        if isinstance(shader_program, str):
            return shader_program
        elif isinstance(shader_program, list):
            try:
                with open(os.path.join(*shader_program), 'r') as fobj:
                    return fobj.read()
            except:
                raise Exception('Invalid shader path %s' % os.path.join(*shader_program))
        else:
            # TODO: eventually add option to dynamically construct shader from a Shader class
            pass

    def _prepareChannels(self, _useUV):
        """
        This method separates the sphere into 4 different channels, according to their azimuth.
        This step is crucial for the actual projection and MappApp requires each vertex to be assigned
        a channel ID between 1 nad 4 (1: SW, 2: SE, 3: NE, 4: NW). Vertices that do NOT have a channel ID
        will be disregarded during rendering.

        In principle this method can be re-implemented in any custom stimulus class, so long as it
        specifies the vertex attributes 'a_cart_pos', 'a_sph_pos' and 'a_channel'.
        :param _useUV:
        :return:
        """

        if _useUV:
            all_verts = self.sphere.getVertices()
            all_sph_pos = self.sphere.getSphericalCoords()

            orientations = ['sw', 'se', 'ne', 'nw']
            verts = dict()
            faces = dict()
            sph_pos = dict()
            channel = dict()
            for i, orient in enumerate(orientations):
                theta_center = -3 * np.pi / 4 + i * np.pi / 2
                vert_mask = mageo.SphereHelper.getAzElLimitedMask(theta_center - np.pi / 4, theta_center + np.pi / 4,
                                                            -np.inf, np.inf, all_verts)

                verts[orient] = all_verts[vert_mask]
                sph_pos[orient] = all_sph_pos[vert_mask]
                channel[orient] = (i + 1) * np.ones((verts[orient].shape[0], 2))
                faces[orient] = Delaunay(verts[orient]).convex_hull

            ## CREATE BUFFERS
            v = np.concatenate([verts[orient] for orient in orientations], axis=0)
            # Vertex buffer
            self.vertexBuffer = np.zeros(v.shape[0],
                                         [('a_cart_pos', np.float32, 3),
                                 ('a_sph_pos', np.float32, 2),
                                 ('a_channel', np.float32, 2)])
            self.vertexBuffer['a_cart_pos'] = v.astype(np.float32)
            self.vertexBuffer['a_sph_pos'] = np.concatenate([sph_pos[orient] for orient in orientations], axis=0).astype(np.float32)
            self.vertexBuffer['a_channel'] = np.concatenate([channel[orient] for orient in orientations], axis=0).astype(np.float32)
            self.vertexBuffer = self.vertexBuffer.view(gloo.VertexBuffer)
            # Index buffer
            self.indexBuffer = np.zeros((0, 3))
            startidx = 0
            for orient in orientations:
                self.indexBuffer = np.concatenate([self.indexBuffer, startidx + faces[orient]], axis=0)
                startidx += verts[orient].shape[0]
            self.indexBuffer = self.indexBuffer.astype(np.uint32).view(gloo.IndexBuffer)


    def draw(self, dt):
        """
        METHOD CAN BE RE-IMPLEMENTED.

        By default this method uses the indexBuffer object to draw GL_TRIANGLES.

        :param dt: time since last call
        :return:
        """
        self.time += dt

        self.program.draw(gl.GL_TRIANGLES, self.indexBuffer)

    def update(self, *args, **kwargs):
        """
        Method has to be re-implemented in child class
        """
        print('WARNING: update method not implemented for stimulus!')
        pass


class Checkerboard(Stimulus):

    fragment_shader = """
        uniform int u_checker_rows;
        uniform int u_checker_cols;
        
        void main()
        {
            <viewport.clipping>;

            // Checkerboard
            float c = sin(float(u_checker_cols) * v_sph_pos.x) * sin(float(u_checker_rows) * v_sph_pos.y);
            if (c > 0) {
               c = 1.0;
            } else {
                 c = 0.0;
            }

            // Final color
            gl_FragColor = vec4(c, c, c, 1.0);

        }
    """

    def __init__(self, rows, cols):
        super().__init__()

        self.program['u_checker_rows'] = rows
        self.program['u_checker_cols'] = cols

    def update(self, cols=None, rows=None):

        if cols is not None and cols > 0:
            self.program['u_checker_cols'] = cols

        if rows is not None and rows > 0:
            self.program['u_checker_rows'] = rows
