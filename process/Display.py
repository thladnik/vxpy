"""
MappApp ./process/DefaultDisplayRoutines.py - Process which handles rendering of visual visuals.
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

from glumpy import app
from PyQt5 import QtWidgets
import Config
import Def
import IPC
import Process
import Protocol
import protocols
import Visuals

if Def.Env == Def.EnvTypes.Dev:
    pass

class Display(Process.AbstractProcess):
    name = Def.Process.Display

    glwindow  : app.window.Window         = None
    protocol  : Protocol.AbstractProtocol = None
    visual    : Visuals.AbstractVisual    = None

    def __init__(self,**kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        app.use('{} (GL {}.{} {})'.format(Config.Display[Def.DisplayCfg.window_backend],
                                          Config.Display[Def.DisplayCfg.gl_version_major],
                                          Config.Display[Def.DisplayCfg.gl_version_minor],
                                          Config.Display[Def.DisplayCfg.gl_profile]))

        self._window_config = app.configuration.Configuration()
        self._window_config.double_buffer = True

        ### Open OpenGL window
        self.glwindow = app.Window(width=256,
                                   height=256,
                                   color=(0., 0., 0., 1),
                                   title='Display',
                                   config=self._window_config,
                                   vsync=True)

        ### (Manually) Configure glumpy eventloop
        self.glumpy_backend = app.__backend__
        self.glumpy_clock = app.__init__(backend=self.glumpy_backend)
        self.glumpy_count = len(self.glumpy_backend.windows())

        ### Set position
        self.glwindow.set_position(Config.Display[Def.DisplayCfg.window_pos_x],
                                   Config.Display[Def.DisplayCfg.window_pos_y])

        ### Set window size
        self.glwindow.set_size(Config.Display[Def.DisplayCfg.window_width],
                               Config.Display[Def.DisplayCfg.window_height])

        ### Set screen
        scr_handle = self.glwindow._native_app.screens()[Config.Display[Def.DisplayCfg.window_screen_id]]
        self.glwindow._native_window.windowHandle().setScreen(scr_handle)

        ### Set fullscreen
        if Config.Display[Def.DisplayCfg.window_fullscreen]:
            self.glwindow._native_window.showFullScreen()

        ###
        self.glwindow._native_window.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        ### Apply event wrapper
        self.on_draw = self.glwindow.event(self.on_draw)
        self.on_init = self.glwindow.event(self.on_init)

        ### Run event loop
        self.run(1./Config.Display[Def.DisplayCfg.fps])


    def on_init(self):
        """Glumpy on_init event"""
        pass

    def _prepare_protocol(self):
        self.protocol = protocols.load(IPC.Control.Protocol[Def.ProtocolCtrl.name])(self)

    def _prepare_phase(self):
        new_phase = self.protocol._phases[IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]]
        new_visual, kwargs, duration = new_phase['visuals'][0]
        self.visual = new_visual(self.glwindow, **kwargs)
        self.frame_idx = 0

    def _cleanup_protocol(self):
        pass

    def on_draw(self, dt):
        """Glumpy on_draw event.

        :param dt: elapsed time since last call in [s]. This is usually ~1/FPS
        :return:
        """

        self.glwindow.clear()

        IPC.Routines.Display.handleFile()

        ### Call draw, if protocol is running
        if not(self.visual is None):
            self.visual.draw(self.frame_idx, self.phase_time)

        if self._run_protocol():
            # Update routines
            IPC.Routines.Display.update(self.visual)
        else:
            self.glwindow.clear()

    def _start_shutdown(self):
        self.glwindow.close()
        Process.AbstractProcess._start_shutdown(self)

    def main(self):
        if self.glumpy_count:
            self.glumpy_count = self.glumpy_backend.process(self.glumpy_clock.tick())

        ## OLD
        #app.clock.schedule_interval(self._handleInbox, 0.01)
        # Run Glumpy event loop
        #app.run(framerate=Config.Display[Def.DisplayCfg.fps])

