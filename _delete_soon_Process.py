import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.connection
import signal
import sys
from time import perf_counter

import Definition
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class BaseProcess:

    class Signals:
        UpdateProperty  = 10
        RPC             = 20
        Query           = 30
        Shutdown        = 99
        ConfirmShutdown = 100

    name      : str

    _running   : bool
    _shutdown  : bool

    _ctrlQueue : mp.Queue
    _logQueue  : mp.Queue
    _inPipe    : mp.connection.PipeConnection

    _pipes     : dict = dict()
    _processes : dict = dict()

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

        self.send(Definition.Process.Controller, BaseProcess.Signals.ConfirmShutdown)

    def main(self):
        """
        Event loop to be re-implemented in subclass
        :return:
        """
        pass

    def _startShutdown(self):
        # Handle all pipe messages before shutdown
        while self._inPipe.poll():
            self._handlePipe()

        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def send(self, processName, signal, *args, **kwargs):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        :param processName:
        :param data:
        :return: None
        """
        if self.name == Definition.Process.Controller:
            self._pipes[processName][0].send([signal, args, kwargs])
        else:
            self._ctrlQueue.put([self.name, processName, [signal, args, kwargs]])

    def rpc(self, processName, function, *args, **kwargs):
        self.send(processName, BaseProcess.Signals.RPC, function, *args, **kwargs)

    def registerProperty(self, propName):
        return
        self.rpc(Controller.Controller.name, Controller.Controller.connectProperty, propName, self.name)

    def _updateProperty(self, propName, propData):

        try:
            Logging.logger.log(logging.DEBUG, 'Set property <{}> to {}'.
                               format(propName, propData))
            setattr(self, propName, propData)
            self.send(Definition.Process.Controller, BaseProcess.Signals.UpdateProperty, propName, propData)
        except:
            Logging.logger.log(logging.WARNING, 'FAILED to set property <{}> to {}'.
                               format(propName, propData))

    def _executeRPC(self, fun, *args, **kwargs):
        try:
            Logging.logger.log(logging.DEBUG, 'RPC call to method {}() with params {}, {}'.
                               format(fun, args, kwargs))
            fun(self, *args, **kwargs)
        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'RPC call to method {}() failed with args {} and kwargs {} '
                                                '// Exception: {}'.
                                                format(fun, args, kwargs, exc))

    def _handlePipe(self, *args):  # needs *args for compatibility with Glumpy's schedule_interval

        # Poll pipe
        if not(self._inPipe.poll()):
            return

        msg = self._inPipe.recv()
        Logging.logger.log(logging.DEBUG, 'Received message: {}'.
                           format(msg))
        signal, args, kwargs = (msg[0], list(msg[1]), msg[2])

        if signal == BaseProcess.Signals.Shutdown:
            self._startShutdown()

        # RPC calls
        elif signal == BaseProcess.Signals.RPC:
            fun = args.pop(0)

            try:
                Logging.logger.log(logging.DEBUG, 'RPC call to method {} with args {} and kwargs {}'
                                   .format(fun, args, kwargs))
                fun(self, *args, **kwargs)
            except:
                Logging.logger.log(logging.WARNING, 'RPC call to method {} failed with args {} and kwargs {}'
                                   .format(fun, args, kwargs))

        # Set property
        elif signal == BaseProcess.Signals.UpdateProperty:
            propName = args[0]
            propData = args[1]

            try:
                Logging.logger.log(logging.DEBUG,
                                   'Set property <{}> to {}'
                                   .format(propName, str(propData)))
                setattr(self, propName, propData)
            except Exception as exc:
                Logging.logger.log(logging.WARNING,
                                   'Failed to set property <{}> to {} // Exception: {}'
                                   .format(propName, str(propData), exc))


    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)
