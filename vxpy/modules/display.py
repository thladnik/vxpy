"""Display process module
"""
from __future__ import annotations
from inspect import isclass
from typing import Callable, Dict, Union, Type
import glfw
import time

from vispy import app
from vispy import gloo

import vxpy.config
from vxpy.core.ipc import get_time
from vxpy import calib
from vxpy import config
from vxpy.definitions import *
import vxpy.core.container as vxcontainer
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.process as vxprocess
import vxpy.core.protocol as vxprotocol
import vxpy.core.transform as vxtransform
import vxpy.core.visual as vxvisual
import vxpy.core.devices.serial as vxserial

log = vxlogger.getLogger(__name__)

vxvisual.set_vispy_env()


class Display(vxprocess.AbstractProcess):
    name = PROCESS_DISPLAY

    # Protocol settings
    current_visual: Union[vxvisual.AbstractVisual, None] = None
    fallback_phase_counter = 0

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        self.app = app.use_app()

        self.visual_is_displayed = False
        self.times = []

        # Create canvas
        # _interval = 1. / (2 * config.DISPLAY_FPS)
        _interval = 1. / config.DISPLAY_FPS
        self.canvas = Canvas()

        # Get transform from config and set it to process and canvas
        _transform = vxtransform.get_config_transform()
        if _transform is not None:
            _transform = _transform()
        self.current_transform: vxtransform.BaseTransform = _transform
        self.canvas.set_transform(self.current_transform)

        # Process vispy events once to avoid frozen screen at start
        app.process_events()

        # Run event loop
        # self.enable_idle_timeout = False
        self.run(interval=_interval)

    def main(self):

        # Process app events
        # This is going call the canvas' on_draw method
        app.process_events()

        # Update routines IF visual is set and active
        if self.current_visual is not None and self.current_visual.is_active:
            self.update_routines(self.current_visual)

    def prepare_static_protocol(self):
        # Create all visuals during protocol preparation (ahead of protocol run)
        #  This may come with some initial overhead, but reduces latency between stimulation phases
        self.current_protocol.create_visuals(self.canvas, _transform=self.current_transform)

    def prepare_static_protocol_phase(self):
        # Prepare visual associated with phase
        self.prepare_visual()

    def start_static_protocol_phase(self):
        self.start_visual()

    def prepare_trigger_protocol(self):
        # Initialize all visuals during protocol preparation
        #  This may come with some overhead, but reduces latency between stimulation phases
        self.current_protocol.create_visuals(self.canvas, _transform=self.current_transform)

    def prepare_trigger_protocol_phase(self):
        # Prepare visual associated with phase
        self.prepare_visual()

    def start_trigger_protocol_phase(self):
        self.start_visual()

    def prepare_visual(self, visual: vxvisual.AbstractVisual = None, parameters: dict = None) -> None:

        # If no visual is given, this should be a protocol-controlled run -> fetch current visual from phase
        if visual is None:
            visual = self.current_protocol.current_phase.visual

        # Prepare parameters
        if parameters is None:
            if self.current_protocol is None:
                parameters = {}
            else:
                # Fetch protocol-defined parameters
                parameters = self.current_protocol.current_phase.visual_parameters

        # If new_visual hasn't been instantiated yet, do it now
        if isclass(visual):
            log.debug(f'Create new visual of class {visual.__name__}')
            self.current_visual = visual(self.canvas, _transform=self.current_transform)
        else:
            log.debug(f'Set visual to existing instance of {visual.__class__.__name__}')
            self.current_visual = visual

        # Update visual parameters
        self.update_visual(parameters)

        # Set fallback counter in case this is outside a stimulation protocol
        vxcontainer.set_fallback_phase_id(f'{self.current_visual.__class__.__name__}_{self.fallback_phase_counter}')
        self.fallback_phase_counter += 1

        # Create datasets for all variable visual parameters
        for param in self.current_visual.variable_parameters:
            vxcontainer.create_phase_dataset(param.name, param.shape, param.dtype)

        if self.current_protocol is not None:
            vxcontainer.add_phase_attributes({'__target_duration': self.current_protocol.current_phase.duration})

        # Set phase attributes
        attributes = {
            '__target_start_time': self.phase_start_time,
            '__target_end_time': self.phase_end_time,
            '__target_sample_rate': config.DISPLAY_FPS,
            '__visual_module': self.current_visual.__module__,
            '__visual_name': str(self.current_visual.__class__.__qualname__)
        }
        vxcontainer.add_phase_attributes(attributes)

    def start_visual(self):
        log.info(f'Start new visual {self.current_visual.__class__.__name__}')

        # Initialize and update visual on canvas
        self.current_visual.initialize(**self.phase_info)
        self.canvas.set_visual(self.current_visual)

        # Save static parameter data to container attributes
        # (needs to happen AFTER initialization and parameter updates!!)
        static_params = {param.name: param.data for param in self.current_visual.static_parameters}
        vxcontainer.add_phase_attributes(static_params)

        # Start visual
        self.current_visual.start()

        # Update time
        self.canvas.update_current_time()

        # Set start time precisely
        vxcontainer.add_phase_attributes({f'__start_time': vxipc.get_time()})

    def end_static_protocol_phase(self):
        self.stop_visual()

    def end_static_protocol(self):
        self.current_protocol = None
        self.canvas.current_visual = self.current_visual

    def run_visual(self, new_visual: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]], parameters: dict):
        self.prepare_visual(new_visual, parameters)
        self.start_visual()

    def update_visual(self, parameters: Dict):
        if self.current_visual is None:
            log.warning(f'Tried updating visual while none is set. Parameters: {parameters}')
            return

        self.current_visual.update(parameters)

    def stop_visual(self):
        if self.current_visual is None:
            log.warning('Tried to stop visual while none was set')
            return

        log.debug(f'Stop visual {self.current_visual.__class__.__name__}')

        self.current_visual.end()
        self.current_visual = None
        self.canvas.set_visual(self.current_visual)

    def trigger_visual(self, trigger_fun: Union[Callable, str]):
        self.current_visual.trigger(trigger_fun)

    def clear_canvas(self):
        self.canvas.clear()

    def _start_shutdown(self):
        vxprocess.AbstractProcess._start_shutdown(self)


