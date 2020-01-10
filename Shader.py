"""
MappApp ./Shader.py - Custom shader class used in ./process/Display.py.
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


import os

import Definition
class Shader:

    _glumpy_placeholders = {
        '//<viewport.transform>;': '<viewport.transform>;',
        '//<viewport.clipping>;': '<viewport.clipping>;'
    }

    def __init__(self, base, main):
        self._compile(base, main)

    def _compile(self, base, main):
        self.shader = ''

        # Load base shader
        with open(os.path.join(Definition.Path.Shader, base), 'r') as fobj:
            self.shader += fobj.read()
            fobj.close()
        self.shader += '\n'

        # Load shader containing void main()
        with open(os.path.join(Definition.Path.Shader, main), 'r') as fobj:
            self.shader += fobj.read()
            fobj.close()

            # Substitute Glumpy-specific placeholders
        for key, str in self._glumpy_placeholders.items():
            self.shader = self.shader.replace(key, str)

    def getString(self):
            return self.shader