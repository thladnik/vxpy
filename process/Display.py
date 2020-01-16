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
import logging
import time

import Controller
import Definition
import Logging
import Protocol

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class Main(Controller.BaseProcess):
    name = Definition.Process.Display

    _config   : dict              = dict()
    _glWindow : app.window.Window = None
    protocol  : Protocol          = None

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        ### Set Glumpy to use pyglet backend
        # (If pylget throws an exception when moving/resizing the window -> update pyglet)
        app.use('pyglet')
        self._window_config = app.configuration.Configuration()
        self._window_config.stencil_size = 8

        ### Open OpenGL window
        self._glWindow = app.Window(width=self.config_Display[Definition.DisplayConfig.int_window_width],
                                    height=self.config_Display[Definition.DisplayConfig.int_window_height],
                                    color=(1, 1, 1, 1),
                                    title='Display',
                                    config=self._window_config,
                                    vsync=True)
        self._glWindow.set_position(800, 500)

        ### Apply event wrapper
        self.on_draw = self._glWindow.event(self.on_draw)
        self.on_resize = self._glWindow.event(self.on_resize)
        self.on_init = self._glWindow.event(self.on_init)


        ### Run event loop
        self.run()

    ################
    ### Properties

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

        #print(self.config_Display[Definition.DisplayConfig.float_pos_glob_x_pos])

        ### Check if protocol is set yet
        if self.protocol is None:
            return

        ### Call draw of protocol class
        self.protocol.draw(dt)

    def on_resize(self, width: int, height: int):
        """Glumpy on_resize event

        :param width: new pixel width of window
        :param height: new pixel height of window
        :return:
        """

        ### Fix for (many different) glumpy backends:
        self._glWindow._width = width
        self._glWindow._height = height

        ### Check if protocol is set yet
        if self.protocol is None:
            return

        self.config_Display[Definition.DisplayConfig.int_window_width] = width
        self.config_Display[Definition.DisplayConfig.int_window_height] = height

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
        # Schedule glumpy to check for new inputs (keep this as INfrequent as possible, rendering has priority)
        app.clock.schedule_interval(self._handleCommunication, 0.01)

        # Run Glumpy event loop
        app.run(framerate=60)
