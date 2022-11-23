"""
vxPy ./core/process.py
Copyright (C) 2022 Tim Hladnik

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

import numpy as np
import signal
import sys
import time
from typing import Any, Callable, List, Union, Tuple

from vispy import gloo

from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.calibration as vxcalib
import vxpy.core.configuration as vxconfig
import vxpy.core.container as vxcontainer
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.protocol as vxprotocol
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxui
from vxpy.definitions import *

log = vxlogger.getLogger(__name__)


##################################
# Process BASE class

class AbstractProcess:
    """AbstractProcess class, which is inherited by all modules.

    All processes **need to** implement the "main" method, which is called once on
    each iteration of the event loop.
    """
    name: str

    interval: float
    _running: bool
    _shutdown: bool
    _disable_phases = True
    program_start_time: float = None

    # Protocol related
    current_protocol: Union[vxprotocol.AbstractProtocol, None] = None
    phase_time: float = None

    enable_idle_timeout: bool = True
    _registered_callbacks: Dict[str, Tuple[object, Callable]] = {}
    _protocolized: List[str] = [PROCESS_DISPLAY, PROCESS_IO]

    _routines: Dict[str, Dict[str, vxroutine.Routine]] = dict()
    file_container: Union[None, vxcontainer.H5File] = None
    record_group: int = -1
    compression_args: Dict[str, Any] = {}

    def __init__(self,
                 _program_start_time=None,
                 _configuration_path=None,
                 _controls=None,
                 _control=None,
                 _log=None,
                 _proxies=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 _attrs=None,
                 **kwargs):

        # Reset logger to include process_name
        global log
        log = vxlogger.getLogger(f'{__name__}[{self.name}]')

        if _program_start_time is not None:
            self.program_start_time = _program_start_time
        else:
            log.error(f'No program start time provided to {self.name}')

        # Add handlers to modules that were imported before process class initialization
        vxlogger.add_handlers()

        # Set modules instance
        vxipc.init(self, _pipes, _states, _proxies, _control, _controls)

        # Build attributes
        vxattribute.init(_attrs)

        # Load configuration
        config_loaded = vxconfig.load_configuration(_configuration_path)
        assert config_loaded, f'Loading of configuration file {_configuration_path} failed. Check log for details.'

        # Load calibration
        vxcalib.load_calibration(config.CONF_CALIBRATION_PATH)

        # Set additional attributes to process instance
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set routines and let routine wrapper create hooks in modules instance and initialize buffers
        if _routines is not None and isinstance(_routines, dict):
            self._routines = _routines
            if self.name in self._routines:

                process_routines = self._routines[self.name]

                for routine in process_routines.values():

                    # Run local initialization for producer modules (this needs to happen before callback reg.)
                    routine.initialize()

                    for fun in routine.callback_ops:

                        try:
                            self.register_rpc_callback(routine, fun)
                        except:
                            # This is a workaround. Please do not remove or you'll break the GUI.
                            # In order for some IPC features to work the, AbstractProcess init has to be
                            # called **before** the PySide6.QtWidgets.QMainWindow init in the GUI modules.
                            # Doing this, however, causes an exception about failing to call
                            # the QMainWindow super-class init, since "createHooks" directly sets attributes
                            # on the new, uninitialized QMainWindow sub-class.
                            # Catching this (unimportant) exception prevents a crash.
                            pass

        # Set modules state
        if getattr(vxipc.State, self.name) is not None:
            vxipc.set_state(State.STARTING)

        # Bind signals
        signal.signal(signal.SIGINT, self.handle_sigint)

        self.global_t: float = 0.0
        self.next_iter_global_t: float = 0.0
        self.loop_times: List[float] = [time.perf_counter()]

    def _keep_time(self):
        self.loop_times.append(time.perf_counter())
        if (self.loop_times[-1] - self.loop_times[0]) > 1.:
            dt = np.diff(self.loop_times)
            mean_dt = np.mean(dt)
            std_dt = np.std(dt)
            # print('Avg loop time in {} {:.2f} +/- {:.2f}ms'.format(self.name, mean_dt * 1000, std_dt * 1000))
            self.loop_times = [self.loop_times[-1]]
            # print(f'{self.name} says {self.t}')
            update_args = (self.name, self.interval, mean_dt, std_dt)
            vxipc.gui_rpc(vxui.ProcessMonitorWidget.update_process_interval, *update_args, _send_verbosely=False)

    def run(self, interval: float, enable_idle_timeout: bool = True):
        """Event loop of process.
        Event loop logic:
        ---

        ---

        :param interval: Interval (in seconds) of this process' event loop
        :type interval: float
        :param enable_idle_timeout: Flag determines whether to allow sleep during idle times
        :type enable_idle_timeout: bool
        :return: None
        """

        self.interval = interval
        log.info(f'Process started')

        # Set state to running
        self._running = True
        self._shutdown = False

        # Set modules state
        vxipc.set_state(STATE.IDLE)

        min_sleep_time = vxipc.Control.General[GenCtrl.min_sleep_time]
        # Run event loop
        while self._is_running():
            self._handle_inbox()

            self._open_file()

            self._eval_process_state()

            if self.name in self._protocolized:
                self._eval_protocol_state()

            self._keep_time()

            # Wait until interval time is up
            dt = self.next_iter_global_t - (time.time() - self.program_start_time)
            if self.enable_idle_timeout and dt > (1.2 * min_sleep_time):
                # Sleep to reduce CPU usage
                time.sleep(0.9 * dt)

            # Busy loop until next main execution for precise timing
            # while self.t + interval - time.perf_counter() >= 0:
            while (time.time() - self.program_start_time) < self.next_iter_global_t:
                pass

            # Set new global time
            self.global_t = time.time() - self.program_start_time

            self.next_iter_global_t = self.global_t + self.interval

            # Add record_group_id aand corresponding global time if anything is to be written to file from this process
            if len(vxattribute.Attribute.to_file) > 0:
                self._append_to_dataset('record_group_id', vxipc.Control.Recording[RecCtrl.record_group_counter])
                self._append_to_dataset('global_time', self.global_t)

            # Process triggers
            for trigger in vxevent.Trigger.all:
                trigger.process()

            # Execute main method
            self.main()

            self._close_file()

    def main(self):
        """Event loop to be re-implemented in subclass"""
        raise NotImplementedError(f'Event loop of modules base class is not implemented in {self.name}.')

    # PROTOCOL RESPONSE

    @property
    def protocol_type(self):
        return vxipc.CONTROL[CTRL_PRCL_TYPE]

    @property
    def protocol_import_path(self):
        return vxipc.CONTROL[CTRL_PRCL_IMPORTPATH]

    @property
    def phase_id(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def phase_start_time(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME]

    @property
    def phase_active(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ACTIVE]

    @property
    def phase_end_time(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME]

    def _prepare_protocol(self):

        # Fetch protocol class
        _protocol = vxprotocol.get_protocol(vxipc.Control.Protocol[ProtocolCtrl.name])
        if _protocol is None:
            # Controller should abort this
            return

        # Make sure recording is running
        # self._open_file()

        # Instantiate protocol
        self.current_protocol = _protocol()

        # Call implemented preparation function of module
        self.prepare_protocol()

        # Let file container know that protocol was started
        self.file_container.start_protocol()
        protocol_attributes = {'__protocol_module': self.current_protocol.__class__.__module__,
                               '__protocol_name': self.current_protocol.__class__.__qualname__,
                               '__start_time': vxipc.get_time(),
                               '__target_phase_count': self.current_protocol.phase_count}

        self.file_container.add_protocol_attributes(protocol_attributes)

        # Set next state
        self.set_state(State.WAIT_FOR_PHASE)

    def prepare_protocol(self):
        """Method is called when a new protocol has been started by Controller."""
        pass

    def _prepare_protocol_phase(self):
        # Set record group to write to in file
        if not self._disable_phases:
            self.set_record_group(vxipc.Control.Recording[RecCtrl.record_group_counter])

        # Set current phase
        self.current_protocol.current_phase_id = vxipc.Control.Protocol[ProtocolCtrl.phase_id]

        # Call implemented phase initialization
        self.prepare_protocol_phase()

        # Set next state
        self.set_state(State.READY)

    def prepare_protocol_phase(self):
        """Method is called when the Controller has set the next protocol phase."""
        pass

    def _start_protocol_phase(self):
        pass

    def start_protocol_phase(self):
        """Method is called when the Controller has set the next protocol phase."""
        pass

    def end_protocol_phase(self):
        """Method is called at end of stimulation protocol phase."""
        pass

    def end_protocol(self):
        """Method is called after the last phase at the end of the protocol."""
        pass

    def _start_recording(self):
        # DO START RECORDING STUFF
        log.debug(f'Start recording to {vxipc.get_recording_path()}')

        # AND THEN, SWITCH STATE
        vxipc.set_state(STATE.REC_STARTED)

    def _stop_recording(self):
        # DO START RECORDING STUFF
        log.debug(f'Stop recording to {vxipc.get_recording_path()}')

        # AND THEN, SWITCH STATE
        vxipc.set_state(STATE.REC_STOPPED)

    def _start_protocol(self):
        # If fork has already started/loaded protocol, ignore this
        if vxipc.in_state(STATE.PRCL_STARTED):
            return

        # If fork hasn't reacted yet, do it
        log.debug(f'Load protocol from import path {self.protocol_import_path}')
        self.current_protocol = vxprotocol.get_protocol(self.protocol_import_path)()

        vxipc.set_state(STATE.PRCL_STARTED)

    def _started_protocol(self):
        if not vxipc.in_state(STATE.PRCL_IN_PROGRESS, PROCESS_CONTROLLER):
            return

        # Set state
        vxipc.set_state(STATE.PRCL_STC_WAIT_FOR_PHASE)

    def _stop_protocol(self):
        self.current_protocol = None
        vxipc.set_state(STATE.PRCL_STOPPED)

    def _stopped_protocol(self):
        vxipc.set_state(STATE.IDLE)

    def _process_static_protocol(self):

        t = vxipc.get_time()

        if self.phase_end_time < t:
            if vxipc.in_state(STATE.PRCL_STC_WAIT_FOR_PHASE):
                return

            # TODO: call phase end function
            log.debug(f'Wait for phase')
            vxipc.set_state(STATE.PRCL_STC_WAIT_FOR_PHASE)
            return

        # If phase start equals end time, this should only happen when controller sets both to inf
        elif vxipc.in_state(STATE.PRCL_STC_WAIT_FOR_PHASE):

            log.debug(f'Ready phase {self.phase_id}')

            # TODO: call method to prepare new phase in module
            vxipc.set_state(STATE.PRCL_STC_PHASE_READY)

        elif self.phase_start_time <= t < self.phase_end_time:
            if not vxipc.in_state(STATE.PRCL_STC_RUN_PHASE):
                log.info(f'Run phase {self.phase_id}')
                vxipc.set_state(STATE.PRCL_STC_RUN_PHASE)

    def _eval_process_state(self):

        # Check controller states

        # Controller is in idle
        if vxipc.in_state(STATE.IDLE, PROCESS_CONTROLLER):
            # TODO: Check different transition conditions based on CURRENT fork state
            #  i.e. are cleanups needed after protocol/abort
            #       do file handles need to be closed after recording
            #       etc...

            # Ultimately, go into idle too
            if not vxipc.in_state(STATE.IDLE):
                vxipc.set_state(STATE.IDLE)

        # Controller has started a recording
        elif vxipc.in_state(STATE.REC_START, PROCESS_CONTROLLER):
            # If fork hasn't reacted yet, do it
            if not vxipc.in_state(STATE.REC_STARTED):
                self._start_recording()

        # Controller has stopped a recording
        elif vxipc.in_state(STATE.REC_STOP, PROCESS_CONTROLLER):
            # If fork hasn't reacted yet, do it
            if not vxipc.in_state(STATE.REC_STOPPED):
                self._stop_recording()

        # Controller has started shutdown
        elif vxipc.in_state(STATE.SHUTDOWN, PROCESS_CONTROLLER):
            self._start_shutdown()

    def _eval_protocol_state(self):

        # Check own states
        if vxipc.in_state(STATE.PRCL_STARTED):
            self._started_protocol()

        elif vxipc.in_state(STATE.PRCL_STOPPED):
            self._stopped_protocol()

        # Reaction to controller states

        # Controller has started a protocol
        if vxipc.in_state(STATE.PRCL_START, PROCESS_CONTROLLER):
            self._start_protocol()

        # Controller is currently running the protocol
        elif vxipc.in_state(STATE.PRCL_IN_PROGRESS, PROCESS_CONTROLLER):

            prcl_type = vxipc.CONTROL[CTRL_PRCL_TYPE]
            if prcl_type == vxprotocol.StaticPhasicProtocol:
                self._process_static_protocol()
            elif prcl_type == vxprotocol.ContinuousProtocol:
                pass
            elif prcl_type == vxprotocol.TriggeredProtocol:
                pass

        # Controller has stopped running protocol
        elif vxipc.in_state(STATE.PRCL_STOP, PROCESS_CONTROLLER):
            # If fork hasn't reacted yet, do it
            if not vxipc.in_state(STATE.PRCL_STOPPED):
                self._stop_protocol()

    def idle(self):
        if self.enable_idle_timeout:
            time.sleep(vxipc.Control.General[GenCtrl.min_sleep_time])

    @staticmethod
    def get_state(process_name: str = None):
        """Convenience function for access in modules class"""
        return vxipc.get_state(process_name)

    @staticmethod
    def set_state(code):
        """Convenience function for access in modules class"""
        vxipc.set_state(code)

    def in_state(self, code: State, process_name: str = None):
        """Convenience function for access in modules class"""
        if process_name is None:
            process_name = self.name
        return vxipc.in_state(code, process_name)

    def _start_shutdown(self):
        # Handle all pipe messages before shutdown
        while vxipc.Pipes[self.name][1].poll():
            self._handle_inbox()

        # Set modules state
        vxipc.set_state(STATE.STOPPED)

        self._shutdown = True

    def _is_running(self):
        return self._running and not self._shutdown

    def register_rpc_callback(self, obj, fun):
        fun_str = fun.__qualname__
        if fun_str not in self._registered_callbacks:
            log.debug(f'Register callback {obj.__class__.__qualname__}:{fun_str} in module {self.name}')
            self._registered_callbacks[fun_str] = (obj, fun)
        else:
            log.warning('Trying to register callback \"{}\" more than once'.format(fun_str))

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

            msg = f'Callback to {self.name}:{fun_str} with args {args} and kwargs {kwargs}'
            try:
                if _send_verbosely:
                    log.debug(msg)

                getattr(self, fun_str)(*args, **kwargs)

            except Exception as exc:
                import traceback
                print(traceback.print_exc())

                log.warning(f'{msg} failed // Exception: {exc}')

        # RPC on registered callback
        elif fun_str in self._registered_callbacks:

            msg = f'Call registered callback {self.name}:{fun_str} with args {args} and kwargs {kwargs}'
            try:
                if _send_verbosely:
                    log.debug(msg)

                instance, fun = self._registered_callbacks[fun_str]
                fun(instance, *args, **kwargs)

            except Exception as exc:
                import traceback
                traceback.print_exc()

                log.warning(f'{msg} failed // Exception: {exc}')

        else:
            log.warning(f'Callback {self.name}:{fun_str} not found')

    def _handle_inbox(self, *args):

        # Poll pipe
        if not vxipc.Pipes[self.name][1].poll():
            return

        # Receive
        msg = vxipc.Pipes[self.name][1].recv()

        # Unpack
        sig, sender_name, args, kwargs = msg

        # Log
        if kwargs.get('_send_verbosely'):
            log.debug(f'{self.name} received message from {sender_name}. '
                      f'Signal: {sig}, args: {args}, kwargs: {kwargs}')

        # If RPC
        if sig == Signal.rpc:
            self._execute_rpc(*args, **kwargs)

    def _create_dataset(self, path: str, attr_shape: tuple, attr_dtype: Any):

        # Skip if dataset exists already
        if path in self.file_container:
            log.warning(f'Tried to create existing attribute {self.name}/{path}')
            return

        try:
            self.file_container.require_dataset(path,
                                                shape=(0, *attr_shape,),
                                                dtype=attr_dtype,
                                                maxshape=(None, *attr_shape,),
                                                chunks=(1, *attr_shape,),
                                                **self.compression_args)
            log.debug(f'Create record dataset {self.name}/{path}')

        except Exception as exc:
            import traceback
            log.warning(f'Failed to create record dataset {self.name}/{path}'
                        f' // Exception: {exc}')
            traceback.print_exc()

    def _append_to_dataset(self, path: str, value: Any):
        # May need to be uncommented:
        if self.file_container is None:
            return

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

    @property
    def record_group_name(self):
        return f'phase{self.record_group}' if self.record_group >= 0 else ''

    def set_record_group_attrs(self, group_attributes: Dict[str, Any] = None):
        if self.file_container is None:
            return

        if self.record_group < 0:
            return

        grp = self.file_container.require_group(self.record_group_name)
        if group_attributes is not None:
            for attr_name, attr_data in group_attributes.items():

                # For arrays there may be special rules
                if isinstance(attr_data, np.ndarray):

                    # There is a hard size limit on attributes of 64KB: store as dataset instead
                    if attr_data.dtype.itemsize * attr_data.size >= 64 * 2 ** 10:
                        grp.create_dataset(f'group_attr_{attr_name}', data=attr_data)
                        continue

                    # Unpack scalar attributes
                    elif attr_data.shape == (1,):
                        grp.attrs[attr_name] = attr_data[0]
                        continue

                elif isinstance(attr_data, gloo.buffer.DataBufferView):
                    # TODO: this needs to work in the future
                    #   problem: buffers can't be read, only set in vispy.
                    #            How do I get the buffer contents after it's been set?
                    continue

                # Otherwise, just write whole attribute data to attribute
                grp.attrs[attr_name] = attr_data

    def set_record_group(self, group_id: int):
        if self.file_container is None:
            return

        # Save last results (this should also delete large temp. files)
        self.file_container.save()

        self.record_group = group_id

        # Of record group is not set
        if self.record_group < 0:
            return

        # Set group
        self.file_container.require_group(self.record_group_name)
        log.info(f'Set record group "{self.record_group_name}"')

        # Create attributes in group
        for attr in vxattribute.get_permanent_attributes():
            if not isinstance(attr, vxattribute.ArrayAttribute):
                continue

            path = f'{self.record_group_name}/{attr.name}'
            self._create_dataset(path, attr.shape, attr.numpytype[1])
            self._create_dataset(f'{path}_time', (1,), np.float64)

    def _open_file(self) -> bool:
        """Check if output file should be open and open one if it should be, but isn't.
        """

        if not vxipc.Control.Recording[RecCtrl.active]:
            return True

        if self.file_container is not None:
            return True

        if not bool(vxipc.Control.Recording[RecCtrl.folder]):
            log.warning('Recording has been started but output folder is not set.')
            return False

        # If output folder is set: open file
        filepath = os.path.join(config.CONF_REC_OUTPUT_FOLDER,
                                vxipc.Control.Recording[RecCtrl.folder],
                                f'{self.name}.hdf5')

        # Open new file
        log.debug(f'Open new file {filepath}')
        self.file_container = vxcontainer.H5File(filepath, 'a')
        self._create_dataset('record_group_id', (1,), np.int32)

        # Set compression
        compr_method = vxipc.Control.Recording[RecCtrl.compression_method]
        compr_opts = vxipc.Control.Recording[RecCtrl.compression_opts]
        self.compression_args = dict()
        if compr_method is not None:
            self.compression_args = {'compression': compr_method, **compr_opts}

        # Set current group to root
        self.set_record_group(-1)

        return True

    def _close_file(self) -> bool:
        if vxipc.Control.Recording[RecCtrl.active]:
            return True

        if self.file_container is None:
            return True

        log.debug(f'Close file {self.file_container}')
        self.file_container.close()
        self.file_container = None
        return True

    def update_routines(self, *args, **kwargs):

        # Call routine main functions
        if self.name in self._routines:
            for routine_name, routine in self._routines[self.name].items():
                routine.main(*args, **kwargs)

        if not vxipc.Control.Recording[RecCtrl.active] or self.file_container is None:
            return

        # Write attributes to file
        _iter = vxattribute.get_permanent_data()
        if _iter is None:
            return

        for attr_name, attr_idx, attr_time, attr_data in _iter.__iter__():

            if attr_time is None or attr_data is None:
                continue

            path = f'{self.record_group_name}/{attr_name}'
            self._append_to_dataset(path, attr_data)
            # Keep for now for compatibility
            self._append_to_dataset(f'{path}_attr_time', attr_time)
            # New version: double leading underscores
            self._append_to_dataset(f'__attr_time_{path}', attr_time)

    @property
    def routines(self):
        return self._routines

    def handle_sigint(self, sig, frame):
        print(f'> SIGINT handled in  {self.__class__}')
        sys.exit(0)
