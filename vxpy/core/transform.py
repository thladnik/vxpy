"""Core visual transform module
"""
from __future__ import annotations
from typing import Any, Callable, Dict, Type, Union

import numpy as np
from vispy import gloo
from vispy.gloo import gl
from vispy.util import transforms

from vxpy import calib
from vxpy import config
import vxpy.core.logger as vxlogger
from vxpy.utils import geometry, sphere


log = vxlogger.getLogger(__name__)


def get_config_transform():
    return get_transform(config.DISPLAY_TRANSFORM)


def get_transform(name: str) -> Union[Type[BaseTransform], None]:
    if name in globals():
        return globals()[name]

    log.error(f'Display transform {name} does not exist')


class BaseTransform:
    """BaseTransform class to be inherited by all visual transforms
    """

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

    vertex_map = """
    """

    def __init__(self):

        self.transform_uniforms: Dict[str, Any] = {}

        self._buffer_shape = (config.DISPLAY_WIN_SIZE_HEIGHT_PX, config.DISPLAY_WIN_SIZE_WIDTH_PX)
        self._out_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._out_fb = gloo.FrameBuffer(self._out_texture)
        self.frame = self._out_fb

        # Create display program: renders the out texture from FB to screen
        self.square = [[-1, -1], [-1, 1], [1, -1], [1, 1]]
        self._display_prog = gloo.Program(self._vertex_display, self._frag_display, count=4)
        self._display_prog['a_position'] = self.square
        self._display_prog['u_texture'] = self._out_texture

    def parse_vertex_shader(self, vert: str):
        return f'#version {config.DISPLAY_GL_VERSION}\n{self.vertex_map}\n{vert}'

    @staticmethod
    def parse_fragment_shader(frag: str):
        return f'#version {config.DISPLAY_GL_VERSION}\n{frag}'

    def apply_transforms_to_all(self, visual):
        for program in visual.get_programs().values():
            self.apply_transform(program)

    def apply_transform(self, program: gloo.Program):
        """Set uniforms in transform_uniforms on program"""
        for u_name, u_value in self.transform_uniforms.items():
            program[u_name] = u_value

    def apply(self, visual, dt: float):
        pass


class PerspectiveTransform(BaseTransform):

    vertex_map = """
    uniform mat4  u_model;
    uniform mat4  u_view;
    uniform mat4  u_projection;

    vec4 transform_position(vec3 position) {

        vec4 pos = vec4(position, 1.0);
        pos = u_projection * u_view * u_model * pos;

        return pos;
    }
    """

    def __init__(self):
        BaseTransform.__init__(self)

    def apply(self, visual, dt: float):
        gloo.clear()

        gl.glEnable(gl.GL_DEPTH_TEST)

        self.model = np.dot(transforms.rotate(-90, (1, 0, 0)), transforms.rotate(135, (0, 1, 0)))
        self.translate = 10.
        self.view = transforms.translate((0, 0, -self.translate))

        self.transform_uniforms['u_view'] = self.view
        self.transform_uniforms['u_model'] = self.model

        self.zoom()

        self.apply_transforms_to_all(visual)
        visual.render(dt)

    def zoom(self):
        gloo.set_viewport(0, 0, self.canvas.physical_size[0], self.canvas.physical_size[1])
        self.projection = transforms.perspective(25.0, self.canvas.size[0] / float(self.canvas.size[1]), 0.01, 1000.0)
        self.transform_uniforms['u_projection'] = self.projection


class OrthoTransform(BaseTransform):

    vertex_map = """
    uniform mat4  u_model;
    uniform mat4  u_view;
    uniform mat4  u_projection;

    vec4 transform_position(vec3 position) {

        vec4 pos = vec4(position, 1.0);
        pos = u_projection * u_view * u_model * pos;

        return pos;
    }
    """

    def __init__(self):
        BaseTransform.__init__(self)


