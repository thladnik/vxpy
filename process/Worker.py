"""
MappApp ./process/Worker.py - Worker process which can be employed for
continuous or scheduled execution of functions.
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

from time import sleep

import Controller
import Definition

class Main(Controller.BaseProcess):
    name = Definition.Process.Worker

    _functionList : list = list()

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(**kwargs)

    def addFunction(self, fun):
        self._functionList.append(fun)

    def main(self):
        if len(self._functionList) == 0:
            sleep(0.1)
        for fun in self._functionList:
            fun()