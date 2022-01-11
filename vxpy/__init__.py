"""
MappApp ./display_calibration.py
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
__version__ = '0.0.1-alpha'
__author__ = 'Tim Hladnik'

import sys
from vispy import app, gloo

from vxpy.modules import Controller
from vxpy.configure import acc


def set_vispy_env():
    if sys.platform == 'win32':
        app.use_app('PySide6')
        gloo.gl.use_gl('gl2')

    elif sys.platform == 'linux':
        app.use_app('glfw')
        gloo.gl.use_gl('gl2')


def main(configfile):

    set_vispy_env()

    if sys.platform == 'win32':
        # Set windows timer precision as high as possible
        import wres
        minres, maxres, curres = wres.query_resolution()
        with wres.set_resolution(maxres):
            ctrl = Controller(configfile)

    elif sys.platform == 'linux':
        ctrl = Controller(configfile)

    else:
        print('Sorry, probably not gonna work on \"{}\"'.format(sys.platform))