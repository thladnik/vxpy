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
import os
import signal
import sys
import time

import Buffer
import buffers.CameraBuffers
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

    _logQueue  : mp.Queue
    _inPipe    : mp.connection.PipeConnection

    ## Controller exclusives
    _pipes     : dict = dict()
    _processes : dict = dict()


    def __init__(self, **kwargs):
        """
        Kwargs should contain at least
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

            # Set state ints (managed ints)
            elif key == '_states':
                for skey, state in value.items():
                    setattr(IPC.State, skey, state)

            # Set buffer object
            elif key == 'CameraBufferObject':
                IPC.CameraBufferObject = value

            elif key == 'IoBufferObject':
                IPC.IoBufferObject = value

            # Set process attributes
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
        """Event loop to be re-implemented in subclass"""
        NotImplementedError('Event loop of base process class is not implemented.')

    def setState(self, code):
        getattr(IPC.State, self.name).value = code

    def inState(self, code, process=None):
        if process is None:
            process = self.name
        return getattr(IPC.State, process).value == code

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
        Config.Camera.update(configuration.configuration(Definition.Camera))
        # Display
        Config.Display = IPC.createConfigDict()
        Config.Display.update(configuration.configuration(Definition.Display))
        # Gui
        Config.Gui = IPC.createConfigDict()
        Config.Gui.update(configuration.configuration(Definition.Gui))
        # IO
        Config.IO = IPC.createConfigDict()
        Config.IO.update(configuration.configuration(Definition.IO))
        # Recording
        Config.Recording = IPC.createConfigDict()
        Config.Recording.update(configuration.configuration(Definition.Recording))
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
        self._setupBuffers()

        ### Set up processes
        ## GUI
        if Config.Gui[Definition.Gui.use]:
            import process.GUI
            self._registerProcess(process.GUI.Main)
        ## Camera
        if Config.Camera[Definition.Camera.use]:
            import process.Camera
            self._registerProcess(process.Camera.Main)
        ## Display
        if Config.Display[Definition.Display.use]:
            import process.Display
            self._registerProcess(process.Display.Main)
        ## Logger
        import process.Logger
        self._registerProcess(process.Logger.Main)

        ### Run event loop
        self.start()

    def _registerProcess(self, target, **kwargs):
        """Register new process to be spawned.

        :param target: process class
        :param kwargs: optional keyword arguments for intialization of process class
        """
        self._registeredProcesses.append((target, kwargs))

    def initializeProcess(self, target, **kwargs):
        self.setState(Definition.State.busy)

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
                                                      _configuration = {k:v for k, v in Config.__dict__.items() if not(k.startswith('_'))},
                                                      _states = {k:v for k, v in IPC.State.__dict__.items() if not(k.startswith('_'))},
                                                      CameraBufferObject = IPC.CameraBufferObject,
                                                      **kwargs
                                                  ))
        self._processes[processName].start()

        self.setState(Definition.State.idle)

    def _setupBuffers(self):
        ### Create buffer object
        IPC.CameraBufferObject = Buffer.BufferObject(Definition.Process.Camera)

        ### Add camera buffers if camera is activated
        if Config.Camera[Definition.Camera.use]:
            for bufferName in Config.Camera[Definition.Camera.buffers]:
                IPC.CameraBufferObject.addBuffer(getattr(buffers.CameraBuffers, bufferName))


    def start(self):
        ### Initialize all pipes
        for target, kwargs in self._registeredProcesses:
            self._pipes[target.name] = mp.Pipe()

        ### Initialize all processes
        for target, kwargs in self._registeredProcesses:
            self.initializeProcess(target, **kwargs)

        ### Run controller
        self.run()

        ### Pre-shutdown
        ## Update configurations that should persist
        configuration.updateConfiguration(Definition.Display, **Config.Display)
        configuration.updateConfiguration(Definition.Recording, **Config.Recording)
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'
                           .format(_configfile))
        configuration.saveToFile()

        ### Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Wait for processes to terminate')
        while True:
            ## Complete shutdown if all processes are deleted
            if not(bool(self._processes)):
                break

            ## Check process stati
            for processName in list(self._processes):
                if not(getattr(IPC.State, processName).value == Definition.State.stopped):
                    continue
                # Termin`ate and delete references
                self._processes[processName].terminate()
                del self._processes[processName]
                del self._pipes[processName]
        self._running = False

    ################
    # Recording

    def toggleEnableRecording(self, newstate):
        Config.Recording[Definition.Recording.enabled] = newstate

    def startRecording(self):
        if Config.Recording[Definition.Recording.active]:
            Logging.write(logging.WARNING, 'Tried to start new recording while active')
            return

        ### Set current folder if none is given
        if not(bool(Config.Recording[Definition.Recording.current_folder])):
            Config.Recording[Definition.Recording.current_folder] = 'rec_{}'.format(time.strftime('%Y-%m-%d-%H-%M-%S'))

        ### Create output folder
        outPath = os.path.join(Definition.Path.Output, Config.Recording[Definition.Recording.current_folder])
        if not(os.path.exists(outPath)):
            os.mkdir(outPath)

        ### Set state to recording
        self.setState(Definition.State.recording)
        Config.Recording[Definition.Recording.active] = True

    def pauseRecording(self):
        if not(Config.Recording[Definition.Recording.active]):
            Logging.write(logging.WARNING, 'Tried to pause inactive recording.')
            return

        self.setState(Definition.State.recording_paused)
        Config.Recording[Definition.Recording.active] = False

    def stopRecording(self):
        if Config.Recording[Definition.Recording.active]:
            Config.Recording[Definition.Recording.active] = False

        self.setState(Definition.State.idle)
        Config.Recording[Definition.Recording.current_folder] = ''


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
