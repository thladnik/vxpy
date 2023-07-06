"""Core visual module
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
from numbers import Number
import sys

import numpy as np
from numpy.typing import DTypeLike
from typing import List, Tuple, Any, Union, Callable, Dict
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

    available_transforms: Dict[str, vxtransforms.BaseTransform] = {}
    transform: vxtransforms.BaseTransform = None

    description: str = ''

    def __init__(self, canvas=None, _protocol=None, _transform=None):
        if canvas is None:
            canvas = gloo.context.FakeCanvas()
        self.canvas: app.Canvas = canvas

        if _protocol is None:
            _protocol = protocol.BaseProtocol()
        self.protocol: protocol.BaseProtocol = _protocol

        if _transform is None:
            _transform = vxtransforms.BaseTransform()
        self.transform = _transform

        self.parameters: Dict[str, Any] = {}
        self.custom_programs: Dict[str, gloo.Program] = {}
        self.data_appendix: Dict[str, Any] = {}

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

    def get_programs(self) -> Dict[str, gloo.Program]:
        return self.custom_programs

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

    @classmethod
    def load_shader(cls, filepath: str):
        if filepath.startswith('./'):
            # Use path relative to visual
            pyfileloc = inspect.getfile(cls)
            path = os.sep.join([*pyfileloc.split(os.sep)[:-1], filepath[2:]])
        else:
            # Use absolute path to global shader folder
            path = os.path.join(PATH_SHADERS, filepath)

        log.debug(f'Load shader from {path}')
        with open(path, 'r') as f:
            code = f.read()

        return code

    def load_vertex_shader(self, filepath: str):
        log.debug(f'Load vertex shader from {filepath}')
        return self.parse_vertex_shader(self.load_shader(filepath))

    def parse_vertex_shader(self, vert: str):
        log.debug('Parse vertex shader')
        return self.transform.parse_vertex_shader(vert)

    def trigger(self, trigger_fun: Union[Callable, str]):
        name = trigger_fun.__name__ if callable(trigger_fun) else trigger_fun
        getattr(self, name)()

    def start(self):
        for attr in self.__dict__.values():
            if issubclass(type(attr), vxevent.Trigger):
                attr.set_active(True)
        self.is_active = True

    def end(self):
        for attr in self.__dict__.values():
            if issubclass(type(attr), vxevent.Trigger):
                attr.set_active(False)
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

    def apply_transform(self, *args, **kwargs):
        """DEPRECATED. This method has been moved to core transform module.

        It only exists for backwards compatibility here.
        Where neccessary, it can still be called directly via self.transform.apply_transform"""
        pass

    @abstractmethod
    def initialize(self, **kwargs):
        """Method to initialize and reset all parameters."""

    @abstractmethod
    def render(self, dt):
        """Method to be implemented in final visual."""


class SphericalVisual(AbstractVisual, ABC):

    available_transforms = [vxtransforms.PerspectiveTransform,
                            vxtransforms.Spherical4ChannelProjectionTransform,
                            vxtransforms.Spherical4ScreenCylindricalTransform]

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)


class PlanarVisual(AbstractVisual, ABC):

    available_transforms = [vxtransforms.PlanarTransform]

    def __init__(self, *args, **kwargs):
        AbstractVisual.__init__(self, *args, **kwargs)


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
        return self.name

    def __add__(self, other):
        self.data = self.data + other

    @property
    def shape(self):
        return self._shape

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
        if self._data is None:
            self._shape = data.shape if hasattr(data, 'shape') else (1,)
            self._data = np.array(data, dtype=self.dtype)

    @property
    def data(self):
        return self._data[:]

    @data.setter
    def data(self, data):
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
        if self._data is None or self._shape != data.shape:
            self._shape = data.shape
            self._data = gloo.VertexBuffer(np.ascontiguousarray(data, dtype=self.dtype))


class BoolAttribute(Parameter):
    dtype = bool

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self, *args, **kwargs)


# Complete list of all visual bases
visual_bases = (AbstractVisual, PlanarVisual, SphericalVisual, PlainVisual, )
