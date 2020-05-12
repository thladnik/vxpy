"""
MappApp ./Protocol.py - Collection of protocol classes which
are be used to concatenate and present successive visuals.
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

import Def
import Logging

class AbstractProtocol:
    def draw(self, dt):
        raise NotImplementedError('draw method not implemented in {}'
                                  .format(self.__class__.__qualname__))

class StaticProtocol(AbstractProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    _name = None

    def __init__(self, process):
        self.process = process

        self._time = 0.0

        self._current = None

        self._phases = list()

    def phaseCount(self):
        return len(self._phases)

    def newPhase(self, duration):
        self._phases.append(dict(visuals=list(), signals=list(), duration=duration))

    def addVisual(self, stimulus, kwargs, duration=None):
        self._phases[-1]['visuals'].append((stimulus, kwargs, duration))

    def addSignal(self, signal, kwargs, duration=None):
        self._phases[-1]['signals'].append((signal, kwargs, duration))

    def setCurrentPhase(self, phase_id):
        new_stimulus, kwargs, duration = self._phases[phase_id]['visuals'][0]
        self._current = new_stimulus(self, self.process, **kwargs)
        self._current.start()

    def draw(self, dt):
        self._time += dt
        self._current.draw(dt)
