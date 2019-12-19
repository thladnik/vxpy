import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.connection as mpconn
import signal
import sys
from time import perf_counter

import MappApp_Definition as madef
import MappApp_Helper as mahelp
import MappApp_Logging as malog

class BaseProcess:

    _name = None

    _running = None
    _shutdown = None

    def __init__(self,
                 _ctrlQueue: mp.Queue=None,
                 _logQueue: mp.Queue = None,
                 _inPipe: mpconn.PipeConnection = None,
                 **kwargs):
        self._ctrlQueue = _ctrlQueue
        self._logQueue = _logQueue
        self._inPipe = _inPipe

        # Setup logging
        malog.setupLogger(self._logQueue, self._name)

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
            try:
                setattr(self, propName, data)
            except:
                pass
                #malog.logger.log(logging.WARNING, 'FAILED to set property <{}> to {}'.format(propName, data))
            else:
                pass
                #malog.logger.log(logging.DEBUG, 'Set property <{}> to {}'.format(propName, data))
            finally:
                return
        #malog.logger.log(logging.WARNING, 'Property <{}> does not exist.'.format(propName))



    def _handlePipe(self, *args):  # needs *args for compatibility with glumpy schedule_interval

        # Poll pipe and (optionally) wait for a number of iterations
        t = perf_counter()
        if not(self._inPipe.poll()):
            return

        msg = self._inPipe.recv()

        # RPC calls
        if msg[0] == madef.Process.Signal.rpc:
            #malog.logger.log(logging.DEBUG, 'Calling method {}'.format(msg[1]))
            mahelp.rpc(self, msg[1:])

        # Set property
        elif msg[0] == madef.Process.Signal.setProperty:
            self._setProperty(*msg[1:])


    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)
