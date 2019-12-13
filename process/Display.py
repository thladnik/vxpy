
from time import sleep

from process.Base import BaseProcess
import MappApp_Definition as madef

######
# Worker processes

class Display(BaseProcess):

    _name = madef.Process.Display.name

    def __init__(self, **kwargs):
        BaseProcess.__init__(self, **kwargs)

        self.run()

    def main(self):
        while self._isRunning():
            # Look in pipe for new data
            action = self._handlePipe()

            if action is not None:
                # Take further actions
                pass


            sleep(0.1)

    # RPC calls
    pass