"""vxPy - vision Experiments in Python

Python package for visual stimulation in different display settings,
aquisition of multiple data streams and online data analysis.
"""
import importlib.metadata

import vxpy.configuration

metadata = importlib.metadata.metadata('vxpy')

__author__ = 'Tim Hladnik'
__contact__ = 'contact@vxpy.org'
__copyright__ = 'Copyright 2022, Tim Hladnik'
__credits__ = ['Yue Zhang']
__deprecated__ = False
__email__ = 'contact@vxpy.org'
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


def load_config_data_from_string(_config):

    _config_data = None

    # If _config is string, first try to evaluate as dictionary
    if isinstance(_config, str):

        try:
            _config_data = eval(_config)
        except:
            # If dictionary eval failed, try to load from path
            try:
                _config_data = vxpy.configuration.load_configuration(_config)
            except FileNotFoundError:
                print('ERROR: configuration file does not exist')
                sys.exit(1)

    # If _config is a dictionary, assume it contains the configuration
    elif isinstance(_config, dict):
        _config_data = _config

    return _config_data


def run(_config: Union[str, Dict[str, Any]] = None):
    """Run vxPy
    """

    # Get/load configuration data
    _config_data = load_config_data_from_string(_config)

    if _config_data is None:
        print(f'ERROR: invalid configuration. Config: {_config}, Config data: {_config_data}')
        sys.exit(1)

    # Set up controller
    from vxpy.modules import Controller

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

    # Start controller
    ctrl.start()

    # Save config if persistent
    if isinstance(_config, str):
        vxpy.configuration.save_configuration(_config)

    # Exit
    sys.exit(0)


def calibrate(_config_path: str = None):

    # Get/load configuration data
    # _config_data = load_config_data_from_string(_config)
    #
    # if _config_data is None:
    #     print(f'ERROR: invalid configuration. Config: {_config}, Config data: {_config_data}')
    #     sys.exit(1)

    from vxpy import calibration
    new_calibration = calibration.run_calibration_manager(_config_path)

    # TODO: Save calibration


def configure(_config_path: str = None):

    from vxpy import configuration

    # # Get/load configuration data
    # _config_data = load_config_data_from_string(_config)
    #
    # if _config_data is None:
    #     print(f'ERROR: invalid configuration. Config: {_config}, Config data: {_config_data}')
    #     sys.exit(1)

    vxpy.configuration.run_configuration_manager(_config_path)

    # new_configuration = run_configuration(_config_data['CALIBRATION_PATH'])

    # TODO: implement new configuration manager and save new config
