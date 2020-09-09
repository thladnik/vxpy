"""
MappApp ./process/Worker.py - Worker process which can be employed for
continuous or scheduled execution of functions.
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

from time import sleep, time
import importlib
import logging
import os

import Process
import Def
import Logging

class Worker(Process.AbstractProcess):
    name = Def.Process.Worker

    def __init__(self, **kwargs):
        Process.AbstractProcess.__init__(self, **kwargs)

        self._task_intervals = list()
        self._scheduled_times = list()
        self._scheduled_tasks = list()
        self._tasks = dict()

        ### Run event loop
        self.run(interval=0.5)

    def _loadTask(self, task_name):
        if not(task_name in self._tasks):
            module = '.'.join([Def.Path.Task, task_name])
            try:
                Logging.write(logging.DEBUG, 'Import task {}'.format(module))
                self._tasks[task_name] = importlib.import_module(module)
            except:
                Logging.write(logging.WARNING, 'Failed to import task {}'.format(module))

        return self._tasks[task_name]

    def scheduleTask(self, task_name, task_interval=1. / 2):
        self._scheduled_tasks.append(task_name)
        self._scheduled_times.append(time() + task_interval)
        self._task_intervals.append(task_interval)

    def runTask(self, task_name, *args, **kwargs):
        self.setState(Def.State.RUNNING)
        self._loadTask(task_name).run(*args, **kwargs)
        self.setState(Def.State.IDLE)

    def main(self):
        for i, task_name, task_time, task_interval in enumerate(zip(self._scheduled_tasks,
                                                                    self._scheduled_times,
                                                                    self._task_intervals)):
            ### If scheduled time is now
            if task_time <= time():
                Logging.write(logging.DEBUG, 'Run task {}'.format(task_time))

                # Run
                self.runTask(task_name)

                ## Set next time
                task_idx = self._scheduled_tasks.index(task_name)
                self._scheduled_times[task_idx] = time() + self._task_intervals[task_idx]
