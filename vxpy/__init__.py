"""
vxPy ./__init__.py
Copyright (C) 2022 Tim Hladnik

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

from vxpy.modules import Controller


def main(configfile):

    if sys.platform == 'win32':
        # Set windows timer precision as high as possible
        try:
            import wres
        except ImportError as exc:
            print(f'Unable to import wres. '
                  f'Please consider installing wres for better performance on {sys.platform} platform')
        else:
            minres, maxres, curres = wres.query_resolution()
            with wres.set_resolution(maxres):
                ctrl = Controller(configfile)

        ctrl = Controller(configfile)

    elif sys.platform == 'linux':
        ctrl = Controller(configfile)

    else:
        print(f'Platform {sys.platform} not supported')
        sys.exit(1)

    # Run controller
    sys.exit(ctrl.start())
