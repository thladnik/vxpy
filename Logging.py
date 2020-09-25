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

import IPC

logger = None
write = None

DEBUG   = logging.DEBUG
INFO    = logging.INFO
WARN    = logging.WARN
WARNING = logging.WARNING
ERROR   = logging.ERROR

def setup_logger(_name):
    global logger, write
    # Set up logging
    h = logging.handlers.QueueHandler(IPC.Log.Queue)
    logger = logging.getLogger(_name)
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)
    write = logging.getLogger(_name).log