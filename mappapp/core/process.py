"""
MappApp ./core/process.py
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
from __future__ import annotations
import h5py
import multiprocessing as mp
import numpy as np
import os
import signal
import sys
import time

from mappapp import api
from mappapp import Config
from mappapp import Def
from mappapp import IPC
from mappapp import Logging
from mappapp.core.routine import ArrayAttribute
from mappapp.gui.core import ProcessMonitor

# Type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Type, Union
    from mappapp.core.routine import AbstractRoutine


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

    _routines: Dict[str, Dict[str, AbstractRoutine]] = dict()
    h5_file: Union[None, h5py.File] = None
    record_group: Union[None, h5py.Group] = None
    compression_args: Dict[str, Any] = dict()

    def __init__(self,
                 _configurations=None,
                 _controls=None,
                 _log=None,
                 _proxies=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 **kwargs):

        # Set process instance
        IPC.Process = self

        # Set pipes
        if not (_pipes is None):
            IPC.Pipes.update(_pipes)

        # Set log
        if not (_log is None):
            for lkey, log in _log.items():
                setattr(IPC.Log, lkey, log)
            # Setup logging
            Logging.setup_logger(self.name)

        # Set routines and let routine wrapper create hooks in process instance and initialize buffers
        if isinstance(_routines, dict):
            self._routines = _routines

            for process_routines in self._routines.values():
                for routine in process_routines.values():
                    for fun in routine.exposed:
                        try:
                            self.register_rpc_callback(routine, fun.__qualname__, fun)
                        except:
                            # This is a workaround. Please do not remove or you'll break the GUI.
                            # In order for some IPC features to work the, AbstractProcess init has to be
                            # called **before** the PyQt5.QtWidgets.QMainWindow init in the GUI process.
                            # Doing this, however, causes an exception about failing to call
                            # the QMainWindow super-class init, since "createHooks" directly sets attributes
                            # on the new, uninitialized QMainWindow sub-class.
                            # Catching this (unimportant) exception prevents a crash.
                            pass

                    routine._connect_triggers(_routines)

                    # Run local initialization for producer process
                    if self.name == routine.process_name:
                        routine.initialize()

                    # Initialize buffers
                    routine.buffer.build()

        # Set configurations
        if _configurations is not None:
            Config.__dict__.update(_configurations)

        # Set controls
        if _controls is not None:
            for ckey, control in _controls.items():
                setattr(IPC.Control, ckey, control)

        if _proxies is not None:
            for pkey, proxy in _proxies.items():
                setattr(IPC, pkey, proxy)

        # Set states
        if not (_states is None):
            for skey, state in _states.items():
                setattr(IPC.State, skey, state)

        # Set additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set process state
        if not (getattr(IPC.State, self.name) is None):
            IPC.set_state(Def.State.STARTING)

        # Bind signals
        signal.signal(signal.SIGINT, self.handle_SIGINT)

    def run(self, interval):
        Logging.write(Logging.INFO, f'Process {self.name} started at time {time.time()}')

        # Set state to running
        self._running = True
        self._shutdown = False

        # Set process state
        IPC.set_state(Def.State.IDLE)

        min_sleep_time = IPC.Control.General[Def.GenCtrl.min_sleep_time]
        self.t = time.perf_counter()
        self.tt = [time.perf_counter()]
        # Run event loop
        while self._is_running():
            self.handle_inbox()

            self.tt.append(time.perf_counter())
            if (self.tt[-1] - self.tt[0]) > 1.:
                dt = np.diff(self.tt)
                mdt = np.mean(dt)
                sdt = np.std(dt)
                # print('Avg loop time in {} {:.2f} +/- {:.2f}ms'.format(self.name, mdt * 1000, sdt * 1000))
                self.tt = [self.tt[-1]]
                api.gui_rpc(ProcessMonitor.update_process_interval, self.name, interval, mdt, sdt, _send_verbosely=False)

            # Wait until interval time is up
            dt = (self.t + interval) - time.perf_counter()
            if self.enable_idle_timeout and dt > (1.2 * min_sleep_time):
                # Sleep to reduce CPU usage
                time.sleep(dt / 1.2)

            # Busy loop until next main execution for precise timing
            # while self.t + interval - time.perf_counter() >= 0:
            while time.perf_counter() < (self.t + interval):
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
            # self.idle()
            return False

        ########
        # WAIT_FOR_PHASE
        elif self.in_state(Def.State.WAIT_FOR_PHASE):

            if not (self.in_state(Def.State.PREPARE_PHASE, Def.Process.Controller)):
                return False

            self._prepare_phase()

            # Set next state
            self.set_state(Def.State.READY)
            return False

        ########
        # READY
        elif self.in_state(Def.State.READY):
            # If Controller is not yet running, don't wait for go time, because there may be an abort
            if not (self.in_state(Def.State.RUNNING, Def.Process.Controller)):
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
            pass
            # self.idle()

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
        return self._running and not (self._shutdown)

    def register_rpc_callback(self, instance, fun_str, fun):
        if fun_str not in self._registered_callbacks:
            self._registered_callbacks[fun_str] = (instance, fun)
        else:
            Logging.write(Logging.WARNING, 'Trying to register callback \"{}\" more than once'.format(fun_str))

    ################################
    # Private functions

    def _execute_rpc(self, fun_str: str, *args, **kwargs):
        """Execute a remote call to the specified function and pass *args, **kwargs

        :param fun_str: function name
        :param args: list of arguments
        :param kwargs: dictionary of keyword arguments
        :return:
        """
        fun_path = fun_str.split('.')

        _send_verbosely = kwargs.pop('_send_verbosely')

        # RPC on process class
        if fun_path[0] == self.__class__.__name__:
            fun_str = fun_path[1]

            try:

                if _send_verbosely:
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

                if _send_verbosely:
                    Logging.write(Logging.DEBUG,
                                  f'RPC call to callback <{fun_str}> with Args {args} and Kwargs {kwargs}')

                instance, fun = self._registered_callbacks[fun_str]
                fun(instance, *args, **kwargs)

            except Exception as exc:

                Logging.write(Logging.WARNING,
                              f'RPC call to callback <{fun_str}> failed with Args {args} and Kwargs {kwargs}'
                              f' // Exception: {exc}')

                import traceback
                traceback.print_exc()

        else:
            Logging.write(Logging.WARNING, 'Function for RPC of method \"{}\" not found'.format(fun_str))

    def handle_inbox(self, *args):

        # Poll pipe
        if not (IPC.Pipes[self.name][1].poll()):
            return

        # Receive
        msg = IPC.Pipes[self.name][1].recv()

        # Unpack
        signal, args, kwargs = msg

        # Log
        if kwargs.get('_send_verbosely'):
            Logging.write(Logging.DEBUG, f'Received message: {msg}')

        # If shutdown signal
        if signal == Def.Signal.shutdown:
            self._start_shutdown()

        # If RPC
        elif signal == Def.Signal.rpc:
            self._execute_rpc(*args, **kwargs)

    def _create_dataset(self, routine_name: str, attr_name: str, attr_shape: tuple, attr_dtype: Any):

        # Get group for this particular routine
        routine_grp = self.record_group.require_group(routine_name)

        # Skip if dataset exists already
        if attr_name in routine_grp:
            Logging.write(Logging.WARNING, f'Tried to create existing attribute {routine_grp[attr_name]}')
            return

        try:
            routine_grp.create_dataset(attr_name,
                                       shape=(0, *attr_shape,),
                                       dtype=attr_dtype,
                                       maxshape=(None, *attr_shape,),
                                       chunks=(1, *attr_shape,),
                                       **self.compression_args)
            Logging.write(Logging.DEBUG,
                          f'Create record dataset "{routine_grp[attr_name]}"')

        except Exception as exc:
            import traceback
            Logging.write(Logging.WARNING,
                          f'Failed to create record dataset "{routine_grp[attr_name]}"'
                          f' // Exception: {exc}')
            traceback.print_exc()

    def _append_to_dataset(self, grp: h5py.Group, key: str, value: Any):

        # Create dataset (if necessary)
        if key not in grp:
            # Some datasets may not be created on record group creation
            # (this is e.g. the the case for parameters of visuals,
            # because unless the data types are specifically declared,
            # there's no way to know them ahead of time)

            # Iterate over dictionary contents
            if isinstance(value, dict):
                for k, v in value.items():
                    self._append_to_dataset(grp, f'{key}_{k}', v)
                return

            # Try to cast to numpy arrays
            if isinstance(value, list):
                value = np.array(value)
            else:
                value = np.array([value])

            dshape = value.shape
            dtype = value.dtype
            assert np.issubdtype(dtype, np.number) or dtype == bool, \
                f'Unable save non-numerical value "{value}" to dataset "{key}" in group {grp.name}'

            self._create_dataset(grp.name.split('/')[-1], key, dshape, dtype)

        # Get dataset
        dset = grp[key]
        # Increment time dimension by 1
        dset.resize((dset.shape[0] + 1, *dset.shape[1:]))
        # Write new value
        dset[dset.shape[0] - 1] = value

    def _routine_on_record(self, routine_name):
        return f'{self.name}/{routine_name}' in Config.Recording[Def.RecCfg.routines]

    def set_record_group(self, group_name: str, group_attributes: dict = None):
        if self.h5_file is None:
            return

        # Set group
        Logging.write(Logging.INFO, f'Set record group "{group_name}"')
        self.record_group = self.h5_file.require_group(group_name)
        if group_attributes is not None:
            self.record_group.attrs.update(group_attributes)

        # Create routine groups
        for routine_name, routine in self._routines[self.name].items():

            if not (self._routine_on_record(routine_name)):
                continue

            Logging.write(Logging.INFO, f'Set routine group {routine_name}')
            self.record_group.require_group(routine_name)

            # Create datasets in routine group
            for attr_name in routine.file_attrs:
                attr = getattr(routine.buffer, attr_name)
                # Atm only ArrayAttributes have declared data types
                # Other attributes (if compatible) will be created at recording time
                if isinstance(attr, ArrayAttribute):
                    self._create_dataset(routine_name, attr_name, attr._shape, attr._dtype[1])
                    self._create_dataset(routine_name, f'{attr_name}_time', (1,), np.float64)

    def update_routines(self, *args, **kwargs):

        # Fetch current group
        # (this also closes open files so it should be executed in any case)
        record_grp = self.get_container()

        if not (bool(args)) and not (bool(kwargs)):
            return

        current_time = time.time()
        for routine_name, routine in self._routines[self.name].items():
            # Update time
            routine.buffer.set_time(current_time)

            # Execute routine function
            routine.execute(*args, **kwargs)

            # Advance buffer
            routine.buffer.next()

            # If no file object was provided or this particular buffer is not supposed to stream to file: return
            if record_grp is None or not (self._routine_on_record(routine_name)):
                continue

            # Iterate over data in group (buffer)
            for attr_name, attr_time, attr_data in routine.to_file():

                if attr_time is None:
                    continue

                self._append_to_dataset(record_grp[routine_name], attr_name, attr_data)
                self._append_to_dataset(record_grp[routine_name], f'{attr_name}_time', attr_time)

    def get_buffer(self, routine_cls: Type[AbstractRoutine]):
        """Return buffer of a routine class"""

        process_name = routine_cls.process_name
        routine_name = routine_cls.__name__

        assert process_name in self._routines and routine_name in self._routines[process_name], \
            f'Routine {routine_name} is not set in {self.name}'

        return self._routines[process_name][routine_name].buffer

    def read(self, attr_name: str, routine_cls: AbstractRoutine = None, *args, **kwargs):
        """Read shared attribute from buffer.

        :param attr_name: string name of attribute or string format <attrName>/<bufferName>
        :param routine_name: name of buffer; if None, then attrName has to be <attrName>/<bufferName>

        :return: value of the buffer
        """

        return self._routines[routine_cls.process_name][routine_cls.__name__].read(attr_name, *args, **kwargs)

    @property
    def routines(self):
        return self._routines

    def get_container(self) -> Union[h5py.File, h5py.Group, None]:
        """Method checks if application is currently recording.
        Opens and closes output file if necessary and returns either a file/group object or a None.
        """

        # If recording is running and file is open: return record group
        if IPC.Control.Recording[Def.RecCtrl.active] and self.record_group is not None:
            return self.record_group

        elif IPC.Control.Recording[Def.RecCtrl.active] and not (IPC.Control.Recording[Def.RecCtrl.enabled]):
            return None

        # If recording is running and file not open: open file and return record group
        elif IPC.Control.Recording[Def.RecCtrl.active] and self.h5_file is None:
            # If output folder is not set: log warning and return None
            if not (bool(IPC.Control.Recording[Def.RecCtrl.folder])):
                Logging.write(Logging.WARNING, 'Recording has been started but output folder is not set.')
                return None

            # If output folder is set: open file
            rec_folder = IPC.Control.Recording[Def.RecCtrl.folder]
            filepath = os.path.join(rec_folder, f'{self.name}.hdf5')

            # Open new file
            Logging.write(Logging.DEBUG, f'Open new file {filepath}')
            self.h5_file = h5py.File(filepath, 'w')

            # Set compression
            compr_method = IPC.Control.Recording[Def.RecCtrl.compression_method]
            compr_opts = IPC.Control.Recording[Def.RecCtrl.compression_opts]
            self.compression_args = dict()
            if compr_method is not None:
                self.compression_args = {'compression': compr_method, **compr_opts}

            # Set current group to root
            self.set_record_group('/')

            return self.record_group

        # Recording is not running at the moment
        else:

            # If current recording folder is still set: recording is paused
            if bool(IPC.Control.Recording[Def.RecCtrl.folder]):
                # Do nothing; return nothing
                return None

            # If folder is not set anymore
            else:
                # Close open file (if open)
                if not (self.h5_file is None):
                    self.h5_file.close()
                    self.h5_file = None
                    self.record_group = None
                # Return nothing
                return None

    def handle_SIGINT(self, sig, frame):
        print(f'> SIGINT handled in  {self.__class__}')
        sys.exit(0)


class ProcessProxy:
    def __init__(self, name):
        self.name = name
        self._state: mp.Value = getattr(IPC.State, self.name)

    @property
    def state(self):
        return self._state.value

    def in_state(self, state):
        return self.state == state

    def read(self, routine_cls, attr_name, *args, **kwargs):
        return IPC.Process._routines[self.name][routine_cls.__name__].read(attr_name, *args, **kwargs)

    def rpc(self, function: Callable, *args, **kwargs) -> None:
        """Send a remote procedure call of given function to another process.

        @param process_name:
        @param function:
        @param args:
        @param kwargs:
        """
        IPC.rpc(self.name, function, *args, **kwargs)
