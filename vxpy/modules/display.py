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
from inspect import isclass
from typing import Callable, Union

from PySide6 import QtWidgets
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


class Display(vxprocess.AbstractProcess):
    name = PROCESS_DISPLAY

    current_visual: vxvisual.AbstractVisual = None

    _uniform_maps = dict()

    def __init__(self, **kwargs):
        vxprocess.AbstractProcess.__init__(self, **kwargs)

        self.app = app.use_app('PySide6')

        self.visual_is_displayed = False
        self.enable_idle_timeout = False
        self.times = []

        # Create canvas
        _interval = 1. / config.CONF_DISPLAY_FPS

        self.canvas = Canvas(_interval,
                             title='vxPy visual stimulus display',
                             position=(calib.CALIB_DISP_WIN_POS_X, calib.CALIB_DISP_WIN_POS_Y),
                             size=(calib.CALIB_DISP_WIN_SIZE_WIDTH, calib.CALIB_DISP_WIN_SIZE_HEIGHT),
                             resizable=False,
                             always_on_top=True,
                             app=self.app,
                             vsync=True,
                             decorate=False)

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

    def start_protocol(self):
        # Fetch protocol class
        _protocol = vxprotocol.get_protocol(vxipc.Control.Protocol[ProtocolCtrl.name])
        if _protocol is None:
            # Controller should abort this
            return

        # Instantiate protocol
        self.current_protocol = _protocol()
        self.current_protocol.initialize_visuals(self.canvas)

    def prepare_phase(self):
        # Get current phase from protocol
        phase_id = vxipc.Control.Protocol[ProtocolCtrl.phase_id]
        self.set_record_group(f'phase{vxipc.Control.Recording[RecCtrl.record_group_counter]}')
        self.current_phase = self.current_protocol.get_phase(phase_id)

        # Prepare visual associated with phase
        self.prepare_visual()

    def prepare_visual(self, new_visual=None):
        if new_visual is None:
            if self.current_phase is None:
                log.error('No visual set to prepare')
                return
            new_visual = self.current_phase.visual

        # If new_visual hasn't been instantiated yet, do it now
        if isclass(new_visual):
            self.current_visual = new_visual(self.canvas)
        else:
            self.current_visual = new_visual

    def start_phase(self):
        self.start_visual()
        self.set_record_group_attrs({'start_time': get_time(),
                                     'visual_modules': self.current_visual.__module__,
                                     'visual_name': str(self.current_visual.__class__.__qualname__)})

    def start_visual(self, parameters=None):

        # Initialize and update visual on canvas
        self.current_visual.initialize()
        self.canvas.set_visual(self.current_visual)

        # If a current_phase is set, that one dictates the parameters to be used!
        if self.current_phase is not None:
            parameters = self.current_phase.visual_parameters

        # Update visual parameters
        self.update_visual(parameters)

        # Save static parameter data to container attributes (AFTER initialization and parameter updates!!)
        self.set_record_group_attrs({param.name: param.data for param in self.current_visual.static_parameters})

        # Start visual
        self.current_visual.start()

    def end_phase(self):
        self.stop_visual()

    def end_protocol(self):
        self.current_visual = None
        self.canvas.current_visual = self.current_visual

    def run_visual(self, new_visual, parameters):
        self.current_visual = new_visual
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

        self.app.process_events()
        # self.canvas.update()

        # Update routines
        if self.current_visual is not None and self.current_visual.is_active:
            self.update_routines(self.current_visual)

    def _start_shutdown(self):
        vxprocess.AbstractProcess._start_shutdown(self)


class Canvas(app.Canvas):

    def __init__(self, _interval, *args, **kwargs):
        # Get a running PySide6 instance
        current_app = QtWidgets.QApplication.instance()
        if current_app is None:
            current_app = QtWidgets.QApplication([])

        backend_kwargs = {'screen': current_app.screens()[calib.CALIB_DISP_WIN_SCREEN_ID]}
        app.Canvas.__init__(self, *args, **kwargs, backend_kwargs=backend_kwargs)

        self.current_visual = None
        self.t: float = time.perf_counter()
        self.new_t: float = time.perf_counter()

        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))
        self.new_frame_drawn = False

        self.update()
        self.show()

    def set_visual(self, visual):
        self.current_visual = visual

    def on_draw(self, event):

        self.new_t = time.perf_counter()

        # print('This is going to get stuck if update() is conditional')
        if self.current_visual is not None:
            drawn = self.current_visual.draw(self.new_t - self.t)
        self.update()

        self.t = self.new_t

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)

