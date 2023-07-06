"""Recorder process module
"""

from vxpy import definitions
from vxpy.definitions import *
from vxpy.core import process, logger

log = logger.getLogger(__name__)


class Recorder(process.AbstractProcess):
    name = PROCESS_RECORDER

    def __init__(self, **kwargs):
        process.AbstractProcess.__init__(self, **kwargs)

        # Run event loop
        self.run(interval=1./50)

    def main(self):

        self.update_routines()