class PlanarTransform(BaseTransform):

    vertex_map = """
    uniform float u_mapcalib_xscale;
    uniform float u_mapcalib_yscale;
    uniform float u_mapcalib_xextent;
    uniform float u_mapcalib_yextent;
    uniform float u_mapcalib_small_side_size;
    uniform float u_mapcalib_glob_x_position;
    uniform float u_mapcalib_glob_y_position;

    vec4 transform_position(vec3 position) {
        vec4 pos = vec4(position.x * u_mapcalib_xscale * u_mapcalib_xextent + u_mapcalib_glob_x_position,
                        position.y * u_mapcalib_yscale * u_mapcalib_yextent + u_mapcalib_glob_y_position,
                        position.z, 
                        1.0);
        return pos;
    }

    vec2 real_position(vec3 position) {
        vec2 pos = vec2(position.x / 2.0 * u_mapcalib_xextent * u_mapcalib_small_side_size,
                        position.y / 2.0 * u_mapcalib_yextent * u_mapcalib_small_side_size);
        return pos;
    }

    vec2 norm_position(vec3 position) {

        vec2 pos = vec2((1.0 + position.x) / 2.0,
                        (1.0 + position.y) / 2.0);
        return pos;
    }

    """

    def apply(self, visual, dt):

        gloo.clear()

        height = config.DISPLAY_WIN_SIZE_HEIGHT_PX
        width = config.DISPLAY_WIN_SIZE_WIDTH_PX

        # Set aspect scale to square
        if width > height:
            u_mapcalib_xscale = height / width
            u_mapcalib_yscale = 1.
        else:
            u_mapcalib_xscale = 1.
            u_mapcalib_yscale = width / height

        # Set 2d translation
        u_mapcalib_glob_x_position = calib.CALIB_DISP_GLOB_POS_X
        u_mapcalib_glob_y_position = calib.CALIB_DISP_GLOB_POS_Y

        # Extents
        u_mapcalib_xextent = calib.CALIB_DISP_PLA_EXTENT_X
        u_mapcalib_yextent = calib.CALIB_DISP_PLA_EXTENT_Y

        # Set real world size multiplier [mm]
        # (PlanarVisual's positions are normalized to the smaller side of the screen)
        u_mapcalib_small_side_size = calib.CALIB_DISP_PLA_SMALL_SIDE

        # Set uniforms
        self.transform_uniforms['u_mapcalib_xscale'] = u_mapcalib_xscale
        self.transform_uniforms['u_mapcalib_yscale'] = u_mapcalib_yscale
        self.transform_uniforms['u_mapcalib_xextent'] = u_mapcalib_xextent
        self.transform_uniforms['u_mapcalib_yextent'] = u_mapcalib_yextent
        self.transform_uniforms['u_mapcalib_small_side_size'] = u_mapcalib_small_side_size
        self.transform_uniforms['u_mapcalib_glob_x_position'] = u_mapcalib_glob_x_position
        self.transform_uniforms['u_mapcalib_glob_y_position'] = u_mapcalib_glob_y_position

        # Apply transforms to all programs of this visual
        self.apply_transforms_to_all(visual)

        # Call the rendering function of the subclass
        try:
            # Render to buffer
            with self._out_fb:
                visual.render(dt)

            # Render to display
            self._display_prog.draw('triangle_strip')

        except Exception as exc:
            import traceback
            print(traceback.print_exc())


