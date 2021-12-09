"""
MappApp ./Logging.py - Logging module required for setup of logging in individual processes
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
import logging
import logging.handlers
import os

from vxpy.Def import *
from vxpy import Def
from vxpy.Def import *
from vxpy.core import ipc

logger = None
write = None
debug = None
info = None
warning = None
error = None
critical = None

DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARN
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


def setup_log():
    logger = logging.getLogger('mylog')
    # Create logs folder if necessary
    if not os.path.exists(PATH_LOG):
        os.mkdir(PATH_LOG)
    h = logging.handlers.TimedRotatingFileHandler(os.path.join(PATH_LOG, ipc.Log.File.value), 'd')
    h.setFormatter(logging.Formatter('%(levelname)-8s %(asctime)s %(name)-12s  %(message)s'))
    logger.addHandler(h)

    return logger


def setup_log_queue(log):
    global logger, write, debug, info, warning, error, critical

    if logger is not None:
        return

    # Set shared attributes required for logging
    if log is not None:
        for lkey, log in log.items():
            setattr(ipc.Log, lkey, log)

    # Set up logger
    logger = logging.getLogger(ipc.Process.name)
    if not logger.handlers:
        h = logging.handlers.QueueHandler(ipc.Log.Queue)
        logger.addHandler(h)
        logger.setLevel(logging.DEBUG)
        write = logging.getLogger(ipc.Process.name).log
        debug = logging.getLogger(ipc.Process.name).debug
        info = logging.getLogger(ipc.Process.name).info
        warning = logging.getLogger(ipc.Process.name).warning
        error = logging.getLogger(ipc.Process.name).error
        critical = logging.getLogger(ipc.Process.name).critical