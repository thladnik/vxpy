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
import Config
import Def
from helper import Basic
import IPC
import Logging
import process

if Def.Env == Def.EnvTypes.Dev:
    pass

##################################
## Process BASE class

class BaseProcess:
    name       : str

    class State:
        na               = 0
        stopped          = 99
        starting         = 10
        PREPARE_PROTOCOL = 30
        WAIT_FOR_PHASE   = 31
        PREPARE_PHASE    = 32
        READY            = 33
        PHASE_END        = 37
        PROTOCOL_END     = 39
        IDLE             = 20
        RUNNING          = 41
        standby          = 42

    class Signal:
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

            # Set buffers
            if key == '_buffers':
                for bkey, buffer in value.items():
                    setattr(IPC.Buffer, bkey, buffer)
            # Set configurations
            elif key == '_configurations':
                for ckey, config in value.items():
                    setattr(Config, ckey, config)
            # Set controls
            elif key == '_controls':
                for ckey, control in value.items():
                    setattr(IPC.Control, ckey, control)
            # Set state ints (managed ints)
            elif key == '_states':
                for skey, state in value.items():
                    setattr(IPC.State, skey, state)

            # Set process attributes
            else:
                setattr(self, key, value)

        ### Set process state
        if getattr(IPC.State, self.name) is not None:
            getattr(IPC.State, self.name).value = self.State.starting

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
            getattr(IPC.State, self.name).value = self.State.IDLE

        ### Run event loop
        self.t = time.perf_counter()
        while self._isRunning():
            self._handleInbox()
            self.main()
            self.t = time.perf_counter()

    def main(self):
        """Event loop to be re-implemented in subclass"""
        NotImplementedError('Event loop of base process class is not implemented.')

    def getState(self, process=None):
        if process is None:
            process = self.name
        return getattr(IPC.State, process).value

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
            getattr(IPC.State, self.name).value = self.State.stopped

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
        Logging.write(logging.DEBUG, 'Send to process {} with signal {} > args: {} > kwargs: {}'
                      .format(processName, signal, args, kwargs))
        self._pipes[processName][0].send([signal, args, kwargs])

    def rpc(self, processName, function, *args, **kwargs):
        self.send(processName, BaseProcess.Signal.RPC, function.__name__, *args, **kwargs)


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

        if signal == BaseProcess.Signal.Shutdown:
            self._startShutdown()

        ### RPC calls
        elif signal == BaseProcess.Signal.RPC:
            self._executeRPC(*args, **kwargs)

    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)


##################################
### CONTROLLER class

