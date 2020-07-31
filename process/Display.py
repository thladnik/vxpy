"""
MappApp ./process/Display.py - Process which handles rendering of visual visuals.
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

from glumpy import app, gl
import glfw
import keyboard
import logging
import time

import Config
import Def
import IPC
import Logging
import Process
from process import Controller
import Protocol
import protocols
import Visuals

from routines import Camera
if Def.Env == Def.EnvTypes.Dev:
    from IPython import embed

### Set glumpy to use glfw backend
app.use('glfw')

class Main(Process.AbstractProcess):
    name = Def.Process.Display

    _config   : dict                      = dict()
    _glWindow : app.window.Window         = None
    protocol  : Protocol.AbstractProtocol = None
    visual    : Visuals.AbstractVisual    = None

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        self._window_config = app.configuration.Configuration()
        self._window_config.stencil_size = 8
        self._window_config.double_buffer = True

        ### Open OpenGL window
        self._glWindow = app.Window(width=1,
                                    height=1,
                                    color=(1, 1, 1, 1),
                                    title='Display',
                                    config=self._window_config,
                                    vsync=True,
                                    fullscreen=Config.Display[Def.DisplayCfg.window_fullscreen])
        self.updateWindow()

        ### Apply event wrapper
        self.on_draw = self._glWindow.event(self.on_draw)
        self.on_resize = self._glWindow.event(self.on_resize)
        self.on_init = self._glWindow.event(self.on_init)
        self.on_key_press = self._glWindow.event(self.on_key_press)
        self.on_mouse_drag = self._glWindow.event(self.on_mouse_drag)

        self._checkScreenStatus = True

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
        self.visual = new_visual(self.protocol, self, **kwargs)
        self.frame_idx = 0

    def _cleanupProtocol(self):
        pass
        #self._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))

    def on_draw(self, dt):
        """Glumpy on_draw event.

        :param dt: elapsed time since last call in [s]. This is usually ~1/FPS
        :return:
        """

        self._glWindow.clear(color=(0.0, 0.0, 0.0, 1.0))
        gl.glStencilMask(0x00)
        gl.glStencilMask(gl.GL_TRUE)
        gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
        gl.glDisable(gl.GL_STENCIL_TEST)

        IPC.Routines.Display.handleFile()
        ### Call draw, if protocol is running
        #if self._runProtocol() or self.run_protocol_independent_visual:
        if not(self.visual is None):
            self.visual.draw(self.frame_idx, self.phase_time)
        if self._runProtocol():

            # Update routines
            IPC.Routines.Display.update(self.visual)
        else:
            self._glWindow.clear(color=(0.0,0.0,0.0,1.0))

        IPC.Routines.Display.handleFile()

    def updateWindow(self):
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

        ### Fix for (many different) glumpy backends:
        self._glWindow._width = width
        self._glWindow._height = height
        # Update size and position in configuration
        Config.Display[Def.DisplayCfg.window_width] = width
        Config.Display[Def.DisplayCfg.window_height] = height
        Config.Display[Def.DisplayCfg.window_pos_x] = self._glWindow.get_position()[0]
        Config.Display[Def.DisplayCfg.window_pos_y] = self._glWindow.get_position()[1]

    def on_mouse_drag(self, *args):
        print(args)

    def on_key_press(self, symbol, modifiers):
        print(symbol, modifiers)
        continPressDelay = 0.02

        if modifiers & glfw.MOD_CONTROL:
            if modifiers & glfw.MOD_ALT:
                ### Fullscreen toggle: Ctrl+Alt+F
                if symbol == glfw.KEY_F:
                    Config.Display[Def.DisplayCfg.window_fullscreen] = \
                        not(Config.Display[Def.DisplayCfg.window_fullscreen])
                    ## Restart display process
                    IPC.rpc(Def.Process.Controller, Controller.initializeProcess, Main)


            ### X position: Ctrl(+Shift)+X
            elif symbol == glfw.KEY_X:
                while keyboard.is_pressed('X'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.glob_x_pos] += sign * 0.001
                    time.sleep(continPressDelay)

            ### Y position: Ctrl(+Shift)+Y
            elif symbol == glfw.KEY_Y:
                while keyboard.is_pressed('Y'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.glob_y_pos] += sign * 0.001
                    time.sleep(continPressDelay)

            ### Radial offset: Ctrl(+Shift)+R
            elif symbol == glfw.KEY_R:
                while keyboard.is_pressed('R'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_pos_glob_radial_offset] += sign * 0.001
                    time.sleep(continPressDelay)


            ### Elevation: Ctrl(+Shift)+E
            elif symbol == glfw.KEY_E:
                while keyboard.is_pressed('E'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_elev_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Azimuth: Ctrl(+Shift)+A
            elif symbol == glfw.KEY_A:
                while keyboard.is_pressed('A'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_azim_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Distance: Ctrl(+Shift)+D
            elif symbol == glfw.KEY_D:
                while keyboard.is_pressed('D'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_distance] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Scale: Ctrl(+Shift)+S
            elif symbol == glfw.KEY_S:
                while keyboard.is_pressed('S'):
                    sign = +1 if (modifiers & glfw.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.sph_view_scale] += sign * 0.001
                    time.sleep(continPressDelay)
            else:
                self._glWindow.on_key_press(symbol, modifiers)

    def _startShutdown(self):
        self._glWindow.close()
        Process.AbstractProcess._startShutdown(self)

    def main(self):
        app.clock.schedule_interval(self._handleInbox, 0.01)

        # Run Glumpy event loop
        app.run(framerate=Config.Display[Def.DisplayCfg.fps])

