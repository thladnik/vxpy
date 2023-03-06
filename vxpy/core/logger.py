"""
vxPy ./core/logger.py
Copyright (C) 2022 Tim Hladnik

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
import multiprocessing as mp

from vxpy.definitions import *

_log_queue: mp.Queue = None
_log_history: list = None
_file_logger: logging.Logger = None


def setup_log_queue(log_queue):
    global _log_queue
    _log_queue = log_queue


def setup_log_history(log_history):
    global _log_history
    _log_history = log_history


def add_to_history(record):
    global _log_history
    _log_history.append(record)


def add_to_file(record):
    global _file_logger
    _file_logger.handle(record)


def get_queue():
    global _log_queue
    return _log_queue


def get_history():
    global _log_history
    return _log_history


def setup_log_to_file(filepath) -> logging.Handler:
    global _file_logger
    if _file_logger is None:
        _file_logger = logging.getLogger('filelogger')

    # Set file handler
    h = logging.handlers.TimedRotatingFileHandler(filepath, 'd')
    h.setFormatter(logging.Formatter('%(levelname)-7s %(asctime)s %(name)-40s %(message)s'))
    _file_logger.addHandler(h)
    return h


def remove_log_to_file(h: logging.Handler):
    global _file_logger

    _file_logger.removeHandler(h)


def getLogger(name) -> logging.Logger:
    global _log_queue
    log = logging.getLogger(name)

    return log


def add_handlers():
    global _log_queue
    for name in logging.root.manager.loggerDict:
        log = logging.getLogger(name)

        # If handler is already set, skip
        if log.handlers:
            continue

        # Important: avoids repeated handling through hierarchy
        log.propagate = False

        if not log.handlers and _log_queue is not None:
            h = logging.handlers.QueueHandler(_log_queue)
            log.addHandler(h)
            log.setLevel(logging.DEBUG)
