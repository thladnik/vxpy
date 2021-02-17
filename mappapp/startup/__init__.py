"""
MappApp ./startup/routine.py - Startup script is used for creation and
modification of program configuration files.
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


def run():
    import argparse
    import sys
    from PyQt5 import QtWidgets

    from mappapp.process import Controller
    from mappapp.startup import settings

    parser = argparse.ArgumentParser()
    parser.add_argument('--ini', action='store', dest='ini_file', type=str)
    args = parser.parse_args(sys.argv[1:])

    from mappapp.startup.main import StartupConfiguration


    if sys.platform == 'win32':
        import wres

        # Set windows timer precision as high as possible
        minres, maxres, curres = wres.query_resolution()
        with wres.set_resolution(maxres):

            configfile = None

            if args.ini_file is not None:
                configfile = args.ini_file

            else:

                settings.winapp = QtWidgets.QApplication([])
                settings.startupwin = StartupConfiguration()
                settings.winapp.exec_()

                configfile = settings.configfile


            if configfile is None:
                print('No configuration selected. Exit.')
                exit()

            ctrl = Controller(configfile)
    else:
        print('Sorry, probably not gonna work on \"{}\"'.format(sys.platform))