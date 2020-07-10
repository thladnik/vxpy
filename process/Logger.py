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

import Process
import Def
import IPC
import Logging

class Main(Process.AbstractProcess):
    name = Def.Process.Logger

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        ### Set file to log to
        if IPC.Log.File.value == '':
            IPC.Log.File.value = '%s.log' % strftime('%Y-%m-%d-%H-%M-%S')

        ### Set up logger, formatte and handler
        self.logger = logging.getLogger('mylog')
        h = logging.handlers.TimedRotatingFileHandler(os.path.join(Def.Path.Log, IPC.Log.File.value), 'd')
        f = logging.Formatter('%(asctime)s <<>> %(name)-10s <<>> %(levelname)-8s <<>> %(message)s <<')
        h.setFormatter(f)
        self.logger.addHandler(h)

        ### Run event loop
        self.run(interval=0.1)

    def main(self):
        sleep(1)
        return
        ### Check queue
        if IPC.Log.Queue.empty():
            return

        ### Fetch next record
        record = IPC.Log.Queue.get()

        ### Development mode: write to console
        if Def.Env == Def.EnvTypes.Dev:
            print('{:10s} {:15s} {}'.format(record.levelname, record.name, record.message))
            return

        ### Production mode: write to file
        try:
            self.logger.handle(record)
            IPC.Log.History.append(record)
        except Exception:
            import sys, traceback
            print('Exception in Logger:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


    def _startShutdown(self):
        ### Wait for other processes to finish first and then clear the log queue
        sleep(.5)

        ### Process queued log messages
        while not(IPC.Log.Queue.empty()):
            self.logger.handle(IPC.Log.Queue.get())

        ### Finally shut down
        Process.AbstractProcess._startShutdown(self)
