"""
MappApp ./Controller.py - Controller process class.
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

import Routine
import Config
import Def
from helper import Basic
import IPC
import Logging
import process
from Process import AbstractProcess

configfile = None

class Controller(AbstractProcess):
    name = Def.Process.Controller

    _registeredProcesses = list()

    _processes : dict = dict()

    def __init__(self):
        ### Set up manager
        IPC.Manager = mp.Manager()

        ### Set up logging
        IPC.Log.Queue = mp.Queue()
        IPC.Log.History = IPC.Manager.list()
        IPC.Log.File = IPC.Manager.Value(ctypes.c_char_p, '')

        AbstractProcess.__init__(self, _log={k: v for k, v in IPC.Log.__dict__.items()
                                             if not (k.startswith('_'))})
        global configfile

        ### Manually set up pipe for controller
        IPC.Pipes[self.name] = mp.Pipe()

        ### Set configurations
        self.configuration = Basic.Config(configfile)
        # Camera
        Config.Camera = IPC.Manager.dict()
        Config.Camera.update(self.configuration.configuration(Def.CameraCfg))
        # Display
        Config.Display = IPC.Manager.dict()
        Config.Display.update(self.configuration.configuration(Def.DisplayCfg))
        # Gui
        Config.Gui = IPC.Manager.dict()
        Config.Gui.update(self.configuration.configuration(Def.GuiCfg))
        # IO
        Config.IO = IPC.Manager.dict()
        Config.IO.update(self.configuration.configuration(Def.IoCfg))
        # Recording
        Config.Recording = IPC.Manager.dict()
        Config.Recording.update(self.configuration.configuration(Def.RecCfg))


        ### Set up states
        IPC.State.Controller = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.Camera     = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.Display    = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.Gui        = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.IO         = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.Logger     = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)
        IPC.State.Worker     = IPC.Manager.Value(ctypes.c_int8, Def.State.NA)

        ### Set of record object
        IPC.Control.Recording = IPC.Manager.dict()
        IPC.Control.Recording.update({Def.RecCtrl.active    : False,
                                      Def.RecCtrl.folder    : ''})

        ### Set up protocol object
        IPC.Control.Protocol = IPC.Manager.dict({Def.ProtocolCtrl.name          : None,
                                                 Def.ProtocolCtrl.phase_id      : None,
                                                 Def.ProtocolCtrl.phase_start   : None,
                                                 Def.ProtocolCtrl.phase_stop    : None})

        ### Set up routines
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

    def testmeh(self):
        print('TEEEST yay')

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
            # (this is the ONLY instance where a process state may be set externally)
            getattr(IPC.State, processName).value = Def.State.STOPPED

            ### Delete references
            del self._processes[processName]

        ### Update keyword args
        kwargs.update(dict(
                          _pipes          = IPC.Pipes,
                          _configurations = {k: v for k, v in Config.__dict__.items()
                                             if not (k.startswith('_'))},
                          _states         = {k: v for k, v in IPC.State.__dict__.items()
                                             if not (k.startswith('_'))},
                          _buffers        = {k: v for k, v in IPC.Routines.__dict__.items()
                                            if not (k.startswith('_'))},
                          _controls       = {k: v for k, v in IPC.Control.__dict__.items()
                                             if not (k.startswith('_'))},
                          _log            = {k: v for k, v in IPC.Log.__dict__.items()
                                             if not (k.startswith('_'))},
                          **kwargs
                      ))

        ### Create subprocess
        self._processes[processName] = mp.Process(target=target,
                                                  name=processName,
                                                  kwargs=kwargs)

        ### Start subprocess
        self._processes[processName].start()

        ### Set state to IDLE
        self.setState(Def.State.IDLE)

    def _setupBuffers(self):
        ### Create buffer object
        IPC.Routines.Camera = Routine.Routines(Def.Process.Camera)

        ### Add camera routines if camera is activated
        if Config.Camera[Def.CameraCfg.use]:
            import routines.Camera
            for bufferName in Config.Camera[Def.CameraCfg.buffers]:
                IPC.Routines.Camera.addBuffer(getattr(routines.Camera, bufferName))

    def start(self):
        ### Initialize all pipes
        for target, kwargs in self._registeredProcesses:
            IPC.Pipes[target.name] = mp.Pipe()

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
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'.format(configfile))
        self.configuration.updateConfiguration(Def.CameraCfg, **{k : v for k, v in Config.Camera.items() if k.find('_prop_') >= 0})
        self.configuration.updateConfiguration(Def.DisplayCfg, **Config.Display)
        self.configuration.updateConfiguration(Def.RecCfg, **Config.Recording)
        self.configuration.saveToFile()

        ### Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Wait for processes to terminate')
        while True:
            ## Complete shutdown if all processes are deleted
            if not(bool(self._processes)):
                break

            ## Check process stati
            for processName in list(self._processes):
                if not(getattr(IPC.State, processName).value == Def.State.STOPPED):
                    continue

                # Terminate and delete references
                self._processes[processName].terminate()
                del self._processes[processName]
                del IPC.Pipes[processName]

        self._running = False
        self.setState(Def.State.STOPPED)

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
        IPC.rpc(Def.Process.Worker, process.Worker.runTask,
                 'ComposeRecordings',
                 IPC.Control.Recording[Def.RecCtrl.folder])

        Logging.write(logging.INFO, 'Stop recording')
        self.setState(Def.State.IDLE)
        IPC.Control.Recording[Def.RecCtrl.folder] = ''


    def startProtocol(self, protocol_path):

        ### If any relevant subprocesses are currently busy: abort
        if not(self.inState(Def.State.IDLE, Def.Process.Display)):
                #or not(self.inState(self.State.IDLE, Def.Process.IO)):
            processes = list()
            if not(self.inState(Def.State.IDLE, Def.Process.Display)):
                processes.append(Def.Process.Display)
            if not (self.inState(Def.State.IDLE, Def.Process.IO)):
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
        self.setState(Def.State.PREPARE_PROTOCOL)

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

    def main(self):

        ### In state PREPARE_PROTOCOL
        if self.inState(Def.State.PREPARE_PROTOCOL):

            ### Wait for children to WAIT_FOR_PHASE (if they are not stopped)
            if (not(self.inState(Def.State.WAIT_FOR_PHASE, Def.Process.Display))
                and not(self.inState(Def.State.STOPPED, Def.Process.Display))) \
                    or \
                (not(self.inState(Def.State.WAIT_FOR_PHASE, Def.Process.IO))
                 and not(self.inState(Def.State.STOPPED, Def.Process.IO))):
                return

            ### Set next phase
            self.startProtocolPhase()

            ### Set next state
            self.setState(Def.State.PREPARE_PHASE)

        ########
        ### PREPARE_PHASE
        if self.inState(Def.State.PREPARE_PHASE):
            print('meh?')
            ### IF Display READY or STOPPED _and_ IO READY or STOPPED
            if (self.inState(Def.State.READY, Def.Process.Display)
                or self.inState(Def.State.STOPPED, Def.Process.Display))\
                    and \
                (self.inState(Def.State.READY, Def.Process.IO)
                 or self.inState(Def.State.STOPPED, Def.Process.IO)):

                IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] = time.time() + 0.1
                IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] = time.time() + 5.1

                Logging.write(logging.INFO, 'Run phase {}. Set start time to {}'
                      .format(IPC.Control.Protocol[Def.ProtocolCtrl.phase_id],
                              IPC.Control.Protocol[Def.ProtocolCtrl.phase_start]))
                self.setState(Def.State.RUNNING)

        ########
        ### RUNNING
        elif self.inState(Def.State.RUNNING):
            ## If stop time is not reached
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                Logging.write(logging.INFO, 'End phase {}.'.format(IPC.Control.Protocol[Def.ProtocolCtrl.phase_id]))
                self.setState(Def.State.PHASE_END)
                return

        ########
        ### PHASE_END
        elif self.inState(Def.State.PHASE_END):

            # TODO: properly check if there's a next phase
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_id] > 1:
                self.setState(Def.State.PROTOCOL_END)
                return

            self.startProtocolPhase()

            self.setState(Def.State.PREPARE_PHASE)

        ########
        ### PROTOCOL_END
        elif self.inState(Def.State.PROTOCOL_END):

            if (self.inState(Def.State.IDLE, Def.Process.Display)
                or self.inState(Def.State.STOPPED, Def.Process.Display)) \
                    and \
                (self.inState(Def.State.IDLE, Def.Process.IO)
                 or self.inState(Def.State.STOPPED, Def.Process.IO)):

                self.stopRecording()

                self.setState(Def.State.IDLE)

        else:
            ### If nothing's happning: sleep for a bit
            time.sleep(0.05)

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shut down processes')
        self._shutdown = True
        for processName in self._processes:
            IPC.send(processName, Def.Signal.Shutdown)