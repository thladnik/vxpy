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
import sys

from definitions import *

if __name__ == '__main__':

    if CMD_PATCHDIR in sys.argv:
        from vxpy import setup
        setup.patch_dir()

    if CMD_SETUP in sys.argv:
        from vxpy import setup
        setup.setup_resources()

        # Download sample files for release
        if CMD_MOD_NOSAMPLES not in sys.argv:
            setup.download_samples()

    elif CMD_GETSAMPLES in sys.argv:
        from vxpy import setup
        setup.download_samples()

    elif CMD_CONFIGURE in sys.argv:
        from vxpy.configure import main
        main()

    elif CMD_CALIBRATE in sys.argv:
        from vxpy.calibration_manager import run_calibration
        run_calibration()

    elif CMD_MIGRATE:
        pass
        # TODO: migrate current application folder to more recent version (mainly setup resource files?)

    # parser = argparse.ArgumentParser()
    # parser.add_argument('--ini', action='store', dest='ini_file', type=str)
    # parsed_args = parser.parse_args(sys.argv[1:])

    # main()