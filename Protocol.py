"""
MappApp ./Protocol.py - Collection of stimulation protocol classes which
are be used to concatenate and present successive stimuli.
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

from glumpy import gloo, transforms
import importlib
import logging

import Definition
import Logging

class StaticStimulationProtocol:

    _name = None

    def __init__(self, _display):
        self.display = _display

        self._stimuli = list()
        self._stimulus_index = -1
        self._time = 0.0
        self._advanceTime = 0.0

        self._current = None

    def addStimulus(self, stimulus, kwargs, duration=None):
        self._stimuli.append((stimulus, kwargs, duration))

    def _advance(self):
        self._stimulus_index += 1

        if self._stimulus_index >= len(self._stimuli):
            print('End of stimulation protocol')
            return

        new_stimulus, kwargs, duration = self._stimuli[self._stimulus_index]
        Logging.logger.log(logging.INFO, 'Start protocol {} phase {} '
                                         '// Stimulus {} with parameters {} (duration {})'
                           .format(self._name, self._stimulus_index, new_stimulus, kwargs, duration))


        ### Set new stimulus
        self._current = new_stimulus(self, self.display, **kwargs)

        ### Set uniforms on new program
        # self.display._updateDisplayUniforms()     # Nash 11012020: I use a completely different shaders and methods in ico_cmn for rendering so have to comment this

        # Set new time when protocol should advance
        if duration is not None:
            self._advanceTime = self._time + duration
        else:
            self._advanceTime = None

        # FINALLY: dispatch resize event
        self.display._glWindow.dispatch_event('on_resize', self.display._glWindow.width, self.display._glWindow.height)

    def draw(self, dt):
        self._time += dt

        if self._shouldAdvance() or self._current is None:
            self._advance()

        self._current.draw(dt)

    def _shouldAdvance(self):
        if (self._advanceTime is None) or (self._time < self._advanceTime):
            return False
        return True
