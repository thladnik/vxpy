"""Core visual module.

Defines the abstract visual hierarchy (:class:`AbstractVisual`,
:class:`SphericalVisual`, :class:`PlanarVisual`, :class:`PlainVisual`) and
the :class:`Parameter` system used to expose typed, shader-connected stimulus
parameters.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
from numbers import Number
import sys

import numpy as np
from numpy.typing import DTypeLike
from typing import List, Tuple, Any, Union, Callable, Dict, Type
from vispy import app
from vispy import gloo
from vispy.gloo import gl
from vispy.util import transforms

from vxpy import calib
from vxpy.definitions import *
from vxpy.core import logger
from vxpy.core import protocol
import vxpy.core.event as vxevent
import vxpy.core.transform as vxtransforms

log = logger.getLogger(__name__)


def set_vispy_env():
    """Set vispy env.
    """
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
    """AbstractVisual class."""

    available_transforms: Dict[str, vxtransforms.BaseTransform] = {}
    transform: vxtransforms.BaseTransform = None

    static_parameters: List[Parameter]
    variable_parameters: List[Parameter]
    trigger_functions: List[Callable]

    instance: Type[AbstractVisual] = None

    def __init__(self, canvas=None, _protocol=None, _transform=None):
        # Set instance
        """  init  .
        
        Parameters
        ----------
        canvas : app.Canvas
            Target canvas used to create GPU resources for this visual.
        _protocol : protocol.BaseProtocol
            Protocol instance that owns this visual.
        _transform : vxtransforms.BaseTransform
            Display transform used to map rendered geometry to the output setup.
        """
        AbstractVisual.instance = self

        if canvas is None:
            canvas = gloo.context.FakeCanvas()
        self.canvas: app.Canvas = canvas

        if _protocol is None:
            _protocol = protocol.BaseProtocol()
        self.protocol: protocol.BaseProtocol = _protocol

        if _transform is None:
            _transform = vxtransforms.get_config_transform()()
        self.transform = _transform

        self.parameters: Dict[str, Any] = {}
        self.custom_programs: Dict[str, gloo.Program] = {}
        self.data_appendix: Dict[str, Any] = {}

        # Get all visual parameters
        self.collect_parameters()

        # Set inactive
        self.is_active = False

        gloo.set_state(depth_test=True)

    def __setattr__(self, key, value):
        # Catch programs being set and add them to dictionary (if they are not protected, i.e. default, programs)
        """  setattr  .
        
        Parameters
        ----------
        key : Any
            Attribute name being assigned.
        value : Any
            Attribute value; custom ``gloo.Program`` values are tracked automatically.
        """
        if not(hasattr(self, key)) and isinstance(value, gloo.Program) and not(key.startswith('_')):
            self.__dict__[key] = value
            self.__dict__['custom_programs'][key] = value
        else:
            self.__dict__[key] = value

    def get_programs(self) -> Dict[str, gloo.Program]:
        """Get programs.
        
        Returns
        -------
        Dict[str, gloo.Program]
            Mapping of custom program attribute names to program objects.
        """
        return self.custom_programs

    @classmethod
    def collect_parameters(cls):
        """Collect parameters.
        """
        cls.static_parameters = []
        cls.variable_parameters = []
        cls.trigger_functions = []

        # Iterate through instance attributes
        for name in dir(cls):

            param = getattr(cls, name)

            # Skip anything that is not a parameter
            if not isinstance(param, Parameter):
                continue

            # Add to static or variable list
            if param.static:
                cls.static_parameters.append(param)
            else:
                cls.variable_parameters.append(param)

    def _add_data_appendix(self, name, data):
        """ add data appendix.
        
        Parameters
        ----------
        name : Any
            Key under which supplemental output data is stored.
        data : Any
            Supplemental data payload associated with the current frame/update.
        """
        self.data_appendix[name] = data

    @classmethod
    def load_shader(cls, filepath: str):
        """Load shader.
        
        Parameters
        ----------
        filepath : str
            Relative shader path (from visual module) or absolute shader name under ``PATH_SHADERS``.
        """
        if not filepath.startswith('/') or filepath.startswith('\\'):
            # Use path relative to visual
            pyfileloc = inspect.getfile(cls)
            filepath_clean = filepath.replace('./', '')
            path = os.sep.join([*pyfileloc.split(os.sep)[:-1], filepath_clean])
        else:
            # Use absolute path to global shader folder
            path = os.path.join(PATH_SHADERS, filepath)

        log.debug(f'Load shader from {path}')
        with open(path, 'r') as f:
            code = f.read()

        return code

    def load_vertex_shader(self, filepath: str):
        """Load vertex shader.
        
        Parameters
        ----------
        filepath : str
            Vertex shader file path forwarded to :meth:`load_shader`.
        """
        log.debug(f'Load vertex shader from {filepath}')
        return self.parse_vertex_shader(self.load_shader(filepath))

    def parse_vertex_shader(self, vert: str):
        """Parse vertex shader.
        
        Parameters
        ----------
        vert : str
            Raw vertex shader source to be transformed for the active display mapping.
        """
        log.debug('Parse vertex shader')
        return self.transform.parse_vertex_shader(vert)

    def trigger(self, trigger_fun: Union[Callable, str]):
        """Trigger.
        
        Parameters
        ----------
        trigger_fun : Union[Callable, str]
            Trigger function object or name to invoke on this visual.
        """
        name = trigger_fun.__name__ if callable(trigger_fun) else trigger_fun
        getattr(self, name)()

    def start(self):
        """Start.
        """
        for attr in self.__dict__.values():
            if issubclass(type(attr), vxevent.Trigger):
                attr.set_active()
        self.is_active = True

    def end(self):
        """End.
        """
        for attr in self.__dict__.values():
            if issubclass(type(attr), vxevent.Trigger):
                attr.set_inactive()
        self.is_active = False
        self.destroy()

    def update(self, params: dict, _update_verbosely=True):
        """Update.
        
        Parameters
        ----------
        params : dict
            Mapping of parameter names to new values.
        _update_verbosely : Any
            If truthy, log updates at info level instead of debug level.
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

    def apply_transform(self, *args, **kwargs):
        """Apply transform.
        
        Parameters
        ----------
        *args : Any
            Transform-specific positional arguments.
        **kwargs : Any
            Transform-specific keyword arguments.
        """
        pass

    @abstractmethod
    def initialize(self, **kwargs):
        """Initialize.
        
        Parameters
        ----------
        **kwargs : Any
            Visual-specific initialization options.
        """

    @abstractmethod
    def render(self, dt):
        """Render.
        
        Parameters
        ----------
        dt : Any
            Elapsed time since the previous render call.
        """

    def destroy(self):
        """Destroy.
        """