class Spherical4ChannelProjectionTransform(BaseTransform):

    # Standard transforms of sphere for 4-way display configuration
    vertex_map = """
        uniform mat2 u_mapcalib_aspectscale;
        uniform vec2 u_mapcalib_scale;
        uniform mat4 u_mapcalib_translation;
        uniform mat4 u_mapcalib_projection;
        uniform mat4 u_mapcalib_rotate_elev;
        uniform mat4 u_mapcalib_rotate_z;
        uniform mat4 u_mapcalib_rotate_x;
        uniform vec2 u_mapcalib_translate2d;
        uniform mat2 u_mapcalib_rotate2d;
        uniform float u_mapcalib_lateral_luminance_offset;
        uniform float u_mapcalib_lateral_luminance_gradient;
        uniform float u_mapcalib_elevation_angle;
        uniform float u_mapcalib_azimuth_angle;


        vec4 transform_position(vec3 position) {
            // Final position
            vec4 pos = vec4(position, 1.0);

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

            // Flip direction for x (correct mirror inversion) 
            pos.x *= -1.;

            // 2D transforms (AFTER 3D projection!)
            pos = vec4(((u_mapcalib_rotate2d * pos.xy) * u_mapcalib_scale  + u_mapcalib_translate2d * pos.w) * u_mapcalib_aspectscale, pos.z, pos.w);

            return pos;
        }
    """

    _sphere_vert = """
        attribute vec3 a_position;

        varying vec3 v_position;
        varying vec4 v_map_position;
        //varying float v_dist_from_optical_axis;

        void main() {
            v_map_position = transform_position(a_position);
            gl_Position = v_map_position;
            v_position = a_position;

            // Calculate distance between original position 
            // and position after azimuth/elevation rotation
            //vec4 pos = u_mapcalib_rotate_z * vec4(a_position, 1.);
            //pos = u_mapcalib_rotate_elev * pos;
            //v_dist_from_optical_axis = distance(a_position, pos.xyz);

        }
    """

    # Mask fragment shader
    _mask_frag = """
        const float PI = 3.141592653589793;

        uniform int u_part;
        uniform float u_mapcalib_lateral_luminance_offset;
        uniform float u_mapcalib_lateral_luminance_gradient;
        uniform float u_mapcalib_elevation_angle;
        uniform float u_mapcalib_azimuth_angle;

        varying vec3 v_position;
        varying vec4 v_map_position;
        //varying float v_dist_from_optical_axis;


        vec3 sph2cart(in float azimuth, float elevation){
            return vec3(sin(azimuth) * cos(elevation),
                        cos(azimuth) * cos(elevation),
                        sin(elevation));
        }

        void main() {

            float offset = u_mapcalib_lateral_luminance_offset;
            float gradient = u_mapcalib_lateral_luminance_gradient;
            float azim = u_mapcalib_azimuth_angle / 180. * PI;
            float elev = u_mapcalib_elevation_angle / 180. * PI;
            vec3 optical_axis = sph2cart(azim, elev);        

            float dist_from_optical_axis = distance(v_position, optical_axis);

            gl_FragColor = vec4(1.0, 
                    offset + gradient * dist_from_optical_axis / 2., 
                    0.0, 
                    1.0);

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
        uniform int u_part;

        varying vec2 v_texcoord;

        uniform sampler2D u_raw_texture;
        uniform sampler2D u_mask_texture;
        uniform sampler2D u_out_texture;

        void main() {

            vec3 out_tex = texture2D(u_out_texture, v_texcoord).xyz;
            vec3 raw = texture2D(u_raw_texture, v_texcoord).xyz;
            vec2 mask = texture2D(u_mask_texture, v_texcoord).xy;

            if(mask.x > 0.0) {
                gl_FragColor = vec4(raw * mask.y, 1.0);
            } else {
                gl_FragColor = vec4(out_tex, 1.0);
            }

        }
    """

    def __init__(self):
        BaseTransform.__init__(self)
        # Create mask model

        self._mask_model = sphere.UVSphere(azim_lvls=50,
                                           elev_lvls=50,
                                           azimuth_range=np.pi / 2,
                                           upper_elev=np.pi / 4 + np.pi / 16,
                                           radius=1.0)
        self._mask_position_buffer = gloo.VertexBuffer(self._mask_model.a_position)
        self._mask_index_buffer = gloo.IndexBuffer(self._mask_model.indices)

        # Set textures and FBs
        self._mask_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
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
        self._out_prog['u_out_texture'] = self._out_texture

        # Set clear color
        #gloo.set_clear_color('black')
        #gloo.set_clear_color('red')

    def apply(self, visual, dt: float):

        gloo.clear()

        win_width = config.DISPLAY_WIN_SIZE_WIDTH_PX
        win_height = config.DISPLAY_WIN_SIZE_HEIGHT_PX
        # Set 2D scaling for aspect 1
        # Regular version
        # if win_height > win_width:
        #     u_mapcalib_aspectscale = np.eye(2) * np.array([1, win_width / win_height])
        # else:
        #     u_mapcalib_aspectscale = np.eye(2) * np.array([win_height / win_width, 1])

        # TODO: make this adjustable; maybe there needs to be a special "Lightcrafter_native_res" flag
        fixed_aspect = 800 / 1280
        if win_height < win_width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, fixed_aspect])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([fixed_aspect, 1])

        self.transform_uniforms['u_mapcalib_aspectscale'] = u_mapcalib_aspectscale
        self.transform_uniforms['u_mapcalib_lateral_luminance_offset'] = calib.CALIB_DISP_SPH_LAT_LUM_OFFSET
        self.transform_uniforms['u_mapcalib_lateral_luminance_gradient'] = calib.CALIB_DISP_SPH_LAT_LUM_GRADIENT

        # Make sure stencil testing is disabled and depth testing is enabled
        #gl.glDisable(gl.GL_STENCIL_TEST)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Clear raw stimulus buffer
        with self._raw_fb:
            gloo.clear()

        # Clear mask buffer
        with self._mask_fb:
            gloo.clear()

        with self._out_fb:
            gloo.clear()

        with self._display_fb:
            gloo.clear()

        azim_orientation = calib.CALIB_DISP_SPH_VIEW_AZIM_ORIENT
        for i in range(4):

            # Set 3D transform
            distance = calib.CALIB_DISP_SPH_VIEW_DISTANCE[i]
            fov = calib.CALIB_DISP_SPH_VIEW_FOV[i]
            view_scale = calib.CALIB_DISP_SPH_VIEW_SCALE[i]
            azim_angle = calib.CALIB_DISP_SPH_VIEW_AZIM_ANGLE[i]
            elev_angle = calib.CALIB_DISP_SPH_VIEW_ELEV_ANGLE[i]
            radial_offset_scalar = calib.CALIB_DISP_SPH_POS_RADIAL_OFFSET[i]
            lateral_offset_scalar = calib.CALIB_DISP_SPH_POS_LATERAL_OFFSET[i]

            # Set angles
            self.transform_uniforms['u_mapcalib_azimuth_angle'] = azim_angle + 45.
            self.transform_uniforms['u_mapcalib_elevation_angle'] = elev_angle

            # Set relative size
            self.transform_uniforms['u_mapcalib_scale'] = view_scale * np.array([1, 1])

            # 3D translation
            self.transform_uniforms['u_mapcalib_translation'] = transforms.translate((0, 0, -distance))

            # 3D projection
            self.transform_uniforms['u_mapcalib_projection'] = transforms.perspective(fov, 1., 0.1, 400.0)

            xy_offset = np.array([calib.CALIB_DISP_GLOB_POS_X * win_width / win_height,
                                  calib.CALIB_DISP_GLOB_POS_Y])

            self.transform_uniforms['u_mapcalib_rotate_x'] = transforms.rotate(90, (1, 0, 0))

            # 3D elevation rotation
            self.transform_uniforms['u_mapcalib_rotate_elev'] = transforms.rotate(-elev_angle, (1, 0, 0))

            # 2D rotation around center of screen
            self.transform_uniforms['u_mapcalib_rotate2d'] = geometry.rotation2D(np.pi / 4 - np.pi / 2 * i)

            # 2D translation radially
            radial_offset = np.array([-np.real(1.j ** (.5 + i)), -np.imag(1.j ** (.5 + i))]) * radial_offset_scalar
            sign = -1 if i % 2 == 0 else +1
            lateral_offset = np.array([sign * np.real(1.j ** (.5 + i)), sign * -1 * np.imag(1.j ** (.5 + i))]) * lateral_offset_scalar
            self.transform_uniforms['u_mapcalib_translate2d'] = radial_offset + xy_offset + lateral_offset

            # Render 90 degree mask to mask buffer
            # (BEFORE further 90deg rotation)
            self.transform_uniforms['u_mapcalib_rotate_z'] = transforms.rotate(45 + azim_angle, (0,0,1))
            self.apply_transform(self._mask_program)
            self._mask_program['u_part'] = i
            with self._mask_fb:
                self._mask_program.draw('triangles', self._mask_index_buffer)

            # Apply 90*i degree rotation to actual spherical stimulus
            self.transform_uniforms['u_mapcalib_rotate_z'] = transforms.rotate(azim_orientation + 90 * i + azim_angle, (0, 0, 1))

            # And render actual stimulus sphere
            with self._raw_fb:
                # Important: only provide dt on first iteration.
                # Otherwise the final cumulative time is going to be ~4*dt (too high!)
                self.apply_transforms_to_all(visual)
                visual.render(dt if i == 0 else 0.0)

            # Combine mask and raw texture into out_texture
            # (To optionally be saved to disk and rendered to screen)
            self._out_prog['u_part'] = i
            with self._out_fb:
                self._out_prog.draw('triangle_strip')

            with self._mask_fb:
                gloo.clear()

            with self._raw_fb:
                gloo.clear()

        self._display_prog.draw('triangle_strip')


