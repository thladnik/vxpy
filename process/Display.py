"""
MappApp ./process/Display.py - Process which handles rendering of visual stimuli.
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

from glumpy import app, glm
import keyboard
import logging
import time

import Controller
import Config
import Def
import IPC
import Logging
import Protocol

if Def.Env == Def.EnvTypes.Dev:
    from IPython import embed

### Set Glumpy to use pyglet backend
# (If pylget throws an exception when moving/resizing the window -> update pyglet)
app.use('pyglet')
from pyglet.window import key

class Main(Controller.BaseProcess):
    name = Def.Process.Display

    _config   : dict              = dict()
    _glWindow : app.window.Window = None
    protocol  : Protocol          = None

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        self._window_config = app.configuration.Configuration()
        self._window_config.stencil_size = 8

        ### Open OpenGL window
        self._glWindow = app.Window(width=Config.Display[Def.DisplayCfg.window_width],
                                    height=Config.Display[Def.DisplayCfg.window_height],
                                    color=(1, 1, 1, 1),
                                    title='Display',
                                    config=self._window_config,
                                    vsync=True,
                                    fullscreen=False)
        self._glWindow.set_position(Config.Display[Def.DisplayCfg.window_pos_x],
                                    Config.Display[Def.DisplayCfg.window_pos_y])

        ### Apply event wrapper
        self.on_draw = self._glWindow.event(self.on_draw)
        self.on_resize = self._glWindow.event(self.on_resize)
        self.on_init = self._glWindow.event(self.on_init)
        self.on_key_press = self._glWindow.event(self.on_key_press)

        self._checkScreenStatus = True

        ### Run event loop
        self.run()

    ################
    ### Glumpy-called events

    def on_init(self):
        """Glumpy on_init event
        """
        pass

    def on_draw(self, dt):
        """Glumpy on_draw event.
        This method is just a pass-through to the currently set protocol.

        :param dt: elapsed time since last call in [s]
        :return:
        """

        ########
        ### RUNNING
        if self.inState(self.State.RUNNING):

            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                Logging.write(logging.INFO, 'Phase {} ended.'.format(IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]))
                self.setState(self.State.PHASE_END)
                return

            #TODO: actually draw frame
            pass

        ########
        ### IDLE
        elif self.inState(self.State.IDLE):

            ## Ctrl PREPARE_PROTOCOL
            if self.inState(self.State.PREPARE_PROTOCOL, Def.Process.Controller):

                # TODO: actually set up protocol
                protocol = IPC.Control.Protocol[Def.ProtocolCtrl.name]

                # Set next state
                self.setState(self.State.WAIT_FOR_PHASE)
                return

            ### Fallback, timeout
            time.sleep(0.05)

        ########
        ### WAIT_FOR_PHASE
        elif self.inState(self.State.WAIT_FOR_PHASE):

            if not(self.inState(self.State.PREPARE_PHASE, Def.Process.Controller)):
                return

            # TODO: actually set up phase
            phase = IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]

            # Set next state
            self.setState(self.State.READY)

        ########
        ### READY
        elif self.inState(self.State.READY):
            if not(self.inState(self.State.RUNNING, Def.Process.Controller)):
                return

            ### Wait for go time
            while self.inState(self.State.RUNNING, Def.Process.Controller):
                if IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] <= time.time():
                    Logging.write(logging.INFO, 'Start at {}'.format(time.time()))
                    self.setState(self.State.RUNNING)
                    break

            return

        ########
        ### PHASE_END
        elif self.inState(self.State.PHASE_END):

            ####
            ## Ctrl in PREPARE_PHASE -> there's a next phase
            if self.inState(self.State.PREPARE_PHASE, Def.Process.Controller):
                self.setState(self.State.WAIT_FOR_PHASE)
                return

            elif self.inState(self.State.PROTOCOL_END, Def.Process.Controller):

                # TODO: clean up protocol

                self.setState(self.State.IDLE)
            else:
                pass

        ########
        ### Fallback: timeout
        else:
            time.sleep(0.05)

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

    def on_key_press(self, symbol, modifiers):
        continPressDelay = 0.02
        if modifiers & key.MOD_CTRL:
            if modifiers & key.MOD_ALT:
                ### Fullscreen toggle: Ctrl+Alt+F
                if symbol == key.F:
                    Config.Display[Def.DisplayCfg.window_fullscreen] = \
                        not(Config.Display[Def.DisplayCfg.window_fullscreen])

            ### X position: Ctrl(+Shift)+X
            elif symbol == key.X:
                while keyboard.is_pressed('X'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.pos_glob_x_pos] += sign * 0.001
                    time.sleep(continPressDelay)

            ### Y position: Ctrl(+Shift)+Y
            elif symbol == key.Y:
                while keyboard.is_pressed('Y'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.pos_glob_y_pos] += sign * 0.001
                    time.sleep(continPressDelay)

            ### Radial offset: Ctrl(+Shift)+R
            elif symbol == key.R:
                while keyboard.is_pressed('R'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.pos_glob_radial_offset] += sign * 0.001
                    time.sleep(continPressDelay)


            ### Elevation: Ctrl(+Shift)+E
            elif symbol == key.E:
                while keyboard.is_pressed('E'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.view_elev_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Azimuth: Ctrl(+Shift)+A
            elif symbol == key.A:
                while keyboard.is_pressed('A'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.view_azim_angle] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Distance: Ctrl(+Shift)+D
            elif symbol == key.D:
                while keyboard.is_pressed('D'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.view_distance] += sign * 0.1
                    time.sleep(continPressDelay)

            ### Scale: Ctrl(+Shift)+S
            elif symbol == key.S:
                while keyboard.is_pressed('S'):
                    sign = +1 if (modifiers & key.MOD_SHIFT) else -1
                    Config.Display[Def.DisplayCfg.view_scale] += sign * 0.001
                    time.sleep(continPressDelay)

    def _checkScreen(self, dt):
        if not(self._checkScreenStatus):
            return
        screenid = Config.Display[Def.DisplayCfg.window_screen_id]
        fscreen = Config.Display[Def.DisplayCfg.window_fullscreen]
        if self._glWindow.get_fullscreen() != fscreen:
            try:
                self._glWindow.set_fullscreen(fscreen, screen=screenid)
            except:
                self._glWindow.set_fullscreen(fscreen)
                Logging.write(logging.WARNING, 'Unable to set screen ID for fullscreen. Check glumpy version.')
                self._checkScreenStatus = False

            if not(fscreen):
                try:
                    self._glWindow.set_size(600, 400)
                except:
                    Logging.write(logging.WARNING, 'Unable to set backend window size. Check glumpy version.')
                    self._checkScreenStatus = False

    def startProtocol(self):
        Logging.write(logging.INFO, 'Start new protocol ({})'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.name]))

        print('Start protocol')
        ### Set protocol
        self.protocol1 = 'blabla'

        ### Stand by for phase
        self.setState(self.State.standby)

    def stopProtocol(self):
        Logging.write(logging.INFO, 'Stop protocol ({})'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.name]))

        print('Stop protocol')
        ### Cleanup
        self.protocol1 = None

        ### Turn to idle
        self.setState(self.State.idle)

    def startNewStimulationProtocol(self, protocol_cls):
        """Start the presentation of a new stimulation protocol

        :param protocol_cls: class object of the stimulation protocol
        :return:
        """

        ### Initialize new stimulus protocol
        Logging.logger.log(logging.INFO, 'Start new stimulation procotol {}'.
                           format(str(protocol_cls)))
        self.protocol = protocol_cls(self)

    def _startShutdown(self):
        self._glWindow.close()
        Controller.BaseProcess._startShutdown(self)

    def main(self):
        app.clock.schedule_interval(self._handleInbox, 0.01)
        app.clock.schedule_interval(self._checkScreen, 0.1)

        # Run Glumpy event loop
        app.run(framerate=Config.Display[Def.DisplayCfg.fps])