class SphericalVisual(AbstractVisual, ABC):
    """SphericalVisual class."""

    available_transforms = [vxtransforms.PerspectiveTransform,
                            vxtransforms.Spherical4ChannelProjectionTransform,
                            vxtransforms.Spherical4ScreenCylindricalTransform,
                            vxtransforms.Spherical2ScreenCylindricalTransform]

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`AbstractVisual`.
        **kwargs : Any
            Forwarded to :class:`AbstractVisual`.
        """
        AbstractVisual.__init__(self, *args, **kwargs)


class PlanarVisual(AbstractVisual, ABC):
    """PlanarVisual class."""

    available_transforms = [vxtransforms.PlanarTransform]

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`AbstractVisual`.
        **kwargs : Any
            Forwarded to :class:`AbstractVisual`.
        """
        AbstractVisual.__init__(self, *args, **kwargs)


class PlainVisual(AbstractVisual, ABC):
    """PlainVisual class."""

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`AbstractVisual`.
        **kwargs : Any
            Forwarded to :class:`AbstractVisual`.
        """
        AbstractVisual.__init__(self, *args, **kwargs)

    def draw(self, dt):
        """Draw.
        
        Parameters
        ----------
        dt : Any
            Elapsed time forwarded to :meth:`render`.
        """
        self.render(dt)


# Special visuals

class KeepLast(PlainVisual):
    """KeepLast class."""

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Forwarded to :class:`PlainVisual`.
        **kwargs : Any
            Forwarded to :class:`PlainVisual`.
        """
        PlainVisual.__init__(self, *args, **kwargs)

    def initialize(self, *args, **kwargs):
        """Initialize.
        
        Parameters
        ----------
        *args : Any
            Unused positional arguments accepted for interface compatibility.
        **kwargs : Any
            Unused keyword arguments accepted for interface compatibility.
        """
        pass

    def render(self, frame_time):
        """Render.
        
        Parameters
        ----------
        frame_time : Any
            Elapsed frame time (unused because this visual keeps the previous frame).
        """
        pass


