"""
MappApp ./Process.py - Base process and controller class called to start program.
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

import logging
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

if Def.Env == Def.EnvTypes.Dev:
    pass

##################################
## Process BASE class

class AbstractProcess:
    """AbstractProcess class, which is inherited by all processes.
    All processes **need to** implement the "main" method, which is called once on
    each iteration of the event loop.


    """
    name       : str

    _running   : bool
    _shutdown  : bool

    ### Protocol related
    phase_start_ptime    : float = None
    phase_time           : float = None

    def __init__(self,
                 _configurations=None,
                 _controls=None,
                 _log=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 **kwargs):

        ### Set routines and let routine wrapper create hooks in process instance
        if not(_routines is None):
            for bkey, routine in _routines.items():
                ## Set routines object
                setattr(IPC.Routines, bkey, routine)

                ## Create method hooks in process class instance
                try:
                    if not(routine is None):
                        routine.createHooks(self)
                except:
                    # This is a workaround. Please do not remove or you'll break the GUI.
                    # In order for some IPC features to work the, AbstractProcess init has to be
                    # called **before** the PyQt5.QtWidgets.QMainWindow init in the GUI process.
                    # Doing this, however, causes an exception about failing to call
                    # the QMainWindow super-class init, since "createHooks" directly sets attributes
                    # on the new, uninitialized QMainWindow sub-class.
                    # Catching this exception prevents a crash.
                    # Why this is the case? Well... once upon a time in land far, far away...
                    # -> #JustPythonStuff
                    pass

        ### Set configurations
        if not(_configurations is None):
            for ckey, config in _configurations.items():
                setattr(Config, ckey, config)

        ### Set controls
        if not(_controls is None):
            for ckey, control in _controls.items():
                setattr(IPC.Control, ckey, control)

        ### Set log
        if not(_log is None):
            for lkey, log in _log.items():
                setattr(IPC.Log, lkey, log)

        ### Set pipes
        if not(_pipes is None):
            IPC.Pipes.update(_pipes)

        ### Set states
        if not(_states is None):
            for skey, state in _states.items():
                setattr(IPC.State, skey, state)

        ### Set additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        ### Set process name in IPC
        IPC.State.localName = self.name

        ### Set process state
        if not(getattr(IPC.State, self.name) is None):
            IPC.setState(Def.State.STARTING)

        ### Setup logging
        Logging.setupLogger(self.name)

        ### Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)

    def run(self, interval):

        ### Synchronize process to controller
        self.setState(Def.State.SYNC)
        ## Wait
        while IPC.Control.General[Def.GenCtrl.process_null_time] > time.time():
            pass
        ## Set time
        t = time.time()
        self.process_sync_time  = time.perf_counter()

        Logging.write(logging.INFO, 'Synchronized process {} at time {}  to process time {}'.format(self.name, t, self.process_sync_time))
        ### Set state to running
        self._running = True
        self._shutdown = False

        ### Set process state
        IPC.setState(Def.State.IDLE)

        min_sleep_time = IPC.Control.General[Def.GenCtrl.min_sleep_time]
        ### Run event loop
        self.t = time.perf_counter()
        while self._isRunning():
            self._handleInbox()

            ## Wait until interval time is up
            dt = self.t + interval - time.perf_counter()
            # Sleep to reduce CPU usage
            if dt > min_sleep_time:
                time.sleep(dt)
            # If interval is too short for sleep: busy loop
            else:
                while self.t + interval - time.perf_counter() >= 0:
                    pass
            ## Set new time
            self.t = time.perf_counter()

            ## Execute main method
            self.main()


    def main(self):
        """Event loop to be re-implemented in subclass"""
        raise NotImplementedError('Event loop of process base class is not implemented in {}.'
                                  .format(self.name))

    ################################
    ### PROTOCOL RESPONSE

    def _prepareProtocol(self):
        """Method is called when a new protocol has been started by Controller."""
        raise NotImplementedError('Method "_prepareProtocol not implemented in {}.'
                                  .format(self.name))

    def _preparePhase(self):
        """Method is called when the Controller has set the next protocol phase."""
        raise NotImplementedError('Method "_preparePhase" not implemented in {}.'
                                  .format(self.name))

    def _cleanupProtocol(self):
        """Method is called after the last phase at the end of the protocol."""
        raise NotImplementedError('Method "_cleanupProtocol" not implemented in {}.'
                                  .format(self.name))

    def _runProtocol(self):
        """Method can be called by all processes that in some way respond to
        the protocol control states.

        Returns True of protocol is currently running and False if not.
        """

        ########
        ### RUNNING
        if self.inState(Def.State.RUNNING):

            ## If phase stoptime is exceeded: end phase
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                self.setState(Def.State.PHASE_END)
                return False

            ### Default: execute protocol
            self.phase_time = time.perf_counter() - self.phase_start_ptime
            return True

        ########
        ### IDLE
        elif self.inState(Def.State.IDLE):

            ## Ctrl PREPARE_PROTOCOL
            if self.inState(Def.State.PREPARE_PROTOCOL, Def.Process.Controller):

                self._prepareProtocol()

                # Set next state
                self.setState(Def.State.WAIT_FOR_PHASE)
                return False

            ### Fallback, timeout during IDLE operation
            time.sleep(0.05)

        ########
        ### WAIT_FOR_PHASE
        elif self.inState(Def.State.WAIT_FOR_PHASE):

            if not(self.inState(Def.State.PREPARE_PHASE, Def.Process.Controller)):
                return False

            self._preparePhase()

            # Set next state
            self.setState(Def.State.READY)

        ########
        ### READY
        elif self.inState(Def.State.READY):
            ### If Controller is not yet running, don't wait for go time, because there may be an abort
            if not(self.inState(Def.State.RUNNING, Def.Process.Controller)):
                return False

            ### Wait for go time
            # TODO: there is an issue where Process gets stuck on READY, when protocol is
            #       aborted while it is waiting in this loop. Fix: periodic checking? Might mess up timing?
            while self.inState(Def.State.RUNNING, Def.Process.Controller):
                if IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] <= time.time():
                    Logging.write(logging.INFO, 'Start at {}'.format(time.time()))
                    self.setState(Def.State.RUNNING)
                    self.phase_start_ptime = time.perf_counter()
                    break

            return False

        ########
        ### PHASE_END
        elif self.inState(Def.State.PHASE_END):

            ####
            ## Ctrl in PREPARE_PHASE -> there's a next phase
            if self.inState(Def.State.PREPARE_PHASE, Def.Process.Controller):
                self.setState(Def.State.WAIT_FOR_PHASE)


            elif self.inState(Def.State.PROTOCOL_END, Def.Process.Controller):

                self._cleanupProtocol()

                self.setState(Def.State.IDLE)
            else:
                pass

            ### Do NOT execute
            return False

        ########
        ### Fallback: timeout
        else:
            time.sleep(0.05)

    def getState(self, process=None):
        """Convenience function for access in process class"""
        return IPC.getState()

    def setState(self, code):
        """Convenience function for access in process class"""
        IPC.setState(code)

    def inState(self, code, process_name=None):
        """Convenience function for access in process class"""
        if process_name is None:
            process_name = self.name
        return IPC.inState(code, process_name)

    def _startShutdown(self):
        # Handle all pipe messages before shutdown
        while IPC.Pipes[self.name][1].poll():
            self._handleInbox()

        ### Set process state
        self.setState(Def.State.STOPPED)

        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    ################################
    ### Private functions

    def _executeRPC(self, fun: str, *args, **kwargs):
        """Execute a remote call to the specified function and pass *args, **kwargs

        :param fun: function name
        :param args: list of arguments
        :param kwargs: dictionary of keyword arguments
        :return:
        """
        fun_path = fun.split('.')
        if fun_path[0] == self.__class__.__name__:
            fun_str = fun_path[1]
        else:
            fun_str = '_'.join(fun_path)

        try:
            Logging.logger.log(logging.DEBUG, 'RPC call to function <{}> with Args {} and Kwargs {}'
                               .format(fun_str, args, kwargs))
            getattr(self, fun_str)(*args, **kwargs)
        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'RPC call to function <{}> failed with Args {} and Kwargs {} '
                                                '// Exception: {}'.
                                                format(fun_str, args, kwargs, exc))


    def _handleInbox(self, *args):  # needs *args for compatibility with Glumpy's schedule_interval

        # Poll pipe
        if not(IPC.Pipes[self.name][1].poll()):
            return

        msg = IPC.Pipes[self.name][1].recv()

        Logging.logger.log(logging.DEBUG, 'Received message: {}'.
                           format(msg))

        ### Unpack message
        signal, args, kwargs = msg

        if signal == Def.Signal.Shutdown:
            self._startShutdown()

        ### RPC calls
        elif signal == Def.Signal.RPC:
            self._executeRPC(*args, **kwargs)

    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)
