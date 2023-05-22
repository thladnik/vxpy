"""vxPy - vision Experiments in Python

Python package for visual stimulation in different display settings,
aquisition of multiple data streams and online data analysis.
"""
import importlib.metadata

__author__ = 'Tim Hladnik'
__contact__ = 'tim.hladnik@gmail.com'
__copyright__ = 'Copyright 2022, Tim Hladnik'
__credits__ = ['Yue Zhang']
__deprecated__ = False
__email__ = 'tim.hladnik@gmail.com'
__license__ = 'GPLv3'
__maintainer__ = 'Tim Hladnik'
__status__ = 'Alpha'
__version__ = importlib.metadata.version('vxpy')

import os
import sys
from typing import Any, Dict, Union


# Check this version is a cloned repo and add commit hash to version
def get_version():

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

    except:
        return __version__

    else:
        # Append to version
        return f'{__version__}-{commit_hash[:8]}'


def get_cli_config():
    # CLI start requires at least a configuration file path
    if len(sys.argv) < 2:
        print('ERROR: no configuration provided')
        sys.exit(1)

    print(f'Script path: {sys.argv[0]}')
    print(f'Add {os.getcwd()} to path')
    sys.path.append(os.getcwd())

    # Set config path
    _config = sys.argv[1]

    return _config


def run(_config: Union[str, Dict[str, Any]] = None):

    from vxpy import config
    import vxpy.core.configuration as vxconfig
    from vxpy.modules import Controller

    # For CLI starts
    if _config is None:
        _config = get_cli_config()

    if isinstance(_config, str):
        try:
            _config_data = vxconfig.load_configuration(_config)
        except FileNotFoundError:
            print('ERROR: configuration file does not exist')
            sys.exit(1)

    elif isinstance(_config, dict):
        _config_data = _config
    else:
        print(f'ERROR: invalid configuration of type {type(_config)}')
        sys.exit(1)

    if sys.platform == 'win32':
        # Set windows timer precision as high as possible
        try:
            import wres
        except ImportError as exc:
            print(f'WARNING: Unable to import wres. '
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


def calibrate(_config: Union[str, Dict[str, Any]] = None):

    from vxpy.core import configuration

    # CLI start
    if _config is None:
        _config = get_cli_config()



    from vxpy.calibration_manager import run_calibration

    run_calibration(_config_data)


def configure(_config: Union[str, Dict[str, Any]] = None):
    pass
