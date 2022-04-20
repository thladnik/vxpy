"""
vxpy ./modules/display.py
Copyright (C) 2020 Tim Hladnik

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
from inspect import isclass
from typing import Callable, Union
import glfw
import time

from vispy import app
from vispy import gloo

from vxpy.api import get_time
from vxpy import calib
from vxpy import config
from vxpy.definitions import *
import vxpy.core.process as vxprocess
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.protocol as vxprotocol
import vxpy.core.visual as vxvisual

log = vxlogger.getLogger(__name__)

vxvisual.set_vispy_env()


class Display(vxprocess.AbstractProcess):
    name = PROCESS_DISPLAY

    current_visual: Union[vxvisual.AbstractVisual, None] = None

    _uniform_maps = dict()

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        self.app = app.use_app()

        self.visual_is_displayed = False
        self.enable_idle_timeout = False
        self.times = []

        # Create canvas
        _interval = 1. / config.CONF_DISPLAY_FPS

        self.canvas = Canvas(_interval)

        # Process vispy events once too avoid frozen screen at start
        app.process_events()

        # Run event loop
        self.enable_idle_timeout = False
        self.run(interval=_interval)

    def set_display_uniform_attribute(self, uniform_name, routine_cls, attr_name):
        # TODO: the routine class here is not necesasry anymore, since attributes are now independent entities
        if uniform_name not in self._uniform_maps:
            self._uniform_maps[uniform_name] = (routine_cls, attr_name)
            log.info(f'Set uniform "{uniform_name}" to attribute "{attr_name}" of {routine_cls.__name__}.')
        else:
            log.warning(f'Uniform "{uniform_name}" is already set.')

    def prepare_protocol(self):
        self.current_protocol.initialize_visuals(self.canvas)

    def prepare_phase(self):
        # Prepare visual associated with phase
        self.prepare_visual()

    def prepare_visual(self, new_visual: vxvisual.AbstractVisual = None) -> None:
        # If no visual is given, this should be a protocol-controlled run -> fetch current visual from phase
        if new_visual is None:
            new_visual = self.current_protocol.current_phase.visual

        # If new_visual hasn't been instantiated yet, do it now
        if isclass(new_visual):
            self.current_visual = new_visual(self.canvas)
        else:
            self.current_visual = new_visual

    def start_phase(self):
        self.start_visual()
        self.set_record_group_attrs({'start_time': get_time(),
                                     'visual_module': self.current_visual.__module__,
                                     'visual_name': str(self.current_visual.__class__.__qualname__),
                                     'target_duration': self.current_protocol.current_phase.duration,
                                     'target_sample_rate': config.CONF_DISPLAY_FPS})

    def start_visual(self, parameters: dict = None):

        # Initialize and update visual on canvas
        self.current_visual.initialize()
        self.canvas.set_visual(self.current_visual)

        # If a protocol is set, the phase information dictates the parameters to be used
        if self.current_protocol is not None:
            parameters = self.current_protocol.current_phase.visual_parameters

        # Update visual parameters
        self.update_visual(parameters)

        # Save static parameter data to container attributes (AFTER initialization and parameter updates!!)
        self.set_record_group_attrs({param.name: param.data for param in self.current_visual.static_parameters})

        # Start visual
        self.current_visual.start()

    def end_phase(self):
        self.stop_visual()

    def end_protocol(self):
        self.current_protocol = None
        self.canvas.current_visual = self.current_visual

    def run_visual(self, new_visual, parameters):
        self.prepare_visual(new_visual)
        self.start_visual(parameters)

    def update_visual(self, parameters: Dict):
        if self.current_visual is None:
            log.warning(f'Tried updating visual while none is set. Parameters: {parameters}')
            return

        self.current_visual.update(parameters)

    def stop_visual(self):
        self.current_visual.end()
        self.current_visual = None
        self.canvas.set_visual(self.current_visual)

    def trigger_visual(self, trigger_fun: Union[Callable, str]):
        self.current_visual.trigger(trigger_fun)

    def main(self):

        # Process app events
        # This is going call the canvas' on_draw method
        app.process_events()

        # Update routines IF visual is set and active
        if self.current_visual is not None and self.current_visual.is_active:
            self.update_routines(self.current_visual)

    def _start_shutdown(self):
        vxprocess.AbstractProcess._start_shutdown(self)


class Canvas(app.Canvas):

    def __init__(self, _interval, **kwargs):

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
        self.t: float = time.perf_counter()
        self.new_t: float = time.perf_counter()

        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))
        self.new_frame_drawn = False

        # Update size and position once
        self.update_dimensions()

        # Show
        self.show()

        # Clear after show
        self.clear()

    def clear(self):
        gloo.clear()
        self.update()
        self.swap_buffers()
        # app.process_events()

    def update_dimensions(self):

        # Update position
        pos = (calib.CALIB_DISP_WIN_POS_X, calib.CALIB_DISP_WIN_POS_Y)
        log.debug(f'Set canvas position to {pos}')
        self.position = pos

        # Update size
        size = (calib.CALIB_DISP_WIN_SIZE_WIDTH, calib.CALIB_DISP_WIN_SIZE_HEIGHT)
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
            drawn = self.current_visual.draw(self.new_t - self.t)

            # If visual is the core's KeepLast visual, don't swap buffers
            if not isinstance(self.current_visual, vxvisual.KeepLast):
                self.swap_buffers()

        # Update
        # WARNING: display is going to get stuck if update() is conditional,
        #  so update() needs to be called on each iteration
        self.update()

        # Set time to new one
        self.t = self.new_t

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)
        gloo.clear()
        self.swap_buffers()
