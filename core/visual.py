"""
MappApp ./process.py - Base stimulus classes which is inherited by
all stimulus implementations in ./stimulus/.
Copyright (C) 2020 Tim Hladnik, Yue Zhang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import numpy as np
import os
from vispy import gloo
from vispy.gloo import gl
from vispy.util import transforms

import Config
import Def
from utils import geometry,sphere
import Logging


################################
# Abstract visual class

class AbstractVisual:

    # Display shaders
    _vertex_display = """
        attribute vec2 a_position;
        varying vec2 v_texcoord;

        void main() {
            v_texcoord = 0.5 + a_position / 2.0;
            gl_Position = vec4(a_position, 0.0, 1.0);
        }
    """

    _frag_display = """
        varying vec2 v_texcoord;

        uniform sampler2D u_texture;

        void main() {
            gl_FragColor = texture2D(u_texture, v_texcoord);
        }
    """

    _vertex_map = """
    """

    _parse_fun_prefix = 'parse_'

    def __init__(self, canvas):
        self.frame_time = None
        self.canvas = canvas
        self._programs = dict()
        self.parameters = dict()
        self.transform_uniforms = dict()

        self._buffer_shape = self.canvas.physical_size[1], self.canvas.physical_size[0]
        self._out_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._out_fb = gloo.FrameBuffer(self._out_texture)
        self.frame = self._out_fb

        # Create display program: renders the out texture from FB to screen
        self.square = [[-1, -1], [-1, 1], [1, -1], [1, 1]]
        self._display_prog = gloo.Program(self._vertex_display, self._frag_display, count=4)
        self._display_prog['a_position'] = self.square
        self._display_prog['u_texture'] = self._out_texture

    def __setattr__(self, key, value):
        # Catch programs being set and add them to dictionary
        if not(hasattr(self, key)) and isinstance(value, gloo.Program):
            # TODO: maybe this can be done smarter
            self.__dict__[key] = value
            self.__dict__['_programs'][key] = value
        else:
            self.__dict__[key] = value

    def apply_transform(self, program):
        """Set uniforms in transform_uniforms on program"""
        for u_name, u_value in self.transform_uniforms.items():
            program[u_name] = u_value

    def draw(self, frame_time):
        raise NotImplementedError('Method draw() not implemented in {}'.format(self.__class__))

    def render(self, frame_time):
        raise NotImplementedError('Method render() not implemented in {}'.format(self.__class__))

    @staticmethod
    def load_shader(filepath):
        with open(os.path.join(Def.Path.Shader, filepath), 'r') as f:
            code = f.read()

        return code

    def load_vertex_shader(self, filepath):
        return self.parse_vertex_shader(self.load_shader(filepath))

    def parse_vertex_shader(self, vert):
        return f'{self._vertex_map}\n{vert}'

    def update(self, **params):
        """
        Method to update stimulus parameters.

        Is called by default to update stimulus parameters.
        May be reimplemented in subclass.
        """

        if not(bool(params)):
            return

        for key, value in params.items():
            if hasattr(self, f'{self._parse_fun_prefix}{key}'):
                value = getattr(self, f'{self._parse_fun_prefix}{key}')(value)
            self.parameters[key] = value

        Logging.write(Logging.INFO,
                      f'Update visual {self.__class__.__name__}. '
                      'Set ' + ' '.join([f'{key}: {value}' for key, value in self.parameters.items()]))

        for program_name, program in self._programs.items():
            for key, value in self.parameters.items():
                if key in program:
                    program[key] = value


################################
# Spherical stimulus class

class SphericalVisual(AbstractVisual):

    # Standard transforms of sphere for 4-way display configuration
    _vertex_map = """
        uniform mat2 u_mapcalib_aspectscale;
        uniform vec2 u_mapcalib_scale;
        uniform mat4 u_mapcalib_translation;
        uniform mat4 u_mapcalib_projection;
        uniform mat4 u_mapcalib_rotate_elev;
        uniform mat4 u_mapcalib_inv_rotate_elev;
        uniform mat4 u_mapcalib_rotate_z;
        uniform mat4 u_mapcalib_rotate_x;
        uniform vec2 u_mapcalib_translate2d;
        uniform mat2 u_mapcalib_rotate2d;

        attribute vec3 a_position;   // Vertex positions

        vec4 mapped_position()
        {
            // Final position
            vec4 pos = vec4(a_position, 1.0);
            
            // Azimuth rotation (here around z axis)
            pos = u_mapcalib_rotate_z * pos;
            
            // 90 degrees in x axis
            pos = u_mapcalib_rotate_x * pos;
                        
            // Change elevation (here around x axis)
            pos = u_mapcalib_rotate_elev * pos;
            
            // Translate along z
            pos = u_mapcalib_translation * pos;
            
            // Project
            pos = u_mapcalib_projection * pos;
            
            // 2D transforms (AFTER 3D projection!)
            pos = vec4(((u_mapcalib_rotate2d * pos.xy) * u_mapcalib_scale  + u_mapcalib_translate2d * pos.w) * u_mapcalib_aspectscale, pos.z, pos.w);
                
            return pos;
        }
    """

    _sphere_vert = """
        varying vec3 v_position;
        varying vec4 v_map_position;
        void main() {
            vec4 v_map_position = mapped_position();
            gl_Position = v_map_position;
            v_position = a_position;
        }
    """

    # Mask fragment shader
    _mask_frag = """
        varying vec3 v_position;
        varying vec4 v_map_position;
        void main() {
            gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
            //gl_FragColor = vec4(1.0-abs(v_position.z), abs(v_position.z)/2.0, 0.0, 1.0); 
            //gl_FragColor = vec4((-v_position.z+1.0)/2.0, (v_position.z+1.0)/2.0, 0.0, 1.0);
            //gl_FragColor = vec4(v_position.x, v_position.y, v_position.z, 1.0);
        }
    """

    # Out shaders
    _out_vert = """
        attribute vec2 a_position;
        varying vec2 v_texcoord;

        void main() {
            v_texcoord = 0.5 + a_position / 2.0;
            gl_Position = vec4(a_position, 0.0, 1.0);
        }
    """
    _out_frag = """
        varying vec2 v_texcoord;

        uniform sampler2D u_raw_texture;
        uniform sampler2D u_mask_texture;

        void main() {
            gl_FragColor = vec4(
              texture2D(u_raw_texture, v_texcoord).xyz 
              * texture2D(u_mask_texture, v_texcoord).x, 1.0);
        }
    """

    def __init__(self, *args):
        AbstractVisual.__init__(self, *args)


        # Create mask model
        self._mask_model = sphere.UVSphere(azim_lvls=50,
                                           elev_lvls=50,
                                           azimuth_range=np.pi / 2,
                                           upper_elev=np.pi / 4,
                                           radius=1.0)
        self._mask_position_buffer = gloo.VertexBuffer(self._mask_model.a_position)
        self._mask_index_buffer = gloo.IndexBuffer(self._mask_model.indices)

        # Set textures and FBs
        self._mask_texture = gloo.Texture2D(self._buffer_shape, format='luminance')
        self._mask_depth_buffer = gloo.RenderBuffer(self._buffer_shape)
        self._mask_fb = gloo.FrameBuffer(self._mask_texture, self._mask_depth_buffer)

        self._raw_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._raw_depth_buffer = gloo.RenderBuffer(self._buffer_shape)
        self._raw_fb = gloo.FrameBuffer(self._raw_texture, self._raw_depth_buffer)

        self._display_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._display_fb = gloo.FrameBuffer(self._display_texture)

        # Create mask program: renders binary mask of quarter-sphere to FB
        sphere_vert = self.parse_vertex_shader(self._sphere_vert)
        self._mask_program = gloo.Program(sphere_vert, self._mask_frag)
        self._mask_program['a_position'] = self._mask_position_buffer

        # Create out program: renders the output texture to FB
        # by combining raw and mask textures
        # (to be saved and re-rendered in display program)
        # square = [[-1, -1], [-1, 1], [1, -1], [1, 1]]
        self._out_prog = gloo.Program(self._out_vert, self._out_frag, count=4)
        self._out_prog['a_position'] = self.square
        self._out_prog['u_raw_texture'] = self._raw_texture
        self._out_prog['u_mask_texture'] = self._mask_texture

        # Set clear color
        #gloo.set_clear_color('black')
        #gloo.set_clear_color('red')

    def draw(self, frame_time):
        gloo.clear()

        self.frame_time = frame_time

        # Set 2D scaling for aspect 1
        width = Config.Display[Def.DisplayCfg.window_width]
        height = Config.Display[Def.DisplayCfg.window_height]
        if height > width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, width/height])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([height/width, 1])
        self.transform_uniforms['u_mapcalib_aspectscale'] = u_mapcalib_aspectscale

        # Set 3D transform
        distance = Config.Display[Def.DisplayCfg.sph_view_distance]
        #fov = 240.0/distance #
        fov = Config.Display[Def.DisplayCfg.sph_view_fov]

        # Set relative size
        self.transform_uniforms['u_mapcalib_scale'] = Config.Display[Def.DisplayCfg.sph_view_scale] * np.array([1, 1])
        #self.transform_uniforms['u_mapcalib_scale'] = Config.Display[Def.DisplayCfg.sph_view_scale] * np.array([1,1])

        #dist = 1.05 + frame_time / 300
        #print('Distance', dist)
        translate3d = transforms.translate((0, 0, -distance))
        self.transform_uniforms['u_mapcalib_translation'] = translate3d
        #project3d = transforms.perspective(fov, 1, 0.1, 200.0)
        #self.transform_uniforms['u_mapcalib_transform3d'] = translate3d @ project3d
        # fov = (frame_time * 10) % 90
        # print('FOV', fov)
        #print(project3d)
        project3d = transforms.perspective(fov, 1., 0.1, 400.0)
        #project3d = transforms.ortho(-2.0, 2.0, -2.0, 2.0, 0.1, 400.0)
        self.transform_uniforms['u_mapcalib_projection'] = project3d

        # Calculate inverse elevation for scaling of sphere into prolate spheroid
        inv_rotate_elev_3d = transforms.rotate(Config.Display[Def.DisplayCfg.sph_view_elev_angle], (1, 0, 0))
        # Calculate elevation rotation for projection
        rotate_elev_3d = transforms.rotate(-Config.Display[Def.DisplayCfg.sph_view_elev_angle], (1, 0, 0))

        # Make sure stencil testing is disabled and depth testing is enabled
        #gl.glDisable(gl.GL_STENCIL_TEST)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Clear raw stimulus buffer
        with self._raw_fb:
            gloo.clear()

        # Clear mask buffer
        with self._mask_fb:
            gloo.clear()

        for i in range(4):

            # Set spheroid transformation uniforms
            self.transform_uniforms['u_mapcalib_rotate_z'] = transforms.rotate(45, (0, 0, 1))
            self.transform_uniforms['u_mapcalib_rotate_x'] = transforms.rotate(90, (1, 0, 0))

            self.transform_uniforms['u_mapcalib_rotate_elev'] = rotate_elev_3d

            # 2D rotation around center of screen
            self.transform_uniforms['u_mapcalib_rotate2d'] = geometry.rotation2D(np.pi / 4 - np.pi / 2 * i)

            # 2D translation radially
            radial_offset = np.array([-np.real(1.j ** (.5 + i)), -np.imag(1.j ** (.5 + i))]) * Config.Display[Def.DisplayCfg.sph_pos_glob_radial_offset]
            xy_offset = np.array([Config.Display[Def.DisplayCfg.glob_x_pos], Config.Display[Def.DisplayCfg.glob_y_pos]])
            self.transform_uniforms['u_mapcalib_translate2d'] =  radial_offset + xy_offset

            # Render 90 degree mask to mask buffer
            # (BEFORE further 90deg rotation)
            self.apply_transform(self._mask_program)
            with self._mask_fb:
                self._mask_program.draw('triangles', self._mask_index_buffer)
            # Clear (important!)
            gloo.clear()

            # Apply 90*i degree rotation
            azim_angle = Config.Display[Def.DisplayCfg.sph_view_azim_angle]
            self.transform_uniforms['u_mapcalib_rotate_z'] = transforms.rotate(azim_angle + 90 * i, (0,0,1))

            # And render actual stimulus sphere
            with self._raw_fb:
                self.render(frame_time)

            # Clear (important!)
            gloo.clear()

            # Combine mask and raw texture into out_texture
            # (To optionally be saved to disk and rendered to screen)
            with self._out_fb:
                self._out_prog.draw('triangle_strip')

        self._display_prog.draw('triangle_strip')


################################
# Plane stimulus class

class PlanarVisual(AbstractVisual):

    def __init__(self, *args):
        AbstractVisual.__init__(self, *args)
        #gloo.set_clear_color('black')

    def draw(self, frame_time):
        gloo.clear()

        # Construct vertices
        height = Config.Display[Def.DisplayCfg.window_height]
        width = Config.Display[Def.DisplayCfg.window_width]

        # Set aspect scale to square
        if width > height:
            self.u_mapcalib_xscale = height/width
            self.u_mapcalib_yscale = 1.
        else:
            self.u_mapcalib_xscale = 1.
            self.u_mapcalib_yscale = width/height

        # Set 2d translation
        self.u_glob_x_position = Config.Display[Def.DisplayCfg.glob_x_pos]
        self.u_glob_y_position = Config.Display[Def.DisplayCfg.glob_y_pos]

        # Extents
        self.u_mapcalib_xextent = Config.Display[Def.DisplayCfg.pla_xextent]
        self.u_mapcalib_yextent = Config.Display[Def.DisplayCfg.pla_yextent]

        # Set real world size multiplier [mm]
        # (PlanarVisual's positions are normalized to the smaller side of the screen)
        self.u_small_side_size = Config.Display[Def.DisplayCfg.pla_small_side]

        # Set uniforms
        self.transform_uniforms['u_mapcalib_xscale'] = self.u_mapcalib_xscale
        self.transform_uniforms['u_mapcalib_yscale'] = self.u_mapcalib_yscale
        self.transform_uniforms['u_mapcalib_xextent'] = self.u_mapcalib_xextent
        self.transform_uniforms['u_mapcalib_yextent'] = self.u_mapcalib_yextent
        self.transform_uniforms['u_small_side_size'] = self.u_small_side_size
        self.transform_uniforms['u_glob_x_position'] = self.u_glob_x_position
        self.transform_uniforms['u_glob_y_position'] = self.u_glob_y_position

        # Call the rendering function of the subclass
        try:
            # Render to buffer
            with self._out_fb:
                self.render(frame_time)

            # Render to display
            self._display_prog.draw('triangle_strip')

        except Exception as exc:
            import traceback
            print(traceback.print_exc())
