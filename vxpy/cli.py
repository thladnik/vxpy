import argparse

from vxpy.definitions import *


# TODO: implement universal interface for manually parsed startup
#  and entry point startup

def parse_arguments():

    parser = argparse.ArgumentParser(description='vxPy CLI')
    parser.add_argument('filename')
    parser.add_argument('command',
                        choices=[CMD_RUN, CMD_CALIBRATE, CMD_CONFIGURE, CMD_SETUP, CMD_GETSAMPLES],
                        help='Command to run')
    parser.add_argument('-c', '--config', dest='config', type=str,
                        help='Path to a configuration file or configuration dictionary')

    return parser.parse_args(sys.argv)


if __name__ == '__main__':

    import sys
    args = parse_arguments()
    print(args)
