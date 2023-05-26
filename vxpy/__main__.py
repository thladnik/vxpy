"""CLI utility for vxPy
"""
import argparse
import sys

from vxpy.definitions import *


def path_from_args():
    return sys.argv[2] if len(sys.argv) > 2 else None


def get_parsed_arguments(args_in):

    command_choices = [CMD_RUN, CMD_CALIBRATE, CMD_CONFIGURE, CMD_SETUP, CMD_GETSAMPLES]

    parser = argparse.ArgumentParser(description='vxPy CLI')
    parser.add_argument(dest='command',
                        choices=command_choices,
                        metavar='',
                        help='Command to run. Available commands are: ' + ', '.join(command_choices))
    parser.add_argument('-c', '--config', dest='config', type=str,
                        help='Path to a configuration file or configuration dictionary')
    parser.add_argument('-r', '--root', dest='root', type=str,
                        help='Path to the current app folder.')
    parser.add_argument(f'--{CMD_MOD_NOSAMPLES}', dest='nosample', action='store_true')
    parser.add_argument(f'--force', dest='force', action='store_true')

    return parser.parse_args(args_in)


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
    elif parsed_args.command == CMD_CONFIGURE:

        from vxpy import configure
        configure(parsed_args.config)

    elif CMD_SETUP in sys.argv:
        from vxpy import setup

        root_path = parsed_args.root
        if root_path is None:
            root_path = '.'

        if not os.path.exists(root_path) and not parsed_args.force:
            print(f'ERROR: root path {root_path} does not exist.')
            print('Use option --force to create root path automatically')
            sys.exit(1)

        if len(os.listdir(root_path)) > 0 and not parsed_args.force:
            print('ERROR: root path for setup is not empty. Aborted')
            print('Use option --force to setup on this path regardless')
            sys.exit(1)

        # Prepare directory
        setup.patch_dir(use_path=root_path)

        # Setup files
        setup.setup_resources(use_path=root_path)

        # Download sample files for release (if not explicitly excluded)
        if not parsed_args.nosample:
            setup.download_samples(use_path=root_path)

    elif parsed_args.command == CMD_GETSAMPLES:
        from vxpy import setup

        # Get path if specified
        setup.download_samples(use_path=path_from_args())


if __name__ == '__main__':
    main()
