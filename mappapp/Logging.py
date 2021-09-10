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

from mappapp import Def
from mappapp import IPC

logger = None
write = None

DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARN
WARNING = logging.WARNING
ERROR = logging.ERROR


def setup_log():
    logger = logging.getLogger('mylog')
    h = logging.handlers.TimedRotatingFileHandler(os.path.join(Def.package, Def.Path.Log, IPC.Log.File.value), 'd')
    h.setFormatter(logging.Formatter('%(asctime)s <<>> %(name)-10s <<>> %(levelname)-8s <<>> %(message)s <<'))
    logger.addHandler(h)

    return logger


def setup_log_queue(log):
    global logger, write

    # Set shared attributes required for logging
    if log is not None:
        for lkey, log in log.items():
            setattr(IPC.Log, lkey, log)

    # Set up logger
    logger = logging.getLogger(IPC.Process.name)
    if not logger.handlers:
        h = logging.handlers.QueueHandler(IPC.Log.Queue)
        logger.addHandler(h)
        logger.setLevel(logging.DEBUG)
        write = logging.getLogger(IPC.Process.name).log