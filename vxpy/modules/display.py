"""
MappApp ./modules/display.py
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
from vispy import app
from vispy import gloo
import time

from vxpy.api import get_time
from vxpy import Config
from vxpy import Def
from vxpy import Logging
from vxpy.core import process, ipc
from vxpy.core.protocol import AbstractProtocol, get_protocol
from vxpy.core import visual


class Display(process.AbstractProcess):
    name = Def.Process.Display

    stimulus_protocol: AbstractProtocol = None
    stimulus_visual: visual.AbstractVisual = None

    _uniform_maps = dict()

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        self.app = app.use_app()
        self.visual_is_displayed = False
        self.enable_idle_timeout = False
        self.times = []

        # Create canvas
        _interval = 1. / Config.Display[Def.DisplayCfg.fps]

        _size = (Config.Display[Def.DisplayCfg.window_width],
                 Config.Display[Def.DisplayCfg.window_height])

        _position = (Config.Display[Def.DisplayCfg.window_pos_x],
                     Config.Display[Def.DisplayCfg.window_pos_y])

        self.canvas = Canvas(_interval,
                             title='Stimulus display',
                             size=_size,
                             resizable=False,
                             position=_position,
                             always_on_top=True,
                             app=self.app,
                             vsync=False,
                             decorate=False)

        # Run event loop
        self.run(interval=_interval)

    def set_display_uniform_attribute(self, uniform_name, routine_cls, attr_name):
        if uniform_name not in self._uniform_maps:
            self._uniform_maps[uniform_name] = (routine_cls, attr_name)
            Logging.write(Logging.INFO,
                          f'Set uniform "{uniform_name}" to attribute "{attr_name}" of {routine_cls.__name__}.')
        else:
            Logging.write(Logging.WARNING, f'Uniform "{uniform_name}" is already set.')

    def start_protocol(self):
        _protocol = get_protocol(ipc.Control.Protocol[Def.ProtocolCtrl.name])
        if _protocol is None:
            # Controller should abort this
            return

        self.stimulus_protocol = _protocol()
        try:
            self.stimulus_protocol.initialize_visuals(self.canvas)
        except Exception as exc:
            import traceback
            print(traceback.print_exc())

    # Phase controls

    def prepare_phase(self, visual=None, **parameters):
        # Get visual info from protocol if not provided
        if visual is None:
            phase_id = ipc.Control.Protocol[Def.ProtocolCtrl.phase_id]
            # self.stimulus_visual = self.stimulus_protocol.fetch_phase_visual(phase_id)
            self.set_record_group(f'phase{ipc.Control.Recording[Def.RecCtrl.record_group_counter]}')
            visual, parameters = self.stimulus_protocol.fetch_phase_visual(phase_id)

        # Prepare visual
        self.prepare_visual(visual, **parameters)

    def start_phase(self):
        self.start_visual()
        self.set_record_group_attrs(self.stimulus_visual.parameters)
        self.set_record_group_attrs({'start_time': get_time()})

    def end_phase(self):
        self.stop_visual()

    def end_protocol(self):
        self.stimulus_visual = None
        self.canvas.stimulus_visual = self.stimulus_visual

    # Visual controls

    def run_visual(self, visual, **parameters):
        self.prepare_visual(visual, **parameters)
        self.start_visual()

    def prepare_visual(self, stimulus_visual, **parameters):
        # If visual hasn't been instantiated yet, do it now
        if isclass(stimulus_visual):
            self.stimulus_visual = stimulus_visual(self.canvas)
        else:
            self.stimulus_visual = stimulus_visual

        self.stimulus_visual.update(**parameters)

    def start_visual(self):
        self.stimulus_visual.initialize()
        self.visual_is_displayed = True

    def update_visual(self, **parameters):
        if self.stimulus_visual is None:
            return

        self.stimulus_visual.update(**parameters)

    def stop_visual(self):
        self.stimulus_visual = None
        self.visual_is_displayed = False

    def trigger_visual(self, trigger_fun):
        self.stimulus_visual.trigger(trigger_fun)

    def _display(self):
        return self._run_protocol() or self.visual_is_displayed

    def main(self):

        # self.canvas.on_draw(None)
        self.app.process_events()

        try:
            if self._display():

                # if self.stimulus_visual is not None:
                    # Update uniforms from routine attributes
                    # for uniform_name, (routine_cls, attr_name) in self._uniform_maps.items():
                    #     idcs, times, uniform_value = api.read_attribute(routine_cls, attr_name)
                    #     self.stimulus_visual.update(**{uniform_name: uniform_value}, _update_verbosely=False)

                # Update routines
                self.update_routines(self.stimulus_visual)
            else:
                self.update_routines(None)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            # TODO: quit modules here and restart!


class Canvas(app.Canvas):

    def __init__(self, _interval, *args, **kwargs):
        app.Canvas.__init__(self, *args, **kwargs)
        self.tick = 0
        self.measure_fps(.5, self.show_fps)
        self.stimulus_visual = None
        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))

        # self._timer = app.Timer(interval=_interval/2., connect=self.on_draw, start=True)

        self.debug = False
        self.times = []
        self.t = time.perf_counter()

        self.show()

    def on_draw(self, event):
        # gloo.clear()
        if event is None:
            return

        self.newt = time.perf_counter()

        # if ipc.Process.stimulus_visual is not None:
        if ipc.Process._display():
            # Leave catch in here for now.
            # This makes debugging new stimuli much easier.
            try:
                ipc.Process.stimulus_visual.draw(self.newt - self.t)
            except Exception as exc:
                import traceback
                print(traceback.print_exc())

        self.t = self.newt

        self.update()

    def show_fps(self, fps):
        if self.debug:
            print("FPS {:.2f}".format(fps))

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)

    def _start_shutdown(self):
        process.AbstractProcess._start_shutdown(self)
