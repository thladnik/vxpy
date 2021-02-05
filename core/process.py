"""
MappApp ./process.py - Base process and controller class called to start program.
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

import signal
import sys
import time

import Config
import Def
import IPC
import Logging

if Def.Env == Def.EnvTypes.Dev:
    pass

# Type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Callable, Dict, Tuple
    from core.routine import AbstractRoutine

##################################
## Process BASE class

class AbstractProcess:
    """AbstractProcess class, which is inherited by all processes.

    All processes **need to** implement the "main" method, which is called once on
    each iteration of the event loop.
    """
    name: str

    _running: bool
    _shutdown: bool

    # Protocol related
    phase_start_time: float = None
    phase_time: float = None

    enable_idle_timeout: bool = True
    _registered_callbacks: dict = dict()

    _routines: dict = dict()

    def __init__(self,
                 _configurations=None,
                 _controls=None,
                 _log=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 **kwargs):

        # Set process instance
        IPC.Process = self

        # Set routines and let routine wrapper create hooks in process instance and initialize buffers
        if not(_routines is None):
            for bkey, routines in _routines.items():
                ## Set routines object
                setattr(IPC.Routines, bkey, routines)

                if not(routines is None):
                    ## Create method hooks in process class instance
                    try:
                        routines.create_hooks(self)
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

                    ## Initialize buffers
                    routines.initialize_buffers()

        # Set configurations
        if _configurations is not None:
            Config.__dict__.update(_configurations)

        # Set controls
        if _controls is not None:
            for ckey, control in _controls.items():
                setattr(IPC.Control, ckey, control)

        # Set log
        if not(_log is None):
            for lkey, log in _log.items():
                setattr(IPC.Log, lkey, log)

        # Set pipes
        if not(_pipes is None):
            IPC.Pipes.update(_pipes)

        # Set states
        if not(_states is None):
            for skey, state in _states.items():
                setattr(IPC.State, skey, state)

        # Set additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set process state
        if not(getattr(IPC.State, self.name) is None):
            IPC.set_state(Def.State.STARTING)

        # Setup logging
        Logging.setup_logger(self.name)

        # Bind signals
        signal.signal(signal.SIGINT, self.handle_SIGINT)

    def run(self, interval):
        Logging.write(Logging.INFO,
                      'Process {} started at time {}'.format(self.name, time.time()))

        # Set state to running
        self._running = True
        self._shutdown = False

        # Set process state
        IPC.set_state(Def.State.IDLE)

        min_sleep_time = IPC.Control.General[Def.GenCtrl.min_sleep_time]
        self.t = time.perf_counter()
        # Run event loop
        while self._is_running():
            self.handle_inbox()

            # Wait until interval time is up
            dt = self.t + interval - time.perf_counter()
            if self.enable_idle_timeout and dt > 1.2 * min_sleep_time:
                # Sleep to reduce CPU usage
                time.sleep(0.9 * dt)

            # Busy loop until next main execution for precise timing
            while self.t + interval - time.perf_counter() >= 0:
                pass

            # Set new time
            self.t = time.perf_counter()

            # Execute main method
            self.main()

    def main(self):
        """Event loop to be re-implemented in subclass"""
        raise NotImplementedError('Event loop of process base class is not implemented in {}.'
                                  .format(self.name))

    ################################
    # PROTOCOL RESPONSE

    def _prepare_protocol(self):
        """Method is called when a new protocol has been started by Controller."""
        raise NotImplementedError('Method "_prepare_protocol not implemented in {}.'
                                  .format(self.name))

    def _prepare_phase(self):
        """Method is called when the Controller has set the next protocol phase."""
        raise NotImplementedError('Method "_prepare_phase" not implemented in {}.'
                                  .format(self.name))

    def _cleanup_protocol(self):
        """Method is called after the last phase at the end of the protocol."""
        raise NotImplementedError('Method "_cleanup_protocol" not implemented in {}.'
                                  .format(self.name))

    def _run_protocol(self):
        """Method can be called by all processes that in some way respond to
        the protocol control states.

        Returns True of protocol is currently running and False if not.
        """

        ########
        # RUNNING
        if self.in_state(Def.State.RUNNING):

            ## If phase stoptime is exceeded: end phase
            if IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                self.set_state(Def.State.PHASE_END)
                return False

            # Default: set phase time and execute protocol
            self.phase_time = time.time() - self.phase_start_time
            return True

        ########
        # IDLE
        elif self.in_state(Def.State.IDLE):

            ## Ctrl PREPARE_PROTOCOL
            if self.in_state(Def.State.PREPARE_PROTOCOL, Def.Process.Controller):

                self._prepare_protocol()

                # Set next state
                self.set_state(Def.State.WAIT_FOR_PHASE)
                return False

            # Fallback, timeout during IDLE operation
            self.idle()
            return False

        ########
        # WAIT_FOR_PHASE
        elif self.in_state(Def.State.WAIT_FOR_PHASE):

            if not(self.in_state(Def.State.PREPARE_PHASE, Def.Process.Controller)):
                return False

            self._prepare_phase()

            # Set next state
            self.set_state(Def.State.READY)
            return False

        ########
        # READY
        elif self.in_state(Def.State.READY):
            # If Controller is not yet running, don't wait for go time, because there may be an abort
            if not(self.in_state(Def.State.RUNNING, Def.Process.Controller)):
                return False

            # Wait for go time
            # TODO: there is an issue where Process gets stuck on READY, when protocol is
            #       aborted while it is waiting in this loop. Fix: periodic checking? Might mess up timing?
            while self.in_state(Def.State.RUNNING, Def.Process.Controller):
                # TODO: sync of starts could also be done with multiprocessing.Barrier
                t = time.time()
                if IPC.Control.Protocol[Def.ProtocolCtrl.phase_start] <= t:
                    Logging.write(Logging.INFO, 'Start at {}'.format(t))
                    self.set_state(Def.State.RUNNING)
                    self.phase_start_time = t
                    break

            return False

        ########
        # PHASE_END
        elif self.in_state(Def.State.PHASE_END):

            ####
            ## Ctrl in PREPARE_PHASE -> there's a next phase
            if self.in_state(Def.State.PREPARE_PHASE, Def.Process.Controller):
                self.set_state(Def.State.WAIT_FOR_PHASE)


            elif self.in_state(Def.State.PROTOCOL_END, Def.Process.Controller):

                self._cleanup_protocol()

                self.set_state(Def.State.IDLE)
            else:
                pass

            # Do NOT execute
            return False

        ########
        # Fallback: timeout
        else:
            self.idle()

    def idle(self):
        if self.enable_idle_timeout:
            time.sleep(IPC.Control.General[Def.GenCtrl.min_sleep_time])


    def get_state(self, process=None):
        """Convenience function for access in process class"""
        return IPC.get_state()

    def set_state(self, code):
        """Convenience function for access in process class"""
        IPC.set_state(code)

    def in_state(self, code, process_name=None):
        """Convenience function for access in process class"""
        if process_name is None:
            process_name = self.name
        return IPC.in_state(code, process_name)

    def _start_shutdown(self):
        # Handle all pipe messages before shutdown
        while IPC.Pipes[self.name][1].poll():
            self.handle_inbox()

        # Set process state
        self.set_state(Def.State.STOPPED)

        self._shutdown = True

    def _is_running(self):
        return self._running and not(self._shutdown)

    def register_rpc_callback(self, instance, fun_str, fun):
        if fun_str not in self._registered_callbacks:
            self._registered_callbacks[fun_str] = (instance, fun)
        else:
            Logging.write(Logging.WARNING, 'Trying to register callback \"{}\" more than once'.format(fun_str))


    ################################
    # Private functions

    def _execute_rpc(self,fun_str: str,*args,**kwargs):
        """Execute a remote call to the specified function and pass *args, **kwargs

        :param fun_str: function name
        :param args: list of arguments
        :param kwargs: dictionary of keyword arguments
        :return:
        """
        fun_path = fun_str.split('.')

        # RPC on process class
        if fun_path[0] == self.__class__.__name__:
            fun_str = fun_path[1]

            try:
                Logging.write(Logging.DEBUG,
                              f'RPC call to process <{fun_str}> with Args {args} and Kwargs {kwargs}')
                getattr(self, fun_str)(*args, **kwargs)

            except Exception as exc:
                Logging.write(Logging.WARNING,
                              f'RPC call to process <{fun_str}> failed with Args {args} and Kwargs {kwargs}'
                              f' // Exception: {exc}')

        # RPC on registered callback
        elif fun_str in self._registered_callbacks:
            try:
                Logging.write(Logging.DEBUG,
                              f'RPC call to callback <{fun_str}> with Args {args} and Kwargs {kwargs}')
                instance, fun = self._registered_callbacks[fun_str]
                fun(instance, *args, **kwargs)
            except Exception as exc:
                Logging.write(Logging.WARNING,
                              f'RPC call to callback <{fun_str}> failed with Args {args} and Kwargs {kwargs}'
                              f' // Exception: {exc}')

        else:
            Logging.write(Logging.WARNING, 'Function for RPC of method \"{}\" not found'.format(fun_str))

    def handle_inbox(self, *args):

        # Poll pipe
        if not(IPC.Pipes[self.name][1].poll()):
            return

        msg = IPC.Pipes[self.name][1].recv()

        Logging.write(Logging.DEBUG, f'Received message: {msg}')

        # Unpack message
        signal, args, kwargs = msg

        if signal == Def.Signal.shutdown:
            self._start_shutdown()

        # RPC calls
        elif signal == Def.Signal.rpc:
            self._execute_rpc(*args, **kwargs)

    def handle_SIGINT(self, sig, frame):
        print(f'> SIGINT handled in  {self.__class__}')
        sys.exit(0)


import multiprocessing as mp

class ProcessProxy:
    def __init__(self, name, state):
        self.name = name
        self._state: mp.Value = state

    @property
    def state(self):
        return self._state.value

    @state.setter
    def state(self, new_state):
        if self.name == IPC.Process.name:
            self._state.value = new_state
        else:
            Logging.write(Logging.WARNING, f'Trying to set state of process {self.name} from process {IPC.Process.name}')

    # def routine(self, routine) -> AbstractRoutine:
    #     pass
    #
    # def rpc(self, function: Callable, *args, **kwargs) -> None:
    #     """Send a remote procedure call of given function to another process.
    #
    #     @param process_name:
    #     @param function:
    #     @param args:
    #     @param kwargs:
    #     """
    #     IPC.send(self.name, Def.Signal.rpc, function.__qualname__, *args, **kwargs)