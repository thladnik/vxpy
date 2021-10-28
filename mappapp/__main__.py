"""
MappApp ./__main__.py
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
import argparse
import sys
from PyQt6 import QtWidgets
from vispy import app, gloo

from mappapp.modules import Controller
from mappapp.setup import acc


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--ini', action='store', dest='ini_file', type=str)
    args = parser.parse_args(sys.argv[1:])

    from mappapp.setup.main import StartupConfiguration

    if sys.platform == 'win32':

        app.use_app('PyQt6')
        gloo.gl.use_gl('gl2')

        import wres

        # Set windows timer precision as high as possible
        minres, maxres, curres = wres.query_resolution()
        with wres.set_resolution(maxres):

            configfile = None

            if args.ini_file is not None:
                configfile = args.ini_file

            else:

                acc.app = QtWidgets.QApplication([])
                acc.main = StartupConfiguration()
                acc.main.setup_ui()
                acc.app.exec()

                configfile = acc.configfile

            if configfile is None:
                print('No configuration selected. Exit.')
                exit()

            ctrl = Controller(configfile)

    elif sys.platform == 'linux':

        app.use_app('glfw')
        gloo.gl.use_gl('gl2')

        configfile = None

        if args.ini_file is not None:
            configfile = args.ini_file

        else:

            acc.app = QtWidgets.QApplication([])
            acc.main = StartupConfiguration()
            acc.main.setup_ui()
            acc.app.exec_()

            configfile = acc.configfile

        if configfile is None:
            print('No configuration selected. Exit.')
            exit()

        ctrl = Controller(configfile)
    else:
        print('Sorry, probably not gonna work on \"{}\"'.format(sys.platform))