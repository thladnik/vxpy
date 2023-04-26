"""Package for visual stimulation and concurrent behavioral analysis

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

__author__ = 'Tim Hladnik'
__contact__ = 'tim.hladnik@gmail.com'
__copyright__ = 'Copyright 2022, Tim Hladnik'
__credits__ = ['Yue Zhang']
__deprecated__ = False
__email__ = 'tim.hladnik@gmail.com'
__license__ = 'GPLv3'
__maintainer__ = 'developer'
__status__ = 'Production'
__version__ = '0.1.0'

import os
import sys


# Check this version is a cloned repo and add commit hash to version
try:
    # Import gitpython here, because dependency is not installed during setup
    import git

    # Load repository (if available)
    if sys.platform == 'linux':
        path = os.path.join(*__path__[0].split(os.sep)[:-1])
        repo = git.Repo(f'{os.sep}{path}')
    elif sys.platform == 'win32':
        parts = __path__[0].split(os.sep)
        path = f'{parts[0]}\\{os.path.join(*parts[1:-1])}'
        repo = git.Repo(path)
    else:
        raise NotImplementedError('No solution for this platform')

    # Get current HEAD
    commit_hash = repo.git.rev_parse('HEAD')

    # Append to version
    __version__ += f'-{commit_hash[:8]}'

except:
    pass


def main(configfile):

    from vxpy.modules import Controller

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
