"""
MappApp ./process/Logger.py - Logger process which evaluates inputs to the log queue from all sources.
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
from time import strftime, sleep

import Controller
import Def
import IPC
import Logging

class Main(Controller.AbstractProcess):
    name = Def.Process.Logger

    def __init__(self, **kwargs):
        Controller.AbstractProcess.__init__(self, **kwargs)

        ### Set file to log to
        if IPC.Buffer.Logfile.value == '':
            IPC.Buffer.Logfile.value = '%s.log' % strftime('%Y-%m-%d-%H-%M-%S')

        ### Set up logger, formatte and handler
        self.logger = logging.getLogger('mylog')
        h = logging.handlers.TimedRotatingFileHandler(os.path.join(Def.Path.Log, IPC.Buffer.Logfile.value), 'd')
        f = logging.Formatter('%(asctime)s <<>> %(name)-10s <<>> %(levelname)-8s <<>> %(message)s <<')
        h.setFormatter(f)
        self.logger.addHandler(h)

        ### Run event loop
        self.run()

    def main(self):
        ### Check queue
        if self._logQueue.empty():
            return

        ### Fetch next record
        record = self._logQueue.get()

        ### Development mode: write to console
        if Def.Env == Def.EnvTypes.Dev:
            print('{:10s} {:15s} {}'.format(record.levelname, record.name, record.message))
            return

        ### Production mode: write to file
        try:
            self.logger.handle(record)
        except Exception:
            import sys, traceback
            print('Exception in Logger:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        ### Wait for a bit (reduce CPU load)
        sleep(0.05)

    def _startShutdown(self):
        ### Wait for other processes to finish first and then clear the log queue
        sleep(.5)

        ### Process queued log messages
        while not(self._logQueue.empty()):
            self.logger.handle(self._logQueue.get())

        ### Finally shut down
        Controller.AbstractProcess._startShutdown(self)
