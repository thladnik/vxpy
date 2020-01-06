import logging
import logging.handlers
import os
from time import strftime, sleep

import Controller
import Definition
import Logging

class Main(Controller.BaseProcess):
    name = Definition.Process.Logger

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(self, **kwargs)

        ### Set up logger
        self.logger = logging.getLogger('mylog')
        filename = '%s.log' % strftime('%Y-%m-%d-%H-%M-%S')
        h = logging.handlers.TimedRotatingFileHandler(os.path.join(Definition.Path.Log, filename), 'd')
        f = logging.Formatter('%(asctime)s <<>> %(name)-20s <<>> %(levelname)-8s <<>> %(message)s <<')
        h.setFormatter(f)
        self.logger.addHandler(h)

        self._updateProperty('_logFilename', filename)

        ### Run event loop
        self.run()

    def main(self):
        if self._logQueue.empty():
            return

        ### Fetch next record
        record = self._logQueue.get()

        ### Development mode: write to console
        if Definition.Env == Definition.EnvTypes.Dev:
            print('{:10s} {:15s} {}'.format(record.levelname, record.name, record.message))
            return

        ### Production mode: write to file
        try:
            self.logger.handle(record)
        except Exception:
            import sys, traceback
            print('Exception in Logger:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        sleep(0.05)