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
import vispy
from vispy import app
from vispy import gloo
import time

from mappapp import api
from mappapp import Config
from mappapp import Def
from mappapp import IPC
from mappapp import Logging
from mappapp import protocols
from mappapp import gui
from mappapp.core import process
from mappapp.core import protocol
from mappapp.core import visual


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
        gloo.clear()
        if event is None:
            return
        # print(event.__dict__['_sources'][0].__dict__)

        self.newt = time.perf_counter()

        if IPC.Process.stimulus_visual is not None:
            # Leave catch in here for now.
            # This makes debugging new stimuli much easier.
            try:
                IPC.Process.stimulus_visual.draw(self.newt-self.t)
            except Exception as exc:
                import traceback
                print(traceback.print_exc())

        self.t = self.newt

        self.update()

    def show_fps(self, fps):
        if self.debug:
            print("FPS {:.2f}".format(fps))

        # api.gui_rpc(core.Display.update_fps_estimate, fps, _send_verbosely=False)

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)


class Display(process.AbstractProcess):
    name = Def.Process.Display

    stimulus_protocol: protocol.AbstractProtocol = None
    stimulus_visual: visual.AbstractVisual = None

    _uniform_maps = dict()

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        self.app = app.use_app()

        # Create canvas
        _interval = 1. / Config.Display[Def.DisplayCfg.fps]

        _size = (Config.Display[Def.DisplayCfg.window_width],
                 Config.Display[Def.DisplayCfg.window_height])

        _position = (Config.Display[Def.DisplayCfg.window_pos_x],
                     Config.Display[Def.DisplayCfg.window_pos_y])

        self.canvas = Canvas(_interval,
                             size=_size,
                             resizable=False,
                             position=_position,
                             always_on_top=True,
                             app=self.app,
                             vsync=False)
        # self.canvas.fullscreen = Config.Display[Def.DisplayCfg.window_fullscreen]

        self._display_visual = False

        self.times = []

        # Run event loop
        self.enable_idle_timeout = False
        self.run(interval=_interval)

    def set_display_uniform_attribute(self, uniform_name, routine_cls, attr_name):
        if uniform_name not in self._uniform_maps:
            self._uniform_maps[uniform_name] = (routine_cls, attr_name)
            Logging.write(Logging.INFO, f'Set uniform "{uniform_name}" to attribute "{attr_name}" of {routine_cls.__name__}.')
        else:
            Logging.write(Logging.WARNING, f'Uniform "{uniform_name}" is already set.')

    def start_protocol(self):
        self.stimulus_protocol = protocols.load(IPC.Control.Protocol[Def.ProtocolCtrl.name])(self.canvas)
        try:
            self.stimulus_protocol.initialize()
        except Exception as exc:
            import traceback
            print(traceback.print_exc())

    def start_phase(self):
        phase_id = IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]
        self.stimulus_visual = self.stimulus_protocol.fetch_phase_visual(phase_id)
        IPC.Process.set_record_group(f'phase_{phase_id}',group_attributes=self.stimulus_visual.parameters)

    def end_protocol(self):
        self.stimulus_visual = None
        self.canvas.stimulus_visual = self.stimulus_visual

    def start_visual(self, visual_cls, **parameters):
        self.stimulus_visual = visual_cls(self.canvas)
        self.stimulus_visual.initialize(**parameters)
        self._display_visual = True

    def stop_visual(self):
        self.stimulus_visual = None
        self._display_visual = False

    def _start_shutdown(self):
        process.AbstractProcess._start_shutdown(self)

    def trigger_visual(self, trigger_fun):
        self.stimulus_visual.trigger(trigger_fun)

    def update_visual(self, **parameters):
        if self.stimulus_visual is None:
            return

        self.stimulus_visual.update(**parameters)

    def _display(self):
        return self._run_protocol() or self._display_visual

    def main(self):

        self.canvas.on_draw(None)
        self.app.process_events()

        try:
            if self._display():

                if self.stimulus_visual is not None:
                    # Update uniforms from routine attributes
                    for uniform_name, (routine_cls, attr_name) in self._uniform_maps.items():
                        idcs, times, uniform_value = api.read_attribute(routine_cls, attr_name)
                        self.stimulus_visual.update(**{uniform_name: uniform_value}, _update_verbosely=False)

                # Update routines
                self.update_routines(self.stimulus_visual)
            else:
                self.update_routines(None)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            # TODO: quit modules here and restart!
