"""Logging utilities for vxPy.

Provides helpers to configure a shared multiprocessing log queue, an optional
log history list, and a rotating file logger.  All loggers created via
:func:`getLogger` are automatically routed through the queue once
:func:`add_handlers` is called.
"""
import logging
import logging.handlers
import multiprocessing as mp


_log_queue: mp.Queue = None
_log_history: list = None
_file_logger: logging.Logger = None


def setup_log_queue(log_queue):
    """Setup log queue.
    
    Parameters
    ----------
    log_queue : Any
        Description.
    """
    global _log_queue
    _log_queue = log_queue


def setup_log_history(log_history):
    """Setup log history.
    
    Parameters
    ----------
    log_history : Any
        Description.
    """
    global _log_history
    _log_history = log_history


def add_to_history(record):
    """Add to history.
    
    Parameters
    ----------
    record : Any
        Description.
    """
    global _log_history
    _log_history.append(record)


def add_to_file(record):
    """Add to file.
    
    Parameters
    ----------
    record : Any
        Description.
    """
    global _file_logger
    _file_logger.handle(record)


def get_queue():
    """Get queue.
    """
    global _log_queue
    return _log_queue


def get_history():
    """Get history.
    """
    global _log_history
    return _log_history


def setup_log_to_file(filepath) -> logging.Handler:
    """Setup log to file.
    
    Parameters
    ----------
    filepath : Any
        Description.
    
    Returns
    -------
    logging.Handler
        Description.
    """
    global _file_logger
    if _file_logger is None:
        _file_logger = logging.getLogger('filelogger')

    # Set file handler
    h = logging.handlers.TimedRotatingFileHandler(filepath, 'd')
    h.setFormatter(logging.Formatter('%(levelname)-7s %(asctime)s %(name)-40s %(message)s'))
    _file_logger.addHandler(h)
    return h


def remove_log_to_file(h: logging.Handler):
    """Remove log to file.
    
    Parameters
    ----------
    h : logging.Handler
        Description.
    """
    global _file_logger

    _file_logger.removeHandler(h)


def getLogger(name) -> logging.Logger:
    """Getlogger.
    
    Parameters
    ----------
    name : Any
        Description.
    
    Returns
    -------
    logging.Logger
        Description.
    """
    global _log_queue
    log = logging.getLogger(name)

    return log


def add_handlers():
    """Add handlers.
    """
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
