"""
"""
import sys

from vxpy.definitions import *


def path_from_args():
    return sys.argv[2] if len(sys.argv) > 2 else None


if __name__ == '__main__':

    if CMD_PATCHDIR in sys.argv:
        from vxpy import setup

        setup.patch_dir(use_path=path_from_args())

    elif CMD_SETUP in sys.argv:
        from vxpy import setup

        setup.setup_resources(use_path=path_from_args())

        # Download sample files for release
        if CMD_MOD_NOSAMPLES not in sys.argv:
            setup.download_samples(use_path=path_from_args())

    elif CMD_GETSAMPLES in sys.argv:
        from vxpy import setup

        # Get path if specified
        setup.download_samples(use_path=path_from_args())

    elif CMD_CONFIGURE in sys.argv:
        from vxpy.configure import main

        # Run configuration
        main()

    elif CMD_CALIBRATE in sys.argv:
        from vxpy.calibration_manager import run_calibration

        run_calibration()

    elif CMD_HELP in sys.argv:

        print('\nAvailable commands:')

        print(f'\n{CMD_SETUP}'
              f'\n\tcreate a new, clean application directory in the '
              f'specified base folder (uses current folder by default)'
              f'\n\n\tOptions'
              f'\n\t\t{CMD_MOD_NOSAMPLES}: skip download of binary sample files')

        print(f'\n{CMD_PATCHDIR}'
              f'\n\tcreate missing folders in specified application base folder (uses current folder by default)')

        print(f'\n{CMD_GETSAMPLES}'
              f'\n\tdownload binary sample files to specified base folder (uses current folder by default)')

        print(f'\n{CMD_CONFIGURE}'
              f'\n\tRun configuration UI for specified configuration file')

        print(f'\n{CMD_CALIBRATE}'
              f'\n\tRun display calibration UI for specified configuration file')

    elif CMD_MIGRATE in sys.argv:
        pass

    else:

        print(f'No command specified. Run "vxpy {CMD_HELP}" for more information on usage.')
