"""
MappApp ./core/visual.py
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
from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
from numbers import Number
import sys

import numpy as np
from numpy.typing import DTypeLike
from typing import List, Tuple, Any, Union, Callable
from vispy import app
from vispy import gloo
from vispy.gloo import gl
from vispy.util import transforms

from vxpy import calib
from vxpy.definitions import *
from vxpy.core import logger
from vxpy.core import protocol
from vxpy.utils import geometry
from vxpy.utils import sphere

log = logger.getLogger(__name__)


def set_vispy_env():
    if sys.platform == 'win32':
        # app.use_app('PySide6')
        app.use_app('glfw')
        gloo.gl.use_gl('gl2')

    elif sys.platform == 'linux':
        app.use_app('glfw')
        gloo.gl.use_gl('gl2')


################################
# Abstract visual class

class AbstractVisual(ABC):
    description = ''

    interface = []

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

    def __init__(self, canvas=None, _protocol=None):
        if canvas is None:
            canvas = gloo.context.FakeCanvas()
        self.canvas: app.Canvas = canvas
        self.parameters: Dict[str, Any] = dict()
        self.custom_programs: Dict[str, gloo.Program] = dict()
        self.data_appendix: Dict[str, Any] = dict()
        self.transform_uniforms = dict()
        self.protocol: protocol.AbstractProtocol = _protocol

        self._buffer_shape = (calib.CALIB_DISP_WIN_SIZE_HEIGHT, calib.CALIB_DISP_WIN_SIZE_WIDTH)
        self._out_texture = gloo.Texture2D(self._buffer_shape + (3,), format='rgb')
        self._out_fb = gloo.FrameBuffer(self._out_texture)
        self.frame = self._out_fb

        # Create display program: renders the out texture from FB to screen
        self.square = [[-1, -1], [-1, 1], [1, -1], [1, 1]]
        self._display_prog = gloo.Program(self._vertex_display, self._frag_display, count=4)
        self._display_prog['a_position'] = self.square
        self._display_prog['u_texture'] = self._out_texture

        # Get all visual parameters
        self.static_parameters: List[Parameter] = []
        self.variable_parameters: List[Parameter] = []
        self.trigger_functions: List[Callable] = []
        self._collect_parameters()

        self.is_active = True

        gloo.set_state(depth_test=True)

    def __setattr__(self, key, value):
        # Catch programs being set and add them to dictionary (if they are not protected, i.e. default, programs)
        if not(hasattr(self, key)) and isinstance(value, gloo.Program) and not(key.startswith('_')):
            self.__dict__[key] = value
            self.__dict__['custom_programs'][key] = value
        else:
            self.__dict__[key] = value

    def _collect_parameters(self):
        """Function goes through all attributes within visual and collects anything derived from Parameter"""

        # Iterate through instance attributes
        for name in dir(self):

            param = getattr(self, name)

            # Skip anything that is not a parameter
            if not isinstance(param, Parameter):
                continue

            # Add to static or variable list
            if param.static:
                self.static_parameters.append(param)
            else:
                self.variable_parameters.append(param)

    def _add_data_appendix(self, name, data):
        """Deprecated thanks to static parameters?"""
        self.data_appendix[name] = data

    def apply_transform(self, program):
        """Set uniforms in transform_uniforms on program"""
        for u_name, u_value in self.transform_uniforms.items():
            program[u_name] = u_value

    @classmethod
    def load_shader(cls, filepath: str):
        if filepath.startswith('./'):
            # Use path relative to visual
            pyfileloc = inspect.getfile(cls)
            path = os.sep.join([*pyfileloc.split(os.sep)[:-1], filepath[2:]])
        else:
            # Use absolute path to global shader folder
            path = os.path.join(PATH_SHADERS, filepath)

        with open(path, 'r') as f:
            code = f.read()

        return code

    def load_vertex_shader(self, filepath):
        return self.parse_vertex_shader(self.load_shader(filepath))

    def parse_vertex_shader(self, vert):
        return f'{self._vertex_map}\n{vert}'

    def trigger(self, trigger_fun: Union[Callable, str]):
        name = trigger_fun.__name__ if callable(trigger_fun) else trigger_fun
        getattr(self, name)()

    def start(self):
        self.is_active = True

    def end(self):
        # controller_rpc(end_protocol_phase)
        self.is_active = False

    def update(self, params: dict, _update_verbosely=True):
        """Update parameters of the visual

        Is called by default to update stimulus parameters.
        May be reimplemented in subclass.
        """

        if not(bool(params)):
            return

        msg_params = []
        for key, value in params.items():
            if hasattr(value, '__iter__'):
                if isinstance(value, np.ndarray):
                    msg_val = f'Array{value.shape}'
                elif isinstance(value, list):
                    msg_val = f'List({len(value)})'
                elif isinstance(value, tuple):
                    msg_val = f'Tuple({len(value)})'
                else:
                    msg_val = value
            else:
                msg_val = value

            msg_params.append(f'{key}: {msg_val}')

        msg = f'Update parameters for visual {self.__class__.__name__}: {", ".join(msg_params)}'

        if _update_verbosely:
            # (optional) Logging
            log.info(msg)
        else:
            log.debug(msg)

        for key, value in params.items():
            getattr(self, str(key)).data = value

    @abstractmethod
    def initialize(self, **kwargs):
        """Method to initialize and reset all parameters."""

    @abstractmethod
    def draw(self, dt):
        """Method to be implemented by BaseVisual class (BaseVisual, SphericalVisual, PlanarVisual, ...)."""

    @abstractmethod
    def render(self, dt):
        """Method to be implemented in final visual."""


class BaseVisual(AbstractVisual, ABC):

    _vertex_map = """
    uniform mat4  u_model;
    uniform mat4  u_view;
    uniform mat4  u_projection;
    
    vec4 transform_position(vec3 position) {
    
        vec4 pos = vec4(position, 1.0);
        pos = u_projection * u_view * u_model * pos;
        
        return pos;
    }
    """

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)

    def draw(self, dt):
        gloo.clear()
        if not self.is_active:
            return

        self.model = np.dot(transforms.rotate(-90, (1, 0, 0)), transforms.rotate(90, (0, 1, 0)))
        self.translate = 2
        self.view = transforms.translate((0, 0, -self.translate))

        self.transform_uniforms['u_view'] = self.view
        self.transform_uniforms['u_model'] = self.model

        self.apply_zoom()

        self.render(dt)

    def apply_zoom(self):
        gloo.set_viewport(0, 0, self.canvas.physical_size[0], self.canvas.physical_size[1])
        self.projection = transforms.perspective(90.0, self.canvas.size[0] / float(self.canvas.size[1]), 1.0, 1000.0)
        self.transform_uniforms['u_projection'] = self.projection


################################
# Spherical stimulus class

class SphericalVisual(AbstractVisual, ABC):
    # TODO:
    #  There is currently a bug when using GLFW, that causes all spherical visuals to disappear
    #  This always happens when the window's y-position is increased over 0
    #  At y-pos = 1, only the lower two quadrants are visible and over 1 it disappears completely

    # Standard transforms of sphere for 4-way display configuration
    _vertex_map = """
        #version 460

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

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)

        # Create mask model
        self._mask_model = sphere.UVSphere(azim_lvls=50,
                                           elev_lvls=50,
                                           azimuth_range=np.pi / 2,
                                           upper_elev=np.pi / 4,
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

    def _draw(self, dt):

        self.frame_time = dt

        win_width = calib.CALIB_DISP_WIN_SIZE_WIDTH
        win_height = calib.CALIB_DISP_WIN_SIZE_HEIGHT
        # Set 2D scaling for aspect 1
        if win_height > win_width:
            u_mapcalib_aspectscale = np.eye(2) * np.array([1, win_width / win_height])
        else:
            u_mapcalib_aspectscale = np.eye(2) * np.array([win_height / win_width, 1])
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
                self.render(dt if i == 0 else 0.0)

            # Combine mask and raw texture into out_texture
            # (To optionally be saved to disk and rendered to screen)
            self._out_prog['u_part'] = i
            with self._out_fb:
                self._out_prog.draw('triangle_strip')

            with self._mask_fb:
                gloo.clear()

            with self._raw_fb:
                gloo.clear()

    def draw(self, dt):
        gloo.clear()
        if self.is_active:
            self._draw(dt)

        self._display_prog.draw('triangle_strip')

        return True


################################
# Plane stimulus class

class PlanarVisual(AbstractVisual, ABC):

    _vertex_map = """
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
        //vec2 pos = vec2((1.0 + position.x) / 2.0 * u_mapcalib_xextent * u_mapcalib_small_side_size,
        //                (1.0 + position.y) / 2.0 * u_mapcalib_yextent * u_mapcalib_small_side_size);
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

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)

    def draw(self, dt):
        if self.is_active:
            gloo.clear()
            self._draw(dt)

    def _draw(self, dt):

        height = calib.CALIB_DISP_WIN_SIZE_HEIGHT
        width = calib.CALIB_DISP_WIN_SIZE_WIDTH

        # Set aspect scale to square
        if width > height:
            self.u_mapcalib_xscale = height/width
            self.u_mapcalib_yscale = 1.
        else:
            self.u_mapcalib_xscale = 1.
            self.u_mapcalib_yscale = width/height

        # Set 2d translation
        self.u_mapcalib_glob_x_position = calib.CALIB_DISP_GLOB_POS_X
        self.u_mapcalib_glob_y_position = calib.CALIB_DISP_GLOB_POS_Y

        # Extents
        self.u_mapcalib_xextent = calib.CALIB_DISP_PLA_EXTENT_X
        self.u_mapcalib_yextent = calib.CALIB_DISP_PLA_EXTENT_Y

        # Set real world size multiplier [mm]
        # (PlanarVisual's positions are normalized to the smaller side of the screen)
        self.u_mapcalib_small_side_size = calib.CALIB_DISP_PLA_SMALL_SIDE

        # Set uniforms
        self.transform_uniforms['u_mapcalib_xscale'] = self.u_mapcalib_xscale
        self.transform_uniforms['u_mapcalib_yscale'] = self.u_mapcalib_yscale
        self.transform_uniforms['u_mapcalib_xextent'] = self.u_mapcalib_xextent
        self.transform_uniforms['u_mapcalib_yextent'] = self.u_mapcalib_yextent
        self.transform_uniforms['u_mapcalib_small_side_size'] = self.u_mapcalib_small_side_size
        self.transform_uniforms['u_mapcalib_glob_x_position'] = self.u_mapcalib_glob_x_position
        self.transform_uniforms['u_mapcalib_glob_y_position'] = self.u_mapcalib_glob_y_position

        # Call the rendering function of the subclass
        try:
            # Render to buffer
            with self._out_fb:
                self.render(dt)

            # Render to display
            self._display_prog.draw('triangle_strip')

        except Exception as exc:
            import traceback
            print(traceback.print_exc())


class PlainVisual(AbstractVisual, ABC):

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)

    def draw(self, dt):
        self.render(dt)


# Special visuals

class KeepLast(PlainVisual):

    def __init__(self, *args, **kwargs):
        PlainVisual.__init__(self, *args, **kwargs)

    def initialize(self, *args, **kwargs):
        pass

    def render(self, frame_time):
        pass


class Parameter:
    dtype: DTypeLike = None
    limits: Tuple[Number, Number] = None
    default: Any = None
    step_size: Number = None

    def __init__(self, name: str,
                 shape: Tuple[int, ...] = None,
                 static: bool = False,
                 value_map: Union[dict, Callable] = None,
                 internal: bool = False,
                 default: Any = None,
                 limits: Tuple[Number, Number] = None,
                 step_size: Number = None):

        self._name: str = name
        self._programs: List[gloo.Program] = []
        self._downstream_link: List[Parameter] = []

        if shape is not None:
            self._data: np.ndarray = np.zeros(shape, dtype=self.dtype)
        else:
            self._data = None

        self._static = static

        if value_map is None:
            value_map = {}
        self.value_map = value_map

        self.internal = internal
        self.default = default
        self.limits = limits
        self.step_size = step_size

    def __repr__(self):
        return self.name

    def __add__(self, other):
        self.data = self.data + other

    @property
    def static(self):
        return self._static

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        pass

    def _set_start_data(self, data):
        self._data = np.array(data, dtype=self.dtype)

    @property
    def data(self):
        return self._data[:]

    @data.setter
    def data(self, data):
        if self._data is None:
            self._set_start_data(data)

        # If value_map is a callable, use it to transform data
        if callable(self.value_map):
            data = self.value_map(data)

        # If a value_map is a dictionary and contains "data" as key, use the mapped value from dictionary
        else:
            if bool(self.value_map) and data.__hash__ is not None:
                value = self.value_map.get(data)

                # Set data to value
                if value is not None:
                    data = value

                # If the mapped value is a callable, call it and use return value instead
                if callable(data):
                    data = data()

        self._data[:] = data
        self.update()

    def connect(self, program: gloo.Program):
        if program not in self._programs:
            self._programs.append(program)
            self.update()

    def remove_downstream_links(self):
        self._downstream_link = []

    def add_downstream_link(self, parameter: Parameter):
        if parameter not in self._downstream_link:
            self._downstream_link.append(parameter)

    def update(self):
        for program in self._programs:
            if self.name in program:
                program[self.name] = self.data
                # try:
                #     print(self.name, self.data)
                #     program[self.name][:] = self.data
                # except:
                #     program[self.name] = self.data

        for parameter in self._downstream_link:
            parameter.upstream_updated()

    def upstream_updated(self):
        pass


# Bool types

class BoolParameter(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class BoolVec2Parameter(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class BoolVec3Parameter(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class BoolVec4Parameter(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Int types

class IntParameter(Parameter):
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class IntVec2Parameter(Parameter):
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class IntVec3Parameter(Parameter):
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class IntVec4Parameter(Parameter):
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# UInt types

class UIntParameter(Parameter):
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class UIntVec2Parameter(Parameter):
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class UIntVec3Parameter(Parameter):
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class UIntVec4Parameter(Parameter):
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Float types

class FloatParameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class Vec2Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class Vec3Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class Vec4Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Double types

class DoubleParameter(Parameter):
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)


class DoubleVec2Parameter(Parameter):
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class DoubleVec3Parameter(Parameter):
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class DoubleVec4Parameter(Parameter):
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Matrix types

class MatNxMParameter(Parameter):
    """Requires shape = (N, M) keyword argument."""

    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)


class Mat2Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(2, 2), **kwargs)


class Mat3Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(3, 3), **kwargs)


class Mat4Parameter(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, shape=(4, 4), **kwargs)


# Textures

class Texture(Parameter):
    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)


class Texture1D(Texture):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)


class TextureInt1D(Texture):
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)


class TextureUInt1D(Texture):
    dtype = np.uint8

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)


class Texture2D(Texture):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)

    # def _set_start_data(self, data):
    #     self._data = gloo.Texture2D(np.ascontiguousarray(data, dtype=self.dtype))


class TextureInt2D(Texture):
    dtype = np.int16

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)


class TextureUInt2D(Texture):
    dtype = np.uint8

    def __init__(self, *args, **kwargs):
        Texture.__init__(self, *args, **kwargs)


class Attribute(Parameter):
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)
        self._buffer_data_contents = None

    def _set_start_data(self, data):
        self._data = gloo.VertexBuffer(np.ascontiguousarray(data, dtype=self.dtype))


class BoolAttribute(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)