class Canvas(app.Canvas):

    def __init__(self, **kwargs):

        # DONT EVER REMOVE THIS
        # NOTE: GLFW has to be initialized, otherwise canvas positioning is not going to work properly
        glfw.init()
        # DONT EVER REMOVE THIS

        # Set canvas init arguments
        backend_kwargs = {}
        canvas_kwargs = {'app': app.use_app(),
                         'title': 'vxPy visual stimulus display',
                         'position': (64, 64),
                         'size': (256, 256),
                         'resizable': True,
                         'always_on_top': True,
                         'vsync': True,
                         'decorate': False,
                         'autoswap': False}

        # Overwrite canvas arguments
        for key in list(kwargs.keys()):
            if key in canvas_kwargs:
                canvas_kwargs[key] = kwargs.pop(key)

        # Call parent init
        app.Canvas.__init__(self, **canvas_kwargs, backend_kwargs=backend_kwargs)

        self.current_visual: vxvisual.AbstractVisual = None
        self.current_transform: vxtransform.BaseTransform = None

        # Set display transform
        self.current_t: float = time.perf_counter()
        self.new_t: float = time.perf_counter()

        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))
        self.new_frame_drawn = False

        # Update size and position once
        self.update_dimensions()

        # Show
        self.show()

        # Clear after show
        self.clear()

    def update_current_time(self):
        self.current_t = time.perf_counter()

    def set_transform(self, _transform: vxtransform.BaseTransform):
        self.current_transform = _transform

    def clear(self):
        gloo.clear()
        self.update()
        self.swap_buffers()
        # app.process_events()

    def update_dimensions(self):

        # Update position
        pos = (config.DISPLAY_WIN_POS_X, config.DISPLAY_WIN_POS_Y)
        log.debug(f'Set canvas position to {pos}')
        self.position = pos

        # Update size
        size = (config.DISPLAY_WIN_SIZE_WIDTH_PX, config.DISPLAY_WIN_SIZE_HEIGHT_PX)
        log.debug(f'Set canvas size to {size}')
        self.size = size

        self.app.process_events()

    def set_visual(self, visual):
        self.current_visual = visual

    def on_draw(self, event):
        # Get current time
        self.new_t = time.perf_counter()

        if self.current_visual is not None and self.current_visual.is_active:

            # Draw visual
            self.current_transform.apply(self.current_visual, self.new_t - self.current_t)

            # If visual is the core's KeepLast visual, don't swap buffers
            if not isinstance(self.current_visual, vxvisual.KeepLast):
                self.swap_buffers()

            # Write variable display parameters to file
            for parameter in self.current_visual.variable_parameters:
                vxcontainer.add_to_phase_dataset(parameter.name, parameter.data)

        # Update
        # WARNING: display is going to get stuck if update() is conditional,
        #  so update() needs to be called on each iteration
        self.update()

        # Set time to new one
        self.current_t = self.new_t

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)
        gloo.clear()
        self.swap_buffers()
