import logging
import logging.handlers
import os
from time import strftime

import Process
import Definition

class Logger(Process.BaseProcess):

    name = Definition.Process.Logger

    def __init__(self, **kwargs):
        Process.BaseProcess.__init__(self, **kwargs)
        self._logQueue = kwargs['_logQueue']

        root = logging.getLogger()
        filename = '%s.log' % strftime('%Y-%m-%d')
        h = logging.handlers.TimedRotatingFileHandler(os.path.join(Definition.Path.Log, filename), 'd')
        f = logging.Formatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s')
        h.setFormatter(f)
        root.addHandler(h)

        self.run()

    def main(self):
        if not(self._logQueue.empty()):
            try:
                record = self._logQueue.get()
                logger = logging.getLogger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!
            except Exception:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)