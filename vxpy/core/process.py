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

from vxpy import api
from vxpy.api import event
from vxpy import Config
from vxpy import Def
from vxpy.core.ipc import build_pipes, set_process
from vxpy import Logging
from vxpy.Logging import setup_log_queue
from vxpy.core import routine, ipc
from vxpy.core import container
from vxpy.gui.window_controls import ProcessMonitorWidget
from vxpy.core.attribute import ArrayAttribute, build_attributes, get_permanent_attributes, get_permanent_data

# Type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Union


##################################
# Process BASE class

class AbstractProcess:
    """AbstractProcess class, which is inherited by all processes.

    All processes **need to** implement the "main" method, which is called once on
    each iteration of the event loop.
    """
    name: str

    interval: float
    _running: bool
    _shutdown: bool

    # Protocol related
    phase_start_time: float = None
    phase_time: float = None
    program_start_time: float = None

    enable_idle_timeout: bool = True
    _registered_callbacks: dict = dict()

    _routines: Dict[str, Dict[str, routine.Routine]] = dict()
    file_container: Union[None, h5py.File, container.NpBufferedH5File, container.H5File] = None
    record_group: str = None
    compression_args: Dict[str, Any] = dict()

    def __init__(self,
                 _program_start_time=None,
                 _configurations=None,
                 _controls=None,
                 _log=None,
                 _proxies=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 _attrs=None,
                 **kwargs):

        if _program_start_time is not None:
            self.program_start_time = _program_start_time

        # Set modules instance
        set_process(self)

        # Build pipes
        build_pipes(_pipes)

        # Build attributes
        build_attributes(_attrs)

        # Set logger
        setup_log_queue(_log)

        # Set configurations
        if _configurations is not None:
            Config.__dict__.update(_configurations)

        # Set controls
        if _controls is not None:
            for ckey, control in _controls.items():
                setattr(ipc.Control, ckey, control)

        if _proxies is not None:
            for pkey, proxy in _proxies.items():
                setattr(ipc, pkey, proxy)

        # Set states
        if not (_states is None):
            for skey, state in _states.items():
                setattr(ipc.State, skey, state)

        # Set additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set routines and let routine wrapper create hooks in modules instance and initialize buffers
        if isinstance(_routines, dict):
            self._routines = _routines
            if self.name in self._routines:
                process_routines = self._routines[self.name]
                for _routine in process_routines.values():
                    for fun in _routine.exposed:
                        try:
                            self.register_rpc_callback(_routine, fun.__qualname__, fun)
                        except:
                            # This is a workaround. Please do not remove or you'll break the GUI.
                            # In order for some IPC features to work the, AbstractProcess init has to be
                            # called **before** the PySide6.QtWidgets.QMainWindow init in the GUI modules.
                            # Doing this, however, causes an exception about failing to call
                            # the QMainWindow super-class init, since "createHooks" directly sets attributes
                            # on the new, uninitialized QMainWindow sub-class.
                            # Catching this (unimportant) exception prevents a crash.
                            pass

                    # Run local initialization for producer modules
                    _routine._connect_triggers(_routines)
                    _routine.initialize()

        # Set modules state
        if not (getattr(ipc.State, self.name) is None):
            ipc.set_state(Def.State.STARTING)

        # Bind signals
        signal.signal(signal.SIGINT, self.handle_SIGINT)

        self.local_t: float = time.perf_counter()
        self.global_t: float = 0.

        event.post_event('register_rpc')

    def run(self, interval):
        self.interval = interval
        Logging.write(Logging.INFO, f'Process started')

        # Set state to running
        self._running = True
        self._shutdown = False

        # Set modules state
        ipc.set_state(Def.State.IDLE)

        min_sleep_time = ipc.Control.General[Def.GenCtrl.min_sleep_time]
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
                # print(f'{self.name} says {self.t}')
                api.gui_rpc(ProcessMonitorWidget.update_process_interval, self.name, interval, mdt, sdt, _send_verbosely=False)

            # Wait until interval time is up
            dt = (self.local_t + interval) - time.perf_counter()
            if self.enable_idle_timeout and dt > (1.2 * min_sleep_time):
                # Sleep to reduce CPU usage
                time.sleep(dt / 1.2)

            # Busy loop until next main execution for precise timing
            # while self.t + interval - time.perf_counter() >= 0:
            while time.perf_counter() < (self.local_t + interval):
                pass

            # Set new modules time for this iteration
            self.local_t = time.perf_counter()

            # Set new global time
            self.global_t = time.time() - self.program_start_time

            # Execute main method
            self.main()

    def main(self):
        """Event loop to be re-implemented in subclass"""
        raise NotImplementedError('Event loop of modules base class is not implemented in {}.'
                                  .format(self.name))

    ################################
    # PROTOCOL RESPONSE

    def start_protocol(self):
        """Method is called when a new protocol has been started by Controller."""
        raise NotImplementedError('Method "start_protocol not implemented in {}.'
                                  .format(self.name))

    def prepare_phase(self):
        pass

    def start_phase(self):
        """Method is called when the Controller has set the next protocol phase."""
        raise NotImplementedError('Method "start_phase" not implemented in {}.'
                                  .format(self.name))

    def end_phase(self):
        """Method is called at end of stimulation protocol phase phase."""
        raise NotImplementedError('Method "end_phase" not implemented in {}.'
                                  .format(self.name))

    def end_protocol(self):
        """Method is called after the last phase at the end of the protocol."""
        raise NotImplementedError('Method "end_protocol" not implemented in {}.'
                                  .format(self.name))

    def _run_protocol(self):
        """Method can be called by all processes that in some way respond to
        the protocol control states.

        Returns True of protocol is currently running and False if not.
        """

        ########
        # RUNNING
        if self.in_state(Def.State.RUNNING):

            # If phase stoptime is exceeded: end phase
            if ipc.Control.Protocol[Def.ProtocolCtrl.phase_stop] < time.time():
                self.end_phase()
                self.set_state(Def.State.PHASE_END)
                return False

            # Default: set phase time and execute protocol
            self.phase_time = time.time() - self.phase_start_time
            return True

        ########
        # IDLE
        elif self.in_state(Def.State.IDLE):

            # Ctrl PREPARE_PROTOCOL
            if self.in_state(Def.State.PREPARE_PROTOCOL, Def.Process.Controller):
                self.start_protocol()

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

            # self.set_record_group(f'phase{ipc.Control.Recording[Def.RecCtrl.record_group_counter]}')
            # Prepare phase for start
            self.prepare_phase()

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
                if ipc.Control.Protocol[Def.ProtocolCtrl.phase_start] <= t:
                    Logging.write(Logging.DEBUG, 'Start at {}'.format(t))
                    self.set_state(Def.State.RUNNING)
                    self.phase_start_time = t
                    break

            # Immediately start phase
            self.start_phase()

            return False

        ########
        # PHASE_END
        elif self.in_state(Def.State.PHASE_END):

            ####
            ## Ctrl in PREPARE_PHASE -> there's a next phase
            if self.in_state(Def.State.PREPARE_PHASE, Def.Process.Controller):
                self.set_state(Def.State.WAIT_FOR_PHASE)


            elif self.in_state(Def.State.PROTOCOL_END, Def.Process.Controller):

                self.end_protocol()

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
            time.sleep(ipc.Control.General[Def.GenCtrl.min_sleep_time])

    def get_state(self, process=None):
        """Convenience function for access in modules class"""
        return ipc.get_state()

    def set_state(self, code):
        """Convenience function for access in modules class"""
        ipc.set_state(code)

    def in_state(self, code, process_name=None):
        """Convenience function for access in modules class"""
        if process_name is None:
            process_name = self.name
        return ipc.in_state(code, process_name)

    def _start_shutdown(self):
        # Handle all pipe messages before shutdown
        while ipc.Pipes[self.name][1].poll():
            self.handle_inbox()

        # Set modules state
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

        # RPC on modules class
        if fun_path[0] == self.__class__.__name__:
            fun_str = fun_path[1]

            try:

                if _send_verbosely:
                    Logging.write(Logging.DEBUG,
                                  f'RPC call to modules <{fun_str}> with Args {args} and Kwargs {kwargs}')

                getattr(self, fun_str)(*args, **kwargs)

            except Exception as exc:
                import traceback
                print(traceback.print_exc())

                Logging.write(Logging.WARNING,
                              f'RPC call to modules <{fun_str}> failed with Args {args} and Kwargs {kwargs}'
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
                import traceback
                traceback.print_exc()

                Logging.write(Logging.WARNING,
                              f'RPC call to callback <{fun_str}> failed with Args {args} and Kwargs {kwargs}'
                              f' // Exception: {exc}')


        else:
            Logging.write(Logging.WARNING, 'Function for RPC of method \"{}\" not found'.format(fun_str))

    def handle_inbox(self, *args):

        # Poll pipe
        if not (ipc.Pipes[self.name][1].poll()):
            return

        # Receive
        msg = ipc.Pipes[self.name][1].recv()

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

    def _create_dataset(self, path: str, attr_shape: tuple, attr_dtype: Any):

        # Skip if dataset exists already
        if path in self.file_container:
            Logging.write(Logging.WARNING, f'Tried to create existing attribute {path}')
            return

        try:
            self.file_container.require_dataset(path,
                                               shape=(0, *attr_shape,),
                                               dtype=attr_dtype,
                                               maxshape=(None, *attr_shape,),
                                               chunks=(1, *attr_shape,),
                                               **self.compression_args)
            Logging.write(Logging.DEBUG, f'Create record dataset "{path}"')

        except Exception as exc:
            import traceback
            Logging.write(Logging.WARNING,
                          f'Failed to create record dataset "{path}"'
                          f' // Exception: {exc}')
            traceback.print_exc()

    def _append_to_dataset(self, path: str, value: Any):

        # Create dataset (if necessary)
        if path not in self.file_container:
            # Some datasets may not be created on record group creation
            # (this is e.g. the the case for parameters of visuals,
            # because unless the data types are specifically declared,
            # there's no way to know them ahead of time)

            # Iterate over dictionary contents
            if isinstance(value, dict):
                for k, v in value.items():
                    self._append_to_dataset(f'{path}_{k}', v)
                return

            # Try to cast to numpy arrays
            if isinstance(value, list):
                value = np.array(value)
            elif isinstance(value, np.ndarray):
                pass
            else:
                value = np.array([value])

            dshape = value.shape
            dtype = value.dtype
            assert np.issubdtype(dtype, np.number) or dtype == bool, \
                f'Unable save non-numerical value "{value}" to dataset "{path}"'

            self._create_dataset(path, dshape, dtype)

        # Append to dataset
        self.file_container.append(path, value)

    def _routine_on_record(self, routine_name):
        return f'{self.name}/{routine_name}' in Config.Recording[Def.RecCfg.routines]

    def set_record_group_attrs(self, group_attributes: Dict = None):
        if self.file_container is None:
            return

        grp = self.file_container.require_group(self.record_group)
        if group_attributes is not None:
            grp.attrs.update(group_attributes)

    def set_record_group(self, group_name: str):
        if self.file_container is None:
            return

        # Save last results (this should also delete large temp. files)
        self.file_container.save()

        self.record_group = group_name

        if not(bool(self.record_group)):
            return

        # Set group
        self.file_container.require_group(self.record_group)
        Logging.write(Logging.INFO, f'Set record group "{self.record_group}"')

        # Create attributes in group
        for attr in get_permanent_attributes():
            if not isinstance(attr, ArrayAttribute):
                continue

            path = f'{self.record_group}/{attr.name}'
            self._create_dataset(path, attr.shape, attr.dtype[1])
            self._create_dataset(f'{path}_time', (1,), np.float64)

    def update_routines(self, *args, **kwargs):

        # Handle file container
        if ipc.Control.Recording[Def.RecCtrl.active]:
            if self.file_container is None:
                if not (bool(ipc.Control.Recording[Def.RecCtrl.folder])):
                    Logging.write(Logging.WARNING, 'Recording has been started but output folder is not set.')
                    return None

                # If output folder is set: open file
                rec_folder = ipc.Control.Recording[Def.RecCtrl.folder]
                filepath = os.path.join(rec_folder, f'{self.name}.hdf5')

                # Open new file
                Logging.write(Logging.DEBUG, f'Open new file {filepath}')
                self.file_container = container.NpBufferedH5File(filepath, 'w')
                # self.file_container = container.H5File(filepath, 'a')

                # Set compression
                compr_method = ipc.Control.Recording[Def.RecCtrl.compression_method]
                compr_opts = ipc.Control.Recording[Def.RecCtrl.compression_opts]
                self.compression_args = dict()
                if compr_method is not None:
                    self.compression_args = {'compression': compr_method, **compr_opts}

                # Set current group to root
                self.set_record_group('')

        else:
            if self.file_container is not None:
                self.file_container.close()
                self.file_container = None

        # Call routine main functions
        if self.name in self._routines:
            for routine_name, routine in self._routines[self.name].items():
                routine.main(*args, **kwargs)

        if not(ipc.Control.Recording[Def.RecCtrl.active]) or self.file_container is None:
            return

        # Write attributes to file
        _iter = get_permanent_data()
        if _iter is None:
            return

        for attr_name, attr_idx, attr_time, attr_data in _iter.__iter__():

            if attr_time is None or attr_data is None:
                continue

            path = f'{self.record_group}/{attr_name}'
            self._append_to_dataset(path, attr_data)
            self._append_to_dataset(f'{path}_time', attr_time)

    @property
    def routines(self):
        return self._routines

    def handle_SIGINT(self, sig, frame):
        print(f'> SIGINT handled in  {self.__class__}')
        sys.exit(0)


class ProcessProxy:
    def __init__(self, name):
        self.name = name
        self._state: mp.Value = getattr(ipc.State, self.name)

    @property
    def state(self):
        return self._state.value

    def in_state(self, state):
        return self.state == state

    def rpc(self, function: Callable, *args, **kwargs) -> None:
        """Send a remote procedure call of given function to another modules.

        @param process_name:
        @param function:
        @param args:
        @param kwargs:
        """
        ipc.rpc(self.name, function, *args, **kwargs)
