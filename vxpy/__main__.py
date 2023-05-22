"""CLI utility for vxPy
"""
import argparse
import sys

from vxpy.definitions import *


def path_from_args():
    return sys.argv[2] if len(sys.argv) > 2 else None


def get_parsed_arguments(args_in):

    parser = argparse.ArgumentParser(description='vxPy CLI')
    parser.add_argument('command',
                        choices=[CMD_RUN, CMD_CALIBRATE, CMD_CONFIGURE, CMD_SETUP, CMD_GETSAMPLES],
                        help='Command to run')
    parser.add_argument('-c', '--config', dest='config', type=str,
                        help='Path to a configuration file or configuration dictionary')
    parser.add_argument('-p', '--path', dest='config', type=str,
                        help='Path to the current app folder.')

    return parser.parse_args(args_in)


def run():
    sys.argv.append(CMD_RUN)
    main()


def calibrate():
    sys.argv.append(CMD_CALIBRATE)
    main()


def configure():
    sys.argv.append(CMD_CONFIGURE)
    main()


def main():

    # Parse arguments
    parsed_args = get_parsed_arguments(sys.argv[1:])

    # Add current working directory to path (required for direct entry point)
    sys.path.append(os.getcwd())

    # Run
    if parsed_args.command == CMD_RUN:

        if parsed_args.config is None:
            print('ERROR: no configuration path specified')
            sys.exit(1)

        from vxpy import run
        run(parsed_args.config)

    # Calibrate calibration for current configuration
    elif parsed_args.command == CMD_CALIBRATE:

        from vxpy import calibrate
        calibrate(parsed_args.config)

    # Configure program
    elif parsed_args.command == CMD_CALIBRATE:

        from vxpy import configure
        configure(parsed_args.config)

    elif CMD_PATCHDIR in sys.argv:
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

    elif CMD_HELP in sys.argv:

        print('vxPy - vision experiments in Python')
        print('Available commands:')

        print(f'{CMD_SETUP}'
              f'\n  create a new, clean application directory in the '
              f'specified base folder (uses current folder by default)'
              f'\n  Options:'
              f'\n    {CMD_MOD_NOSAMPLES}: skip download of binary sample files')

        print(f'{CMD_RUN}'
              f'\n  Run vxPy for specified configuration file')

        print(f'{CMD_PATCHDIR}'
              f'\n  create missing folders in specified application base folder (uses current folder by default)')

        print(f'{CMD_GETSAMPLES}'
              f'\n  download binary sample files to specified base folder (uses current folder by default)')

        print(f'{CMD_CONFIGURE}'
              f'\n  Run configuration UI for specified configuration file')

        print(f'{CMD_CALIBRATE}'
              f'\n  Run display calibration UI for specified configuration file')

    elif CMD_MIGRATE in sys.argv:
        pass

    else:

        print(f'No command specified. Run "vxpy {CMD_HELP}" for more information on usage.')


if __name__ == '__main__':
    main()
