import logging
import logging.handlers

logQueue = None
logger = None

def setupLogger(_logQueue, _name):
    if logQueue is not None:
        return
    globals()['logQueue'] = _logQueue

    # Set up logging
    h = logging.handlers.QueueHandler(globals()['logQueue'])
    root = logging.getLogger(_name)
    root.addHandler(h)
    root.setLevel(logging.DEBUG)
    globals()['logger'] = logging.getLogger(_name)