class Controller(BaseProcess):
    name = Def.Process.Controller

    _registeredProcesses = list()

    def __init__(self):
        BaseProcess.__init__(self, _logQueue=mp.Queue())

        ### Manually set up pipe for controller
        self._pipes[self.name] = mp.Pipe()

        ### Set up manager
        IPC.Manager = mp.Manager()

        ### Set configurations
        # Camera
        Config.Camera = IPC.Manager.dict()
        Config.Camera.update(configuration.configuration(Def.CameraCfg))
        # Display
        Config.Display = IPC.Manager.dict()
        Config.Display.update(configuration.configuration(Def.DisplayCfg))
        # Gui
        Config.Gui = IPC.Manager.dict()
        Config.Gui.update(configuration.configuration(Def.GuiCfg))
        # IO
        Config.IO = IPC.Manager.dict()
        Config.IO.update(configuration.configuration(Def.IoCfg))
        # Recording
        Config.Recording = IPC.Manager.dict()
        Config.Recording.update(configuration.configuration(Def.RecCfg))

        # Set up logfile
        IPC.Buffer.Logfile = IPC.Manager.Value(ctypes.c_char_p, '')

        ### Set up states
        IPC.State.Controller = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.Camera     = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.Display    = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.Gui        = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.IO         = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.Logger     = IPC.Manager.Value(ctypes.c_int8, self.State.na)
        IPC.State.Worker     = IPC.Manager.Value(ctypes.c_int8, self.State.na)

        ### Set of record object
        IPC.Control.Recording = IPC.Manager.dict()
        IPC.Control.Recording.update({Def.RecCtrl.active    : False,
                                      Def.RecCtrl.folder    : ''})

        ### Set up protocol object
        IPC.Control.Protocol = IPC.Manager.dict({Def.ProtocolCtrl.name          : None,
                                                 Def.ProtocolCtrl.phase_id      : None,
                                                 Def.ProtocolCtrl.phase_start   : None,
                                                 Def.ProtocolCtrl.phase_stop    : None})

        ### Set up buffers
        self._setupBuffers()

        ### Set up processes
        ## Worker
        self._registerProcess(process.Worker)
        ## GUI
        if Config.Gui[Def.GuiCfg.use]:
            self._registerProcess(process.GUI)
        ## Camera
        if Config.Camera[Def.CameraCfg.use]:
            self._registerProcess(process.Camera)
        ## Display
        if Config.Display[Def.DisplayCfg.use]:
            self._registerProcess(process.Display)
        ## IO
        if Config.IO[Def.IoCfg.use]:
            self._registerProcess(process.IO)
        ## Logger (always runs in background)
        self._registerProcess(process.Logger)

        ### Set up protocol
        self.current_protocol = None

        ### Run event loop
        self.start()

    def _registerProcess(self, target, **kwargs):
        """Register new process to be spawned.

        :param target: process class
        :param kwargs: optional keyword arguments for initalization of process class
        """
        self._registeredProcesses.append((target, kwargs))

    def initializeProcess(self, target, **kwargs):

        processName = target.name

        if processName in self._processes:
            ### Terminate process
            Logging.write(logging.INFO, 'Restart process {}'.format(processName))
            self._processes[processName].terminate()

            ### Set process state
            getattr(IPC.State, processName).value = self.State.stopped

            ### Delete references
            del self._processes[processName]

        self._processes[processName] = mp.Process(target=target,
                                                  name=processName,
                                                  kwargs=dict(
                                                      _logQueue       = self._logQueue, # TODO: move out of class, this is IPC
                                                      _pipes          = self._pipes, # TODO: move out of class, this is IPC
                                                      _configurations = {k: v for k, v in Config.__dict__.items()
                                                                         if not (k.startswith('_'))},
                                                      _states         = {k: v for k, v in IPC.State.__dict__.items()
                                                                         if not (k.startswith('_'))},
                                                      _buffers        = {k: v for k, v in IPC.Buffer.__dict__.items()
                                                                        if not (k.startswith('_'))},
                                                      _controls       = {k: v for k, v in IPC.Control.__dict__.items()
                                                                         if not (k.startswith('_'))},
                                                      **kwargs
                                                  ))

        self._processes[processName].start()

        self.setState(self.State.IDLE)

    def _setupBuffers(self):
        ### Create buffer object
        IPC.Buffer.Camera = Buffer.BufferObject(Def.Process.Camera)

        ### Add camera buffers if camera is activated
        if Config.Camera[Def.CameraCfg.use]:
            import buffers.CameraBuffers
            for bufferName in Config.Camera[Def.CameraCfg.buffers]:
                IPC.Buffer.Camera.addBuffer(getattr(buffers.CameraBuffers, bufferName))

    def start(self):
        ### Initialize all pipes
        for target, kwargs in self._registeredProcesses:
            self._pipes[target.name] = mp.Pipe()

        ### Initialize all processes
        for target, kwargs in self._registeredProcesses:
            self.initializeProcess(target, **kwargs)

        ### Check time precision on system
        dt = list()
        t0 = time.time()
        while len(dt) < 100:
            t1 = time.time()
            if t1 > t0:
                dt.append(t1-t0)
        avg_dt = sum(dt) / len(dt)
        msg = 'Timing precision on system {0:6f}s'.format(avg_dt)
        if avg_dt > 0.001:
            msg_type = logging.WARNING
        else:
            msg_type = logging.INFO
        Logging.write(msg_type, msg)

        ### Run controller
        self.run()

        ### Pre-shutdown
        ## Update configurations that should persist
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'.format(_configfile))
        configuration.updateConfiguration(Def.CameraCfg, **{k : v for k, v in Config.Camera.items() if k.find('_prop_') >= 0})
        configuration.updateConfiguration(Def.DisplayCfg, **Config.Display)
        configuration.updateConfiguration(Def.RecCfg, **Config.Recording)
        configuration.saveToFile()

        ### Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Wait for processes to terminate')
        while True:
            ## Complete shutdown if all processes are deleted
            if not(bool(self._processes)):
                break

            ## Check process stati
            for processName in list(self._processes):
                if not(getattr(IPC.State, processName).value == self.State.stopped):
                    continue

                # Terminate and delete references
                self._processes[processName].terminate()
                del self._processes[processName]
                del self._pipes[processName]

        self._running = False
        self.setState(self.State.stopped)

    ################
    # Recording

    def toggleEnableRecording(self, newstate):
        Config.Recording[Def.RecCfg.enabled] = newstate

    def startRecording(self):
        if IPC.Control.Recording[Def.RecCtrl.active]:
            Logging.write(logging.WARNING, 'Tried to start new recording while active')
            return False

        ### Set current folder if none is given
        if not(bool(IPC.Control.Recording[Def.RecCtrl.folder])):
            IPC.Control.Recording[Def.RecCtrl.folder] = 'rec_{}'.format(time.strftime('%Y-%m-%d-%H-%M-%S'))

        ### Create output folder
        outPath = os.path.join(Def.Path.Output, IPC.Control.Recording[Def.RecCtrl.folder])
        Logging.write(logging.DEBUG, 'Set output folder {}'.format(outPath))
        if not(os.path.exists(outPath)):
            Logging.write(logging.DEBUG, 'Create output folder {}'.format(outPath))
            os.mkdir(outPath)

        ### Set state to recording
        Logging.write(logging.INFO, 'Start recording')
        IPC.Control.Recording[Def.RecCtrl.active] = True

        return True

    def pauseRecording(self):
        if not(IPC.Control.Recording[Def.RecCtrl.active]):
            Logging.write(logging.WARNING, 'Tried to pause inactive recording.')
            return

        Logging.write(logging.INFO, 'Pause recording')
        IPC.Control.Recording[Def.RecCtrl.active] = False

    def stopRecording(self, sessiondata=None):
        if IPC.Control.Recording[Def.RecCtrl.active]:
            IPC.Control.Recording[Def.RecCtrl.active] = False

        if not(Config.Gui[Def.GuiCfg.use]) and sessiondata is None:
            # TODO: prompt user for sessiondata?
            pass


        ### Save metadata and externally provided sessiondata
        metadata = dict(hello1name='test', hello2val=123)
        #TODO: compose proper metadata, append sessiondata and save to file

        ### Let worker compose all individual recordings into one data structure
        self.rpc(Def.Process.Worker, process.Worker.runTask,
                 'ComposeRecordings',
                 IPC.Control.Recording[Def.RecCtrl.folder])

        Logging.write(logging.INFO, 'Stop recording')
        self.setState(self.State.IDLE)
        IPC.Control.Recording[Def.RecCtrl.folder] = ''


    def startProtocol(self, protocol_path):

        ### If any relevant subprocesses are currently busy: abort
        if not(self.inState(self.State.IDLE, Def.Process.Display)):
                #or not(self.inState(self.State.IDLE, Def.Process.IO)):
            processes = list()
            if not(self.inState(self.State.IDLE, Def.Process.Display)):
                processes.append(Def.Process.Display)
            if not (self.inState(self.State.IDLE, Def.Process.IO)):
                processes.append(Def.Process.IO)

            Logging.write(logging.WARNING,
                          'One or more processes currently busy. Can not start new protocol.'
                          '(Processes: {})'.format(','.join(processes)))
            return

        ### Start recording if enabled; abort if recording can't be started
        if Config.Recording[Def.RecCfg.enabled]:
            if not(self.startRecording()):
                return

        ### Set phase info
        IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] = None
        IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] = None
        IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] = None
        ### Set protocol class path
        IPC.Control.Protocol[Def.ProtocolCtrl.name] = protocol_path

        ### Go into standby mode
        self.setState(self.State.PREPARE_PROTOCOL)

    def startProtocolPhase(self, _id = None):
        ### If phase ID was provided: run this ID
        if not(_id is None):
            IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] = _id
            return

        ### Else: advance protocol counter
        if IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] is None:
            IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] = 0
        else:
            IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] = IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] + 1

    def stopProtocol(self):
        IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] = None
        self.rpc(Def.Process.Display, process.Display.stopProtocol)
        self.rpc(Def.Process.IO, process.IO.stopProtocol)

        if Config.Recording[Def.RecCfg.enabled]:
            self.stopRecording()

    def main(self):

        ### In state PREPARE_PROTOCOL
        if self.inState(self.State.PREPARE_PROTOCOL):

            ### Wait for children to WAIT_FOR_PHASE
            if not(self.inState(self.State.WAIT_FOR_PHASE, Def.Process.Display)) \
                    or not(self.inState(self.State.WAIT_FOR_PHASE, Def.Process.IO)):
                return

            ### Set next phase
            self.startProtocolPhase()

            ### Set next state
            self.setState(self.State.PREPARE_PHASE)

        ########
        ### PREPARE_PHASE
        if self.inState(self.State.PREPARE_PHASE):
            if self.inState(self.State.READY, Def.Process.Display) \
                and self.inState(self.State.READY, Def.Process.IO):
                IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] = time.time() + 0.1
                IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] = time.time() + 5.1

                Logging.write(logging.INFO, 'Run phase {}. Set start time to {}'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.phase_id],
                              IPC.Control.Protocol[Def.ProtocolCtrl.phase_start]))
                self.setState(self.State.RUNNING)

        ########
        ### RUNNING
        elif self.inState(self.State.RUNNING):
            ## If stop time is not reached
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                self.setState(self.State.PHASE_END)
                return

        ########
        ### PHASE_END
        elif self.inState(self.State.PHASE_END):

            # TODO: properly check if there's a next phase
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] > 1:
                self.setState(self.State.PROTOCOL_END)
                return

            self.startProtocolPhase()

            self.setState(self.State.PREPARE_PHASE)

        ########
        ### PROTOCOL_END
        elif self.inState(self.State.PROTOCOL_END):

            if self.inState(self.State.IDLE, Def.Process.Display) \
                    and self.inState(self.State.IDLE, Def.Process.IO):

                self.stopRecording()

                self.setState(self.State.IDLE)

        else:
            ### If nothing's happning: sleep for a bit
            time.sleep(0.05)

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shut down processes')
        self._shutdown = True
        for processName in self._processes:
            self.send(processName, BaseProcess.Signal.Shutdown)


if __name__ == '__main__':

    _configfile = 'default_TIS.ini'
    #_configfile = 'default.ini'
    configuration = Basic.Config(_configfile)
    ctrl = Controller()
