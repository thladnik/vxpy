"""Process core module

Contains base class for all process modules, including controller and submodules.
"""
from __future__ import annotations

import numpy as np
import signal
import sys
import time
from typing import Any, Callable, List, Union, Tuple, Dict, Type

import vxpy
import vxpy.calibration
import vxpy.configuration
from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.container as vxcontainer
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.protocol as vxprotocol
import vxpy.core.routine as vxroutine
from vxpy.definitions import *

log = vxlogger.getLogger(__name__)


def run_process(target: AbstractProcess, **kwargs):
    """Initialization function for forked processes

    This function should only be used in the Controller and constructs the AbstractProcess
    implementation within the respective subprocess.

    Args:
        target: A reimplementation of AbstractProcess
        kwargs: Arguments to be provided to the constructor of AbstractProcess implementation
    """

    # Set up logging
    vxlogger.setup_log_queue(kwargs.get('_log_queue'))
    log = vxlogger.getLogger(target.name)
    # Bind logging functions
    vxlogger.debug = log.debug
    vxlogger.info = log.info
    vxlogger.warning = log.warning
    vxlogger.error = log.error
    vxlogger.setup_log_history(kwargs.get('_log_history'))

    return target(**kwargs)


class AbstractProcess:
    """Class which is reimplemented by every process implementation"""

    name: str

    interval: float
    _running: bool
    _shutdown: bool
    program_start_time: float = None

    # Protocol related
    current_protocol: Union[vxprotocol.StaticProtocol,
                            vxprotocol.TriggeredProtocol,
                            vxprotocol.ContinuousProtocol,
                            None] = None
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
                 _configuration_data=None,
                 _controls=None,
                 _log=None,
                 _pipes=None,
                 _routines=None,
                 _states=None,
                 _attrs=None,
                 **kwargs):

        # Register default file container types
        vxcontainer.register_file_type(vxcontainer.H5File.__name__, vxcontainer.H5File)

        # Reset logger to include process_name
        global log
        log = vxlogger.getLogger(f'{__name__}[{self.name}]')

        if _program_start_time is not None:
            self.program_start_time = _program_start_time
        else:
            log.error(f'No program start time provided to {self.name}')
            return

        # Add handlers to modules that were imported before process class initialization
        vxlogger.add_handlers()

        # Set modules instance
        vxipc.init(self, pipes=_pipes, states=_states, controls=_controls)

        # Build attributes
        vxattribute.init(_attrs)

        # Initialize container module
        vxcontainer.init()

        # Load configuration
        vxpy.configuration.set_configuration_data(_configuration_data)
        # config_loaded = vxconfig.load_configuration(_configuration_path)
        # assert config_loaded, f'Loading of configuration file {_configuration_path} failed. Check log for details.'

        # Load calibration
        vxpy.calibration.load_calibration(config.PATH_CALIBRATION)

        # Set additional attributes to process instance
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set routines and let routine wrapper create hooks in modules instance
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
        vxipc.set_state(STATE.STARTING)

        # Bind signals
        signal.signal(signal.SIGINT, self.handle_sigint)

        self.next_iteration_time: float = 0.0
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
            vxipc.gui_rpc('ProcessMonitorWidget.update_process_interval', *update_args, _send_verbosely=False)

    def run(self, interval: float):
        """Function to run the event loop of the process

        Args:
            interval: the target interval at which the event loop should run
        """

        self.interval = interval
        log.info(f'Process started')

        # Set state to running
        self._running = True
        self._shutdown = False

        # Set modules state
        vxipc.set_state(STATE.IDLE)

        min_sleep_time = vxipc.CONTROL[CTRL_MIN_SLEEP_TIME]
        # Run event loop
        while self._is_running():
            self._handle_inbox()

            # Evaluate basic operational states, such as idle, recording, etc
            self._eval_process_state()

            # If particular fork implements protocol functionality, evaluate protocol states
            if self.name in self._protocolized:
                self._eval_protocol_state()

            # Calculate iteration time statistics
            self._keep_time()

            # Wait until interval time is up
            vxipc.update_time()
            dt = self.next_iteration_time - vxipc.get_time()
            if self.enable_idle_timeout and dt > (1.2 * min_sleep_time):
                # Sleep to reduce CPU usage
                time.sleep(0.9 * dt)

            # Busy loop until next main execution for precise timing
            while vxipc.get_time() < self.next_iteration_time:
                vxipc.update_time()

            # Set new local time
            vxipc.update_time()

            # Process triggers
            for trigger in vxevent.Trigger.all:
                trigger.process()

            # Execute main method
            self.main()

            # Add record_phase_group_id and corresponding global time if
            # anything is to be written to file from this process
            if len(vxattribute.Attribute.to_file) > 0:
                record_phase_group_id = self.record_phase_group_id if self.phase_is_active else -1
                vxcontainer.add_to_dataset('__record_group_id', record_phase_group_id)
                vxcontainer.add_to_dataset('__time', vxipc.get_time())

            # Set next iteration time
            self.next_iteration_time = vxipc.get_time() + self.interval

    def main(self):
        """Event loop to be re-implemented in subclass"""
        raise NotImplementedError(f'Event loop of modules base class is not implemented in {self.name}.')

    # Shared control properties

    # Recording

    @property
    def record_base_path(self) -> str:
        """Recording base folder path"""
        return vxipc.CONTROL[CTRL_REC_BASE_PATH]

    @property
    def recording_folder_name(self) -> str:
        """Folder name of current recording"""
        return vxipc.CONTROL[CTRL_REC_FLDNAME]

    @property
    def recording_active(self) -> bool:
        """Flag which indicates if recording is currently active"""
        return vxipc.CONTROL[CTRL_REC_ACTIVE]

    @property
    def record_protocol_group_id(self) -> int:
        """Record ID of the currently active protocol"""
        return vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID]

    @property
    def record_phase_group_id(self) -> int:
        """Record ID of the currently active protocol phase"""
        return vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID]

    # Protocol

    @property
    def protocol_type(self) -> Type[vxprotocol.BaseProtocol]:
        """Type of the currently active protocol
        """
        return vxipc.CONTROL[CTRL_PRCL_TYPE]

    @property
    def protocol_import_path(self) -> str:
        """The full import path to the currently active protocol"""
        return vxipc.CONTROL[CTRL_PRCL_IMPORTPATH]

    @property
    def phase_id(self) -> int:
        """The current phase ID within the currently active protocol"""
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def phase_info(self) -> dict:
        """The current phase ID within the currently active protocol"""
        return vxipc.CONTROL[CTRL_PRCL_PHASE_INFO]

    @property
    def phase_start_time(self) -> float:
        """Start time in application time (seconds since start of app) of the currently active protocol phase"""
        return vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME]

    @property
    def phase_active(self) -> bool:
        """Flag whether protocol phase is currently active"""
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ACTIVE]

    @property
    def phase_end_time(self) -> float:
        """End time in application time (seconds since start of app) of the currently active protocol phase"""
        return vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME]

    @property
    def phase_is_active(self) -> bool:
        """Flag which is True if the current local time is within
        the defined start and end times of of the currently active protocol phase
        """
        return self.phase_start_time <= vxipc.get_time() < self.phase_end_time

    def prepare_static_protocol(self):
        """To be reimplemented in fork. Method is called by _prepare_static_protocol"""
        pass

    def prepare_static_protocol_phase(self):
        """Method is called when the Controller has set the next protocol phase."""
        pass

    def start_static_protocol_phase(self):
        """To be reimplemented in fork. Method is called by _start_static_protocol_phase"""
        pass

    def end_static_protocol_phase(self):
        """Method is called at end of stimulation protocol phase."""
        pass

    def end_static_protocol(self):
        """Method is called after the last phase at the end of the protocol."""
        pass

    def prepare_trigger_protocol(self):
        """To be reimplemented in fork"""
        pass

    def prepare_trigger_protocol_phase(self):
        """To be reimplemented in fork"""
        pass

    def start_trigger_protocol_phase(self):
        """To be reimplemented in fork"""
        pass

    def end_trigger_protocol_phase(self):
        """To be reimplemented in fork"""
        pass

    def _recording_attributes(self) -> Dict[str, Any]:
        """To be reimplemented in fork.

        Returns a dictionary of key-value pairs with session data that should
        be saved to the process's record file.
        """
        return {}

    def _start_recording(self):
        """Start a new recording to disk

        Method opens a new file container and adds basic version and debug information.
        It also creates the ``__record_group_id`` and corresponding ``__time`` datasets in file
        and datasets for all ``vxpy.core.attribute.Attribute`` instances that have been marked
        to be saved to disk via a call to ``vxpy.core.attribute.write_to_file``
        """

        # Open new file for recording
        log.debug(f'Start recording to {vxipc.get_recording_path()}')
        vxcontainer.new('H5File', os.path.join(vxipc.get_recording_path(), f'{self.name}'))

        # Add recording attributes
        vxcontainer.add_attributes({'__vxpy_version': vxpy.get_version(),
                                    '__vxpy_status': vxpy.__status__,
                                    **self._recording_attributes()})

        # Add record group and time datasets
        vxcontainer.create_dataset('__record_group_id', (1,), np.int32)
        vxcontainer.create_dataset('__time', (1,), np.float64)

        # Add all shared attributes that have been selected to be written to file
        attributes_to_file = vxattribute.Attribute.to_file.get(self.name)
        if attributes_to_file is not None:
            for attribute, record_ops in attributes_to_file:

                if isinstance(attribute, vxattribute.ArrayAttribute):

                    # Check if this array should be encoded as video
                    if 'videoformat' in record_ops:
                        vxcontainer.create_video_stream(vxipc.get_recording_path(), attribute, **record_ops)
                        vxcontainer.create_dataset(f'{attribute.name}_time', (1,), np.float64)
                    elif 'save_plaintext' in record_ops:
                        vxcontainer.create_text_stream(vxipc.get_recording_path(), attribute)
                    # Otherwise just add attribute dataset
                    else:
                        vxcontainer.create_dataset(attribute.name, attribute.shape, attribute.numpytype)
                        vxcontainer.create_dataset(f'{attribute.name}_time', (1,), np.float64)

                elif isinstance(attribute, vxattribute.ObjectAttribute):

                    # Read last entry to determine structure of object
                    _, _, data = attribute.read()

                    data = data[0]
                    # TODO: do this smartly...

        return True

    def _stop_recording(self) -> bool:
        log.debug(f'Stop recording to {vxipc.get_recording_path()}')

        # Close any open file
        vxcontainer.close()

        # Close any open video streams
        vxcontainer.close_video_streams()

        # Close any open text streams
        vxcontainer.close_text_streams()

        # Switch state to let controller know recording was stopped on fork
        vxipc.set_state(STATE.REC_STOPPED)

        return True

    def _start_protocol(self):
        """"""
        # If fork has already started/loaded protocol, ignore this
        if vxipc.in_state(STATE.PRCL_STARTED):
            return

        # If fork hasn't reacted yet, do it
        log.debug(f'Load protocol from import path {self.protocol_import_path}')
        self.current_protocol = vxprotocol.get_protocol(self.protocol_import_path)()

        if self.protocol_type == vxprotocol.StaticProtocol:

            protocol_attributes = {'__protocol_module': self.current_protocol.__class__.__module__,
                                   '__protocol_name': self.current_protocol.__class__.__qualname__,
                                   '__start_time': vxipc.get_time(),
                                   '__start_record_group_id': self.record_phase_group_id + 1,  # Next id in order
                                   '__target_phase_count': self.current_protocol.phase_count,
                                   '__target_repeat_interval_ids': self.current_protocol.repeat_intervals}

            vxcontainer.add_protocol_attributes(protocol_attributes)

            # Call fork's implementation
            self.prepare_static_protocol()

        elif self.protocol_type == vxprotocol.TriggeredProtocol:

            self.last_phase_id = -1

            # Call fork's implementation
            self.prepare_trigger_protocol()

        elif self.protocol_type == vxprotocol.ContinuousProtocol:
            log.error(f'{self.protocol_type.__name__} prepare method not implemented')

        vxipc.set_state(STATE.PRCL_STARTED)

    def _started_protocol(self):
        """"""
        if not vxipc.in_state(STATE.PRCL_IN_PROGRESS, PROCESS_CONTROLLER):
            return

        # Set state
        vxipc.set_state(STATE.PRCL_STC_WAIT_FOR_PHASE)

    def _stop_protocol(self):
        """"""
        self.current_protocol = None
        vxipc.set_state(STATE.PRCL_STOPPED)

    def _stopped_protocol(self):
        """"""
        vxipc.set_state(STATE.IDLE)

    def _process_static_protocol(self):

        if self.phase_end_time < vxipc.get_time():
            if vxipc.in_state(STATE.PRCL_STC_WAIT_FOR_PHASE):
                return

            self.end_static_protocol_phase()
            log.debug(f'Wait for phase')
            vxipc.set_state(STATE.PRCL_STC_WAIT_FOR_PHASE)
            return

        elif vxipc.in_state(STATE.PRCL_STC_WAIT_FOR_PHASE):

            log.debug(f'Ready phase {self.phase_id}')

            self.prepare_static_protocol_phase()
            vxipc.set_state(STATE.PRCL_STC_PHASE_READY)

        # Leave some buffer time before actual phase start (based on process interval) to get timing right
        elif (self.phase_start_time - 1.5 * self.interval) <= vxipc.get_time() < self.phase_end_time:
            if not vxipc.in_state(STATE.PRCL_IN_PHASE):

                # Busy loop to exactly get start time right
                while vxipc.get_time() < self.phase_start_time:
                    vxipc.update_time()

                # When loop is through
                log.info(f'Run phase {self.phase_id} at {vxipc.get_time():.3f}')
                self.start_static_protocol_phase()
                vxipc.set_state(STATE.PRCL_IN_PHASE)

    def _process_trigger_protocol(self):
        # Check if protocol has not yet advanced to next phase (in Controller)
        if self.last_phase_id == self.phase_id:
            return

        self.prepare_trigger_protocol_phase()
        self.start_trigger_protocol_phase()

        self.last_phase_id = self.phase_id

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
            if not vxipc.in_state(STATE.REC_START_SUCCESS):
                started = self._start_recording()

                if started:
                    # Switch state to let controller know recording was started on fork
                    vxipc.set_state(STATE.REC_START_SUCCESS)
                else:
                    vxipc.set_state(STATE.REC_START_FAIL)

        # Controller has stopped a recording
        elif vxipc.in_state(STATE.REC_STOP, PROCESS_CONTROLLER):
            # If fork hasn't reacted yet, do it
            if not vxipc.in_state(STATE.REC_STOPPED):
                stopped = self._stop_recording()

                if stopped:
                    # Switch state to let controller know recording was stopped on fork
                    vxipc.set_state(STATE.REC_STOPPED)

        # Controller has started shutdown
        elif vxipc.in_state(STATE.SHUTDOWN, PROCESS_CONTROLLER):
            self._start_shutdown()

    def _eval_protocol_state(self):

        if vxipc.in_state(STATE.IDLE, PROCESS_CONTROLLER):
            # Check own states
            if vxipc.in_state(STATE.PRCL_STARTED):
                self._started_protocol()

            elif vxipc.in_state(STATE.PRCL_STOPPED):
                self._stopped_protocol()

        # Controller has started a protocol
        elif vxipc.in_state(STATE.PRCL_START, PROCESS_CONTROLLER):
            self._start_protocol()

        # Controller is currently running the protocol
        elif vxipc.in_state(STATE.PRCL_IN_PROGRESS, PROCESS_CONTROLLER):

            prcl_type = vxipc.CONTROL[CTRL_PRCL_TYPE]
            if prcl_type == vxprotocol.StaticProtocol:
                self._process_static_protocol()
            elif prcl_type == vxprotocol.TriggeredProtocol:
                self._process_trigger_protocol()
            elif prcl_type == vxprotocol.ContinuousProtocol:
                pass

        # Controller has stopped running protocol
        elif vxipc.in_state(STATE.PRCL_STOP, PROCESS_CONTROLLER):
            # If fork hasn't reacted yet, do it
            if not vxipc.in_state(STATE.PRCL_STOPPED):
                self._stop_protocol()

    def idle(self):
        if self.enable_idle_timeout:
            time.sleep(vxipc.CONTROL[CTRL_MIN_SLEEP_TIME])

    @staticmethod
    def get_state(process_name: str = None):
        """Convenience function for access in modules class"""
        return vxipc.get_state(process_name)

    @staticmethod
    def set_state(code):
        """Convenience function for access in modules class"""
        vxipc.set_state(code)

    def in_state(self, code: STATE, process_name: str = None):
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
            log.warning('Trying to register callback {} more than once'.format(fun_str))

    ################################
    # Private functions

    def _execute_rpc(self, fun_str: str, *args, **kwargs):
        """Execute a remote call to the specified function and pass args, kwargs
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
        if sig == SIGNAL.rpc:
            self._execute_rpc(*args, **kwargs)

    @property
    def record_group_name(self):
        return f'phase{self.record_group}' if self.record_group >= 0 else ''

    def update_routines(self, *args, **kwargs):
        """Method updates the routines of the local process and saves new attribute data to file.

        Args:
            args: List of arguments that depend on the type of the local process
            kwargs: Dict of named arguments that depend on the type of the local process
        """

        # Call routine main functions
        if self.name in self._routines:
            for routine_name, routine in self._routines[self.name].items():
                routine.main(*args, **kwargs)

        # Write attributes to file
        data = vxattribute.get_permanent_data()

        if data is None:
            return

        for attribute, record_ops in data:

            _, attr_time, attr_data = [v[0] for v in attribute.read()]

            # Add attribute data to dataset and time dataset
            if isinstance(attribute, vxattribute.ArrayAttribute) and 'videoformat' in record_ops:
                vxcontainer.add_to_video_stream(attribute.name, attr_data)
                vxcontainer.add_to_dataset(f'{attribute.name}_time', attr_time)

            elif 'save_plaintext' in record_ops and record_ops['save_plaintext']:
                vxcontainer.add_to_text_stream(attribute.name, f'{attr_time},{attr_data}')

            else:
                vxcontainer.add_to_dataset(attribute.name, attr_data)
                vxcontainer.add_to_dataset(f'{attribute.name}_time', attr_time)

    def handle_sigint(self, sig, frame):
        """Method called on system interrupt.

        Ensures that, when the program crashes or is insterrupted,
        the process exists by itself.
        """
        print(f'> SIGINT handled in  {self.__class__}')
        sys.exit(0)