class Spherical4ScreenCylindricalTransform(BaseTransform):

    vertex_map = """
        uniform mat4 u_mapcalib_model;
        uniform mat4 u_mapcalib_view;
        uniform mat4 u_mapcalib_projection;

        vec4 transform_position(vec3 position) {
            vec4 pos = u_mapcalib_projection * u_mapcalib_view * u_mapcalib_model * vec4(position, 1.0);

            return pos;
        }
    """

    def __init__(self):
        BaseTransform.__init__(self)
        # Create mask model

        self._display_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._display_fb = gloo.FrameBuffer(self._display_texture)

    def apply(self, visual, dt: float):

        gloo.clear()

        win_width = config.DISPLAY_WIN_SIZE_WIDTH_PX
        viewport_width = win_width // 4
        win_height = config.DISPLAY_WIN_SIZE_HEIGHT_PX

        side_width = calib.CALIB_DISP_CYL_SIDE_WIDTH_MM
        screen_width = calib.CALIB_DISP_CYL_SCREEN_WIDTH_MM
        screen_height = calib.CALIB_DISP_CYL_SCREEN_HEIGHT_MM

        azim_orientation = calib.CALIB_DISP_CYL_VIEW_AZIM_ORIENT

        # Calculate vertical field of view
        distance_to_center = side_width / 2
        fovy = 2 * np.arctan(screen_height / 2 / distance_to_center) / np.pi * 180

        gl.glEnable(gl.GL_DEPTH_TEST)

        gloo.clear()

        # with self._out_fb:
        for i in range(4):
            vp_start = i * viewport_width
            gloo.set_viewport(vp_start, 0, viewport_width, win_height)

            # Calculate rotation based on iteration
            view_rot = np.dot(transforms.rotate(i * 90 + azim_orientation, (0, 0, 1)), transforms.rotate(-90, (1, 0, 0)))
            # Calculate complete view
            view = np.dot(transforms.translate((0, 0, 0)), view_rot)

            # Calculate projection
            projection = transforms.perspective(fovy, screen_width/screen_height, 0.1, 10.0)
            # projection = transforms.perspective(fovy, viewport_width/win_height, 0.1, 10.0)

            self.transform_uniforms['u_mapcalib_model'] = np.eye(4, dtype=np.float32)
            self.transform_uniforms['u_mapcalib_view'] = view
            self.transform_uniforms['u_mapcalib_projection'] = projection

            self.apply_transforms_to_all(visual)
            visual.render(dt)

        # self._display_prog.draw('triangle_strip')
