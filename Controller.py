"""
MappApp ./Controller.py - Base process and controller class called to start program.
Controller spawns all sub processes.
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

import ctypes
import logging
import multiprocessing as mp
import multiprocessing.connection
import signal
import sys
import time

import Buffers
import Config
import Definition
from helper import Basic
import IPC
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    pass

##################################
## Process BASE class

class BaseProcess:
    name       : str

    class Signals:
        UpdateProperty  = 10
        RPC             = 20
        Query           = 30
        Shutdown        = 99
        ConfirmShutdown = 100

    _running   : bool
    _shutdown  : bool

    _ctrlQueue : mp.Queue
    _logQueue  : mp.Queue
    _inPipe    : mp.connection.PipeConnection

    ## Controller exclusives
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
          _app (GUI)
        """
        for key, value in kwargs.items():

            # Set configuration dictionaries (managed dicts)
            if key == '_configuration':
                for ckey, config in value.items():
                    setattr(Config, ckey, config)

            # Set state dictionaries (managed dicts)
            if key == '_states':
                for skey, state in value.items():
                    setattr(IPC.State, skey, state)

            if key == '_buffers':
                for bkey, buffer in value.items():
                    setattr(IPC.Buffer, bkey, buffer)

            # Set base process class attribute
            else:
                setattr(self, key, value)

        ### Set process state
        if getattr(IPC.State, self.name) is not None:
            getattr(IPC.State, self.name).value = Definition.State.starting

        ### Setup logging
        Logging.setupLogger(self._logQueue, self.name)

        ### Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)

    def run(self):
        Logging.logger.log(logging.INFO, 'Run {}'.format(self.name))
        ### Set state to running
        self._running = True
        self._shutdown = False

        ### Set process state
        if getattr(IPC.State, self.name) is not None:
            getattr(IPC.State, self.name).value = Definition.State.idle

        ### Run event loop
        self.t = time.perf_counter()
        while self._isRunning():
            self._handleInbox()
            self.main()
            self.t = time.perf_counter()

    def main(self):
        """Event loop to be re-implemented in subclass
        """
        NotImplementedError('Event loop of base process class is not implemented.')

    def _startShutdown(self):
        # Handle all pipe messages before shutdown
        while self._pipes[self.name][1].poll():
            self._handleInbox()

        ### Set process state
        if getattr(IPC.State, self.name) is not None:
            getattr(IPC.State, self.name).value = Definition.State.stopped

        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    ################################
    ### Inter process communication

    def send(self, processName, signal, *args, **kwargs):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        """
        self._pipes[processName][0].send([signal, args, kwargs])

    def rpc(self, processName, function, *args, **kwargs):
        self.send(processName, BaseProcess.Signals.RPC, function.__name__, *args, **kwargs)


    ################################
    ### Private functions

    def _executeRPC(self, fun: str, *args, **kwargs):
        """Execute a remote call to the specified function and pass *args, **kwargs

        :param fun: function name
        :param args: list of arguments
        :param kwargs: dictionary of keyword arguments
        :return:
        """
        try:
            Logging.logger.log(logging.DEBUG, 'RPC call to function <{}> with Args {} and Kwargs {}'.
                               format(fun, args, kwargs))
            getattr(self, fun)(*args, **kwargs)
        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'RPC call to function <{}> failed with Args {} and Kwargs {} '
                                                '// Exception: {}'.
                                                format(fun, args, kwargs, exc))

    def _handleInbox(self, *args):  # needs *args for compatibility with Glumpy's schedule_interval

        # Poll pipe
        if not(self._pipes[self.name][1].poll()):
            return

        msg = self._pipes[self.name][1].recv()

        Logging.logger.log(logging.DEBUG, 'Received message: {}'.
                           format(msg))

        ### Unpack message
        signal, args, kwargs = msg

        if signal == BaseProcess.Signals.Shutdown:
            self._startShutdown()

        ### RPC calls
        elif signal == BaseProcess.Signals.RPC:
            self._executeRPC(*args, **kwargs)

    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)


##################################
### CONTROLLER class

class Controller(BaseProcess):
    name = Definition.Process.Controller

    _registeredProcesses = list()

    def __init__(self):
        BaseProcess.__init__(self, _logQueue=mp.Queue())

        ### Manually set up pipe for controller
        self._pipes[self.name] = mp.Pipe()

        ### Set up manager
        IPC.Manager = mp.Manager()

        ### Set configurations
        # Camera
        Config.Camera = IPC.createConfigDict()
        Config.Camera.update(configuration.configuration(Definition.CameraConfig))
        # Display
        Config.Display = IPC.createConfigDict()
        Config.Display.update(configuration.configuration(Definition.DisplayConfig))
        # Gui
        Config.Gui = IPC.createConfigDict()
        Config.Gui.update(configuration.configuration(Definition.GuiConfig))
        # Logfile
        Config.Logfile = IPC.Manager.Value(ctypes.c_char_p, '')

        ### Set states
        IPC.State.Controller = IPC.createSharedState()
        IPC.State.Camera     = IPC.createSharedState()
        IPC.State.Display    = IPC.createSharedState()
        IPC.State.Gui        = IPC.createSharedState()
        IPC.State.IO         = IPC.createSharedState()
        IPC.State.Logger     = IPC.createSharedState()
        IPC.State.Worker     = IPC.createSharedState()

        ### Set up components
        self._setupCamera()

        ### Set up processes
        ## GUI
        if Config.Gui[Definition.GuiConfig.use]:
            import process.GUI
            self._registerProcess(process.GUI.Main)
        ## Camera
        import process.Camera
        self._registerProcess(process.Camera.Main)
        ## Display
        import process.Display
        self._registerProcess(process.Display.Main)
        ## Logger
        import process.Logger
        self._registerProcess(process.Logger.Main)

        ### Run event loop
        self.start()

    def _registerProcess(self, target, **kwargs):
        """Spawn a new process with a dedicated pipe connection.

        :param target: process class
        :param kwargs: optional keyword arguments for intialization of process class
        """
        self._registeredProcesses.append((target, kwargs))

    def initializeProcess(self, target, **kwargs):
        processName = target.name

        if processName in self._processes:
            ### Terminate process
            Logging.write(logging.INFO, 'Restart process {}'.format(processName))
            self._processes[processName].terminate()

            ### Set process state
            getattr(IPC.State, processName).value = Definition.State.stopped

            ### Delete references
            del self._processes[processName]

        self._processes[processName] = mp.Process(target=target,
                                                  name=processName,
                                                  kwargs=dict(
                                                      _logQueue = self._logQueue,
                                                      _pipes = self._pipes,
                                                      _configuration = dict(
                                                          Camera  = Config.Camera,
                                                          Display = Config.Display,
                                                          Gui     = Config.Gui,
                                                          Logfile = Config.Logfile
                                                      ),
                                                      _states = dict(
                                                          Controller = IPC.State.Controller,
                                                          Camera     = IPC.State.Camera,
                                                          Display    = IPC.State.Display,
                                                          Gui        = IPC.State.Gui,
                                                          IO         = IPC.State.IO,
                                                          Logger     = IPC.State.Logger,
                                                          Worker     = IPC.State.Worker
                                                      ),
                                                      _buffers = dict(
                                                          CameraBO = IPC.Buffer.CameraBO
                                                      ),
                                                      **kwargs
                                                  ))
        self._processes[processName].start()

    def _setupCamera(self):
        if not(Config.Camera[Definition.CameraConfig.use]):
            return

        ### Create camera buffer object
        IPC.Buffer.CameraBO = Buffers.CameraBufferObject()
        IPC.Buffer.CameraBO.addBuffer(Buffers.FrameBuffer)
        IPC.Buffer.CameraBO.addBuffer(Buffers.EyePositionDetector)
        #IPC.Buffer.CameraBO.addBuffer(Buffers.EdgeDetector)

    def start(self):
        ### Initialze all pipse
        for target, kwargs in self._registeredProcesses:
            self._pipes[target.name] = mp.Pipe()

        for target, kwargs in self._registeredProcesses:
            self.initializeProcess(target, **kwargs)

        ### Run controller
        self.run()

        ################
        # Update configurations that should persist here
        configuration.updateConfiguration(Definition.DisplayConfig, **Config.Display)
        # Save to file
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'
                           .format(_configfile))
        configuration.saveToFile()

        ################
        # Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Wait for processes to terminate')

        while True:
            if not(bool(self._processes)):
                break

            for processName in list(self._processes):
                if getattr(IPC.State, processName).value == Definition.State.stopped:
                    ### Terminate and delete references
                    self._processes[processName].terminate()
                    del self._processes[processName]
                    del self._pipes[processName]
        self._running = False

    def main(self):
        pass

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shut down processes')
        self._shutdown = True
        for processName in self._processes:
            self.send(processName, BaseProcess.Signals.Shutdown)


if __name__ == '__main__':

    _configfile = 'default.ini'
    configuration = Basic.Config(_configfile)
    ctrl = Controller()
