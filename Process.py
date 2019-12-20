import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.connection
import signal
import sys
from time import perf_counter

import Definition
import Logging

class BaseProcess:

    class Signals:
        UpdateProperty  = 10
        RPC             = 20
        Query           = 30
        Shutdown        = 99
        ConfirmShutdown = 100

    name     : str

    _running  : bool
    _shutdown : bool

    _ctrlQueue: mp.Queue
    _logQueue:  mp.Queue
    _inPipe:    mp.connection.PipeConnection

    def __init__(self, **kwargs):
        """
        Kwargs should contain at least
          _ctrlQueue
          _logQueue
          _inPipe
        for basic communication and logging in sub processes (Controller does not require _inPipe)

        Known further kwargs are:
          _cameraBO (multiple instances)
          _app (GUI)
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Setup logging
        Logging.setupLogger(self._logQueue, self.name)

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

        self._sendToCtrl(BaseProcess.Signals.ConfirmShutdown)

    def main(self):
        """
        Event loop to be re-implemented in subclass
        :return:
        """
        pass

    def _startShutdown(self):
        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def _queryPropertyFromCtrl(self, propName, callback=None):
        self._sendToCtrl(BaseProcess.Signals.Query, propName, callback=callback)

    def _sendToProcess(self, targetName, signal, *args, **kwargs):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        :param targetName:
        :param data:
        :return: None
        """
        self._ctrlQueue.put([self.name, targetName, [signal, args, kwargs]])

    def _rpcToProcess(self, targetName, function, *args, **kwargs):
        self._sendToProcess(targetName, BaseProcess.Signals.RPC, function, *args, **kwargs)

    def _rpcToCtrl(self, function, *args, **kwargs):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._sendToCtrl(BaseProcess.Signals.RPC, function, *args, **kwargs)

    def _sendToCtrl(self, signal, *args, **kwargs):
        """
        Convenience function to handle queueing of messages to Controller
        :param data: message to be put in queue
        :return: None
        """
        self._sendToProcess(Definition.Process.Controller, signal, *args, **kwargs)

    def updateProperty(self, propName, propData):
        setattr(self, propName, propData)

    def _updateProperty(self, propName, propData):
        try:
            setattr(self, propName, propData)
            self._sendToCtrl(BaseProcess.Signals.UpdateProperty, propName, propData)
        except:
            pass
            #malog.logger.log(logging.WARNING, 'FAILED to set property <{}> to {}'.format(propName, data))
        else:
            pass
            #malog.logger.log(logging.DEBUG, 'Set property <{}> to {}'.format(propName, data))
        finally:
            return

    def _handlePipe(self, *args):  # needs *args for compatibility with Glumpy's schedule_interval

        # Poll pipe
        t = perf_counter()
        if not(self._inPipe.poll()):
            return

        msg = self._inPipe.recv()

        if msg[0] == BaseProcess.Signals.Shutdown:
            self._startShutdown()

        # RPC calls
        elif msg[0] == BaseProcess.Signals.RPC:
            args = list(msg[1])
            kwargs = msg[2]
            fun = args.pop(0)

            try:
                fun(self, *args, **kwargs)
            except:
                Logging.logger.log(logging.WARNING, 'RPC call to method {} failed'.format(fun))
            else:
                Logging.logger.log(logging.DEBUG, 'RPC call to method {}'.format(fun))

        # Set property
        elif msg[0] == BaseProcess.Signals.UpdateProperty:
            self.updateProperty(*msg[1], **msg[2])


    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)
