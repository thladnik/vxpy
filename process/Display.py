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

import Config
import Def
import IPC
import Process
import Protocol
import protocols
import Visuals

if Def.Env == Def.EnvTypes.Dev:
    pass

### Set glumpy to use pyglet4 backend
app.use(Def.Display_backend)

class Display(Process.AbstractProcess):
    name = Def.Process.Display

    _config   : dict                      = dict()
    glwindow  : app.window.Window         = None
    protocol  : Protocol.AbstractProtocol = None
    visual    : Visuals.AbstractVisual    = None

    def __init__(self,**kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        self._window_config = app.configuration.Configuration()
        self._window_config.double_buffer = True

        ### Open OpenGL window
        self.glwindow = app.Window(width=Config.Display[Def.DisplayCfg.window_width],
                                   height=Config.Display[Def.DisplayCfg.window_height],
                                   color=(0, 0, 0, 1),
                                   title='Display',
                                   config=self._window_config,
                                   vsync=True)
        self.glwindow.set_position(Config.Display[Def.DisplayCfg.window_pos_x],
                                   Config.Display[Def.DisplayCfg.window_pos_y])
        ### Apply event wrapper
        self.on_draw = self.glwindow.event(self.on_draw)
        self.on_init = self.glwindow.event(self.on_init)

        ### Run event loop
        self.run(0.01)

    ################
    ### Glumpy-called events

    def on_init(self):
        """Glumpy on_init event"""
        pass

    def _prepareProtocol(self):
        self.protocol = protocols.load(IPC.Control.Protocol[Def.ProtocolCtrl.name])(self)

    def _preparePhase(self):
        new_phase = self.protocol._phases[IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]]
        new_visual, kwargs, duration = new_phase['visuals'][0]
        self.visual = new_visual(self.glwindow, **kwargs)
        self.frame_idx = 0

    def _cleanupProtocol(self):
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

        if self._runProtocol():
            # Update routines
            IPC.Routines.Display.update(self.visual)
        else:
            self.glwindow.clear()

    def updateWindow(self):
        return
        self._glWindow.set_size(Config.Display[Def.DisplayCfg.window_width],
                                Config.Display[Def.DisplayCfg.window_height])
        self._glWindow.set_position(Config.Display[Def.DisplayCfg.window_pos_x],
                                    Config.Display[Def.DisplayCfg.window_pos_y])

    def on_resize(self, width: int, height: int):
        """Glumpy on_resize event

        :param width: new pixel width of window
        :param height: new pixel height of window
        :return:
        """

        return

        ### Fix for (many different) glumpy backends:
        self._glWindow._width = width
        self._glWindow._height = height
        # Update size and position in configuration
        Config.Display[Def.DisplayCfg.window_width] = width
        Config.Display[Def.DisplayCfg.window_height] = height
        Config.Display[Def.DisplayCfg.window_pos_x] = self._glWindow.get_position()[0]
        Config.Display[Def.DisplayCfg.window_pos_y] = self._glWindow.get_position()[1]



    def _startShutdown(self):
        self.glwindow.close()
        Process.AbstractProcess._startShutdown(self)

    def main(self):
        app.clock.schedule_interval(self._handleInbox, 0.01)

        # Run Glumpy event loop
        app.run(framerate=Config.Display[Def.DisplayCfg.fps])

