"""vxPy - vision Experiments in Python

Python package for visual stimulation in different display settings,
aquisition of multiple data streams and online data analysis.
"""

__author__ = 'Tim Hladnik'
__contact__ = 'tim.hladnik@gmail.com'
__copyright__ = 'Copyright 2022, Tim Hladnik'
__credits__ = ['Yue Zhang']
__deprecated__ = False
__email__ = 'tim.hladnik@gmail.com'
__license__ = 'GPLv3'
__maintainer__ = 'Tim Hladnik'
__status__ = 'Production'
__version__ = '0.1.0'

import os
import sys
from typing import Dict, Union

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


def main(_config: Union[str, Dict]):

    from vxpy import config
    import vxpy.core.configuration as vxconfig
    from vxpy.modules import Controller

    if isinstance(_config, str):
        _config_data = vxconfig.load_configuration(_config)
    elif isinstance(_config, dict):
        _config_data = _config
    else:
        print(f'ERROR: invalid configuration of type {type(_config)}')
        sys.exit(-1)

    if sys.platform == 'win32':
        # Set windows timer precision as high as possible
        try:
            import wres
        except ImportError as exc:
            print(f'Unable to import wres. '
                  f'Please consider installing wres for better performance on {sys.platform} platform')
            ctrl = Controller(_config_data)
        else:
            minres, maxres, curres = wres.query_resolution()
            with wres.set_resolution(maxres):
                ctrl = Controller(_config_data)

    elif sys.platform == 'linux':
        ctrl = Controller(_config_data)

    else:
        print(f'Platform {sys.platform} not supported')
        sys.exit(1)

    # Run controller
    ctrl.start()

    # Save config if persistent
    if isinstance(_config, str):
        vxconfig.save_configuration(_config)

    # Exit
    sys.exit(0)
