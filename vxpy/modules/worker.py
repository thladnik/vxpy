"""
MappApp ./modules/worker.py
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

from time import time
import importlib

from vxpy import definitions
from vxpy.definitions import *
from vxpy.core import process, logger

log = logger.getLogger(__name__)


class Worker(process.AbstractProcess):
    name = PROCESS_WORKER

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        self._task_intervals = list()
        self._scheduled_times = list()
        self._scheduled_tasks = list()
        self._tasks = dict()

        # Run event loop
        self.run(interval=1./10)

    def _load_task(self, task_name):
        if not(task_name in self._tasks):
            module = '.'.join([PATH_TASKS,task_name])
            try:
                log.debug(f'Import task {module}')
                self._tasks[task_name] = importlib.import_module(module)
            except:
                log.warning(f'Failed to import task {module}')

        return self._tasks[task_name]

    def schedule_task(self, task_name, task_interval=1./2):
        self._scheduled_tasks.append(task_name)
        self._scheduled_times.append(time() + task_interval)
        self._task_intervals.append(task_interval)

    def run_task(self, task_name, *args, **kwargs):
        self._load_task(task_name).run(*args, **kwargs)

    def main(self):

        self.update_routines()
