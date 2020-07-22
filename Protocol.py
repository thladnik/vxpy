"""
MappApp ./Protocol.py - Collection of protocol classes.
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
    pass

class StaticProtocol(AbstractProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    _name = None

    def __init__(self, process):

        self._phases = list()

    def phaseCount(self):
        return len(self._phases)

    def newPhase(self, duration):
        self._phases.append(dict(visuals=list(), signals=list(), duration=duration))

    def addVisual(self, stimulus, kwargs, duration=None):
        self._phases[-1]['visuals'].append((stimulus, kwargs, duration))

    def addSignal(self, signal, kwargs, duration=None):
        self._phases[-1]['signals'].append((signal, kwargs, duration))
