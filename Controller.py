"""
MappApp ./Controller.py - Base process and controller class called to start program. Spawns all sub processes.
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

import Config
import Definition
from helper import Basic
import Buffers
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    pass

##################################
## Process BASE class

class BaseProcess:

    class Signals:
        UpdateProperty  = 10
        RPC             = 20
        Query           = 30
        Shutdown        = 99
        ConfirmShutdown = 100

    name       : str

    _running   : bool
    _shutdown  : bool

    _ctrlQueue : mp.Queue
    _logQueue  : mp.Queue
    _inPipe    : mp.connection.PipeConnection

    ## Controller exclusives
    _pipes               : dict = dict()
    _processes           : dict = dict()


    def __init__(self, **kwargs):
        """
        Kwargs should contain at least
          _ctrlQueue
          _logQueue
          _inPipe
        for basic communication and logging in sub processes (Controller does not require _inPipe)

        Known further kwargs are:
          _cameraBO (multiple processes)
          _app (GUI)
        """
        for key, value in kwargs.items():
            # Set configuration dictionaries (managed dictionaries)
            if key == '_configuration':
                Config.Camera = value['camera']
                Config.Display = value['display']
                Config.Gui = value['gui']
                Config.Logfile = value['logfile']

            # Set attributes
            else:
                setattr(self, key, value)

        # Setup logging
        Logging.setupLogger(self._logQueue, self.name)

        # Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)

    def run(self):
        Logging.logger.log(logging.INFO, 'Run {}'.format(self.name))
        ### Set state to running
        self._running = True
        self._shutdown = False

        ### Run event loop
        self.t = time.perf_counter()
        while self._isRunning():
            self._handleCommunication()
            self.main()
            self.t = time.perf_counter()

        ### Inform controller that process has terminated
        self.send(Definition.Process.Controller, BaseProcess.Signals.ConfirmShutdown)

    def main(self):
        """Event loop to be re-implemented in subclass
        """
        NotImplementedError('Event loop of base process class is not implemented.')

    def _startShutdown(self):
        # Handle all pipe messages before shutdown
        while self._inPipe.poll():
            self._handleCommunication()

        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    ################################
    ### Inter0 process communication

    def send(self, processName, signal, *args, **kwargs):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        """
        if self.name == Definition.Process.Controller:
            self._pipes[processName][0].send([signal, args, kwargs])
        else:
            self._ctrlQueue.put([self.name, processName, [signal, args, kwargs]])

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

    def _handleCommunication(self, *args, msg=None):  # needs *args for compatibility with Glumpy's schedule_interval

        ### Msg should only be set if this is the controller process
        if msg is None:
            # Poll pipe
            if not(self._inPipe.poll()):
                return

            msg = self._inPipe.recv()

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

    _cameraBO: Buffers.CameraBufferObject = None

    def __init__(self, _configfile, _useGUI):
        BaseProcess.__init__(self, _ctrlQueue=mp.Queue(), _logQueue=mp.Queue())
        self._useGUI = _useGUI

        ### Set up manager
        self.manager = mp.Manager()

        ### Set configurations
        self._configfile = _configfile
        self.configuration = Basic.Config(self._configfile)

        Config.Camera = self.manager.dict()
        Config.Camera.update(self.configuration.configuration(Definition.CameraConfig))

        Config.Display = self.manager.dict()
        Config.Display.update(self.configuration.configuration(Definition.DisplayConfig))

        Config.Gui = self.configuration.configuration(Definition.GuiConfig)

        Config.Logfile = self.manager.Value(ctypes.c_char_p, '')

        ### Set up components
        self._setupCamera()

        ### Set up processes
        ## GUI
        if self._useGUI:
            import process.GUI
            self._initializeProcess(Definition.Process.GUI, process.GUI.Main,
                                    _cameraBO=self._cameraBO)
        ## Display
        self.initializeDisplay()
        ## Camera
        import process.Camera
        self._initializeProcess(Definition.Process.Camera, process.Camera.Main,
                                _cameraBO=self._cameraBO)
        ## Logger
        import process.Logger
        self._initializeProcess(Definition.Process.Logger, process.Logger.Main)

        ### Run event loop
        self.run()

    def _initializeProcess(self, processName, target, **optKwargs):
        """Spawn a new process with a dedicated pipe connection.

        :param processHandle: MappApp_Defintion.<Process> class
        :param target: process class
        :param optKwargs: optional keyword arguments
        """
        if processName in self._processes:
            Logging.write(logging.INFO, 'Restart process {}'.format(processName))
            self._processes[processName].terminate()
            del self._processes[processName]
            del self._pipes[processName]

        self._pipes[processName] = mp.Pipe()
        self._processes[processName] = mp.Process(target=target,
                                        name=processName,
                                        kwargs=dict(_ctrlQueue=self._ctrlQueue,
                                                    _logQueue=self._logQueue,
                                                    _inPipe=self._pipes[processName][1],
                                                    _configuration = dict(
                                                        camera  = Config.Camera,
                                                        display = Config.Display,
                                                        gui     = Config.Gui,
                                                        logfile = Config.Logfile
                                                    ),
                                                    **optKwargs))
        self._processes[processName].start()

    def initializeDisplay(self):
        import process.Display
        self._initializeProcess(Definition.Process.Display, process.Display.Main)

    def _setupCamera(self):
        if not(Config.Camera[Definition.CameraConfig.bool_use]):
            return

        ### Create camera buffer object
        self._cameraBO = Buffers.CameraBufferObject()
        self._cameraBO.addBuffer(Buffers.FrameBuffer)
        self._cameraBO.addBuffer(Buffers.EdgeDetector)

    def run(self):

        ################
        # Startup
        self._running = True
        self._shutdown = False

        ################
        # Run main loop
        Logging.logger.log(logging.DEBUG, 'Run <{}>'
                           .format(self.name))
        while self._isRunning():

            # Get new Data from control queue
            sender, receiver, (signal, args, kwargs) = self._ctrlQueue.get()
            Logging.logger.log(logging.DEBUG, 'Message from <{}> to <{}>: Signal {}, Args {}, Kwargs {}'
                               .format(sender, receiver, signal, args, kwargs))

            ########
            ## CALLS TO CONTROLLER
            if receiver == self.name:
                self._handleCommunication(msg=[signal, args, kwargs])

            ########
            # CALLS TO OTHER PROCESSES (FORWARDING)
            else:
                try:
                    Logging.logger.log(logging.DEBUG, 'Forward message from <{}> to <{}> with signal {}'.
                                       format(sender, receiver, signal))
                    self.send(receiver, signal, *args, **kwargs)
                except:
                    Logging.logger.log(logging.WARNING, 'Failed to forward message from <{}> to <{}> with signal {}'.
                                       format(sender, receiver, signal))

        ################
        # Update configurations that should persist here
        self.configuration.updateConfiguration(Definition.DisplayConfig, **Config.Display)
        # Save to file
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'
                           .format(self._configfile))
        self.configuration.saveToFile()

        ################
        # Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Waiting for processes to terminate')
        while True:
            if not(self._ctrlQueue.empty()):
                sender, receiver, msg = self._ctrlQueue.get()
                if msg[0] == BaseProcess.Signals.ConfirmShutdown:
                    Logging.logger.log(logging.DEBUG, 'Received shutdown confirmation from {}'.format(sender))
                    del self._processes[sender]
                    del self._pipes[sender]

                # Check if all processes have shut down
                if not(bool(self._processes)) and not(bool(self._pipes)):
                    break
            time.sleep(0.1)

        Logging.logger.log(logging.DEBUG, 'Confirmed complete shutdown')
        self._running = False

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shutting down processes')
        self._shutdown = True
        for processName in self._processes:
            self.send(processName, BaseProcess.Signals.Shutdown)


if __name__ == '__main__':

    _useGUI = True
    _configfile = 'default.ini'
    ctrl = Controller(_configfile=_configfile, _useGUI=_useGUI)
