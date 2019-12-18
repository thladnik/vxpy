import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.connection as mpconn
import pprint
import signal
import sys
from time import perf_counter

import MappApp_Definition as madef
from MappApp_Helper import rpc

class BaseProcess:

    _name = None

    _running = None
    _shutdown = None

    def __init__(self, _ctrlQueue: mp.Queue=None, _logQueue: mp.Queue = None, _inPipe: mpconn.PipeConnection = None):
        self._ctrlQueue = _ctrlQueue
        self._logQueue = _logQueue
        self._inPipe = _inPipe

        # Set up logging
        h = logging.handlers.QueueHandler(self._logQueue)  # Just the one handler needed
        root = logging.getLogger(self._name)
        root.addHandler(h)
        # send all messages, for demo; no other level or filter logic applied.
        root.setLevel(logging.DEBUG)
        self.logger = logging.getLogger(self._name)

        # Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)

    def run(self):
        self._running = True
        self._shutdown = False

        # Run event loop
        self.t = perf_counter()
        while self._isRunning():
            self._handlePipe()
            self.main()
            self.t = perf_counter()

        self._sendToCtrl(madef.Process.State.stopped)

    def main(self):
        """
        Event loop to be re-implemented in subclass
        :return:
        """
        pass

    def _registerPropWithCtrl(self):
        pass

    def _start_shutdown(self):
        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def _queryPropertyFromCtrl(self, propName, callback=None):
        self._sendToCtrl([madef.Process.Signal.query, propName, callback])

    def _rpcToProcess(self, process, function, *args, **kwargs):
        self._sendToProcess(process, [madef.Process.Signal.rpc, function, args, kwargs])

    def _rpcToCtrl(self, function, *args, **kwargs):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._rpcToProcess(madef.Process.Controller, function, *args, **kwargs)

    def _sendToProcess(self, process, data):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        :param process:
        :param data:
        :return: None
        """
        self._ctrlQueue.put([self._name, process.name, data])

    def _sendToCtrl(self, data):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._sendToProcess(madef.Process.Controller, data)

    def _setProperty(self, propName, data):
        if hasattr(self, propName):
            setattr(self, propName, data)
            self.logger.log(logging.DEBUG, '> Process <%s> set property <%s>:' % (self._name, propName))
            pprint.pprint(data)
            return
        self.logger.log(logging.DEBUG, '> Process <%s> FAIL to set property <%s>:' % (self._name, propName))
        pprint.pprint(data)



    def _handlePipe(self, *args):  # needs *args for compatibility with glumpy schedule_interval

        # Poll pipe and (optionally) wait for a number of iterations
        t = perf_counter()
        if not(self._inPipe.poll()):
            return

        obj = self._inPipe.recv()

        # RPC calls
        if obj[0] == madef.Process.Signal.rpc:
            rpc(self, obj[1:])

        # Set property
        elif obj[0] == madef.Process.Signal.setProperty:
            self._setProperty(*obj[1:])


    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)