class Parameter:
    """Parameter class."""

    dtype: DTypeLike = None
    limits: Tuple[Number, Number] = None
    default: Any = None
    step_size: Number = None

    def __init__(self, name: str,
                 shape: Tuple[int, ...] = None,
                 dtype: Type = None,
                 static: bool = False,
                 value_map: Union[dict, Callable] = None,
                 internal: bool = False,
                 default: Any = None,
                 limits: Tuple[Number, Number] = None,
                 step_size: Number = None):

        """  init  .
        
        Parameters
        ----------
        name : str
            Description.
        shape : Tuple[int, ...]
            Description.
        dtype : Type
            Description.
        static : bool
            Description.
        value_map : Union[dict, Callable]
            Description.
        internal : bool
            Description.
        default : Any
            Description.
        limits : Tuple[Number, Number]
            Description.
        step_size : Number
            Description.
        """
        self._name: str = name
        self._programs: List[gloo.Program] = []
        self._downstream_link: List[Parameter] = []

        if dtype is not None:
            self.dtype = dtype
        self._shape = shape
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
        """  repr  .
        """
        return self.name

    def __add__(self, other):
        """  add  .
        
        Parameters
        ----------
        other : Any
            Description.
        """
        self.data = self.data + other

    @property
    def shape(self):
        """Shape.
        """
        return self._shape

    @property
    def static(self):
        """Static.
        """
        return self._static

    @property
    def name(self):
        """Name.
        """
        return self._name

    @name.setter
    def name(self, value):
        """Name.
        
        Parameters
        ----------
        value : Any
            Description.
        """
        pass

    def _set_start_data(self, data):
        """ set start data.
        
        Parameters
        ----------
        data : Any
            Description.
        """
        self._shape = data.shape if hasattr(data, 'shape') else (1,)
        self._data = np.array(data, dtype=self.dtype)

    @property
    def data(self):
        """Data.
        """
        return self._data[:]

    @data.setter
    def data(self, data):
        """Data.
        
        Parameters
        ----------
        data : Any
            Description.
        """
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
        """Connect.
        
        Parameters
        ----------
        program : gloo.Program
            Description.
        """
        if program not in self._programs:
            self._programs.append(program)
            self.update()

    def remove_downstream_links(self):
        """Remove downstream links.
        """
        self._downstream_link = []

    def add_downstream_link(self, parameter: 'Parameter'):
        """Add downstream link.
        
        Parameters
        ----------
        parameter : 'Parameter'
            Description.
        """
        if parameter not in self._downstream_link:
            self._downstream_link.append(parameter)

    def update(self):
        """Update.
        """
        for program in self._programs:
            if self.name in program:
                program[self.name] = self.data

        for parameter in self._downstream_link:
            parameter.upstream_updated()

    def upstream_updated(self):
        """Upstream updated.
        """
        pass


# Bool types

class BoolParameter(Parameter):
    """BoolParameter class."""
    dtype = bool

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class BoolVec2Parameter(Parameter):
    """BoolVec2Parameter class."""
    dtype = bool

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class BoolVec3Parameter(Parameter):
    """BoolVec3Parameter class."""
    dtype = bool

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class BoolVec4Parameter(Parameter):
    """BoolVec4Parameter class."""
    dtype = bool

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Int types

class IntParameter(Parameter):
    """IntParameter class."""
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class IntVec2Parameter(Parameter):
    """IntVec2Parameter class."""
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class IntVec3Parameter(Parameter):
    """IntVec3Parameter class."""
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class IntVec4Parameter(Parameter):
    """IntVec4Parameter class."""
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# UInt types

class UIntParameter(Parameter):
    """UIntParameter class."""
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class UIntVec2Parameter(Parameter):
    """UIntVec2Parameter class."""
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class UIntVec3Parameter(Parameter):
    """UIntVec3Parameter class."""
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class UIntVec4Parameter(Parameter):
    """UIntVec4Parameter class."""
    dtype = np.uint32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Float types

class FloatParameter(Parameter):
    """FloatParameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(1,), **kwargs)


class Vec2Parameter(Parameter):
    """Vec2Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class Vec3Parameter(Parameter):
    """Vec3Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class Vec4Parameter(Parameter):
    """Vec4Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Double types

class DoubleParameter(Parameter):
    """DoubleParameter class."""
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, **kwargs)


class DoubleVec2Parameter(Parameter):
    """DoubleVec2Parameter class."""
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2,), **kwargs)


class DoubleVec3Parameter(Parameter):
    """DoubleVec3Parameter class."""
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3,), **kwargs)


class DoubleVec4Parameter(Parameter):
    """DoubleVec4Parameter class."""
    dtype = np.float64

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4,), **kwargs)


# Matrix types

class MatNxMParameter(Parameter):
    """MatNxMParameter class."""

    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, **kwargs)


class Mat2Parameter(Parameter):
    """Mat2Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(2, 2), **kwargs)


class Mat3Parameter(Parameter):
    """Mat3Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(3, 3), **kwargs)


class Mat4Parameter(Parameter):
    """Mat4Parameter class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, shape=(4, 4), **kwargs)


# Textures

class Texture(Parameter):
    """Texture class."""
    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, **kwargs)


class Texture1D(Texture):
    """Texture1D class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class TextureInt1D(Texture):
    """TextureInt1D class."""
    dtype = np.int32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class TextureUInt1D(Texture):
    """TextureUInt1D class."""
    dtype = np.uint8

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class Texture2D(Texture):
    """Texture2D class."""
    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class TextureInt2D(Texture):
    """TextureInt2D class."""
    dtype = np.int16

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class TextureUInt2D(Texture):
    """TextureUInt2D class."""
    dtype = np.uint8

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Texture.__init__(self, *args, **kwargs)


class Attribute(Parameter):
    """Attribute class."""

    dtype = np.float32

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, **kwargs)
        self._buffer_data_contents = None

    def _set_start_data(self, data):
        """ set start data.
        
        Parameters
        ----------
        data : Any
            Description.
        """
        if self._data is None or self._shape != data.shape:
            self._shape = data.shape
            self._data = gloo.VertexBuffer(np.ascontiguousarray(data, dtype=self.dtype))


class BoolAttribute(Parameter):
    """BoolAttribute class."""
    dtype = bool

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        Parameter.__init__(self, *args, **kwargs)


class StringParameter(Parameter):
    """StringParameter class."""

    dtype = str

    def __init__(self, *args, **kwargs):
        """  init  .
        
        Parameters
        ----------
        *args : Any
            Description.
        **kwargs : Any
            Description.
        """
        super().__init__(*args, **kwargs)

    @property
    def data(self):
        """Data.
        """
        return self._data

    @data.setter
    def data(self, value: str):
        """Data.
        
        Parameters
        ----------
        value : str
            Description.
        """
        self._data = value


# Complete list of all visual bases
visual_bases = (AbstractVisual, PlanarVisual, SphericalVisual, PlainVisual, )
