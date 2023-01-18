"""
vxPy ./modules/controller.py
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
import ctypes
import importlib
import multiprocessing as mp

import numpy as np
import sys

from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
import time
from typing import List, Tuple, Union

import vxpy
from vxpy import config
from vxpy import definitions
from vxpy.definitions import *
import vxpy.modules as vxmodules
import vxpy.core.attribute as vxattribute
import vxpy.core.devices.serial as vxserial
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.protocol as vxprotocol
import vxpy.core.process as vxprocess
import vxpy.core.routine as vxroutine
from vxpy.core.dependency import register_camera_device, register_io_device, assert_device_requirements
from vxpy.core import run_process

log = vxlogger.getLogger(__name__)


class Controller(vxprocess.AbstractProcess):
    name = PROCESS_CONTROLLER

    configfile: str = None

    _processes: Dict[str, mp.Process] = dict()
    _registered_processes: List[Tuple[vxprocess.AbstractProcess, Dict]] = list()

    _active_process_list: List[str] = []
    _active_protocol_list: List[str] = []

    protocol_trigger: vxevent.Trigger = None

    def __init__(self, _configuration_path):
        # Set up manager
        vxipc.Manager = mp.Manager()

        # Set up logging
        vxlogger.setup_log_queue(vxipc.Manager.Queue())
        vxlogger.setup_log_history(vxipc.Manager.list())
        vxlogger.setup_log_to_file(f'{time.strftime("%Y-%m-%d-%H-%M-%S")}.log')

        # Manually set up pipe for controller
        vxipc.Pipes[self.name] = mp.Pipe()

        # Set up STATES
        vxipc.State.Controller = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)
        vxipc.State.Camera = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)
        vxipc.State.Display = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)
        vxipc.State.Gui = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)
        vxipc.State.Io = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)
        vxipc.State.Worker = vxipc.Manager.Value(ctypes.c_int8, STATE.NA)

        # Initialize process
        vxprocess.AbstractProcess.__init__(self, _program_start_time=time.time(), _configuration_path=_configuration_path)

        # Generate and show splash screen
        # TODO: Splashscreen blocks display of GUI under linux
        if sys.platform == 'win32':
            self.qt_app = QtWidgets.QApplication([])
            pngpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.png')

            # Optionally re-render splash
            self._render_splashscreen(pngpath)

            self.splashscreen = QtWidgets.QSplashScreen(f=QtCore.Qt.WindowStaysOnTopHint,
                                                        screen=self.qt_app.screens()[config.CONF_GUI_SCREEN])
            self.splashscreen.setPixmap(QtGui.QPixmap(pngpath))
            self.splashscreen.show()

            # Process events once
            self.qt_app.processEvents()

        # Set up processes
        _routines_to_load = {}
        # Camera
        if config.CONF_CAMERA_USE:
            self._register_process(vxmodules.Camera)
            _routines_to_load[PROCESS_CAMERA] = config.CONF_CAMERA_ROUTINES
        # Display
        if config.CONF_DISPLAY_USE:
            self._register_process(vxmodules.Display)
            _routines_to_load[PROCESS_DISPLAY] = config.CONF_DISPLAY_ROUTINES
        # GUI
        if config.CONF_GUI_USE:
            self._register_process(vxmodules.Gui)
        # IO
        if config.CONF_IO_USE:

            # Load IO devices without setting them up, so routines have a view on available connectivity
            for device_id, device_config in config.CONF_IO_DEVICES.items():

                # Get device for device_id
                device = vxserial.get_serial_device_by_id(device_id)

                # Go through alle pins
                for pin_id, pin in device.get_pins():

                    # Determine signal type
                    prefix = vxmodules.Io.get_pin_prefix(pin)
                    if pin.signal_type == vxserial.PINSIGTYPE.ANALOG:
                        datatype = vxattribute.ArrayType.float64
                    else:
                        datatype = vxattribute.ArrayType.bool

                    vxattribute.ArrayAttribute(f'{prefix}_{pin_id}', (1,), datatype)

            # Register process and get configured routines
            self._register_process(vxmodules.Io)
            _routines_to_load[PROCESS_IO] = config.CONF_IO_ROUTINES

        # Worker
        if config.CONF_WORKER_USE:
            self._register_process(vxmodules.Worker)
            _routines_to_load[PROCESS_WORKER] = config.CONF_WORKER_ROUTINES

        # Select subset of registered processes which should implement
        # the _run_protocol method
        self._active_process_list = [p[0].__name__ for p in self._registered_processes]
        self._active_protocol_list = list(set(self._active_process_list) & set(self._protocolized))
        log.info(f'Protocolized processes: {self._active_protocol_list}')

        # TODO: check if recording routines contains any entries
        #  for inactive processes or inactive routines on active processes
        #  print warning or just shut down completely in-case?

        ################################
        # Set up CONTROLS

        # General
        vxipc.Control.General = vxipc.Manager.dict()
        # Set avg. minimum sleep period
        times = list()
        for i in range(100):
            t = time.perf_counter()
            time.sleep(10 ** -10)
            times.append(time.perf_counter() - t)
        vxipc.Control.General.update({definitions.GenCtrl.min_sleep_time: max(times)})
        log.info(f'Minimum sleep period is {(1000 * max(times)):.3f}ms')

        # Check time precision on system
        dt = list()
        t0 = time.time()
        while len(dt) < 100:
            t1 = time.time()
            if t1 > t0:
                dt.append(t1 - t0)
        avg_dt = sum(dt) / len(dt)
        msg = f'Timing precision on system {1000 * avg_dt:3f}ms'
        if avg_dt > 0.001:
            log.warning(msg)
        else:
            log.info(msg)

        # Protocol
        vxipc.Control.Protocol = vxipc.Manager.dict({ProtocolCtrl.name: None,
                                                     ProtocolCtrl.phase_id: None,
                                                     ProtocolCtrl.phase_start: None,
                                                     ProtocolCtrl.phase_stop: None})

        # NEW UNIFIED CONTROL:
        vxipc.CONTROL = vxipc.Manager.dict(self._create_shared_controls())

        # Set configured cameras
        if config.CONF_CAMERA_USE:
            for device_id in config.CONF_CAMERA_DEVICES:
                register_camera_device(device_id)

        # Set configured io devices
        if config.CONF_IO_USE:
            for device_id in config.CONF_IO_DEVICES:
                register_io_device(device_id)

        # Load routine modules
        self._routines: Dict[str, Dict[str, vxroutine.Routine]] = {}
        for process_name, routine_list in _routines_to_load.items():
            self._routines[process_name] = {}
            for path in routine_list:
                log.info(f'Load routine {path}')

                # TODO: search different paths for package structure redo
                # Load routine
                parts = path.split('.')
                module = importlib.import_module('.'.join(parts[:-1]))
                routine_cls = getattr(module, parts[-1])
                if routine_cls is None:
                    log.error(f'Routine {path} not found.')
                    continue

                # Instantiate
                self._routines[process_name][routine_cls.__name__]: vxroutine.Routine = routine_cls()

        # Compare required vs registered devices
        assert_device_requirements()

        # Set up routines
        for rs in self._routines.values():
            for r in rs.values():
                r.require()
                r.setup()

        # Initialize attributes for Controller (no argument needed, attributes are already set)
        vxattribute.init(None)

        self._init_params = dict(
            _program_start_time=self.program_start_time,
            _configuration_path=_configuration_path,
            _pipes=vxipc.Pipes,
            _states={k: v for k, v
                     in vxipc.State.__dict__.items()
                     if not (k.startswith('_'))},
            _routines=self._routines,
            _controls={k: v for k, v
                       in vxipc.Control.__dict__.items()
                       if not (k.startswith('_'))},
            _control=vxipc.CONTROL,
            _log_queue=vxlogger._log_queue,
            _log_history=vxlogger.get_history(),
            _attrs=vxattribute.Attribute.all
        )

        # Initialize all processes
        for target, kwargs in self._registered_processes:
            self.initialize_process(target, **kwargs)

        # Set up initial recording states
        self.set_compression_method(None)
        self.set_compression_opts(None)

    @staticmethod
    def _create_shared_controls():
        _controls = {CTRL_REC_ACTIVE: False,
                     CTRL_REC_BASE_PATH: os.path.join(os.getcwd(), PATH_RECORDING_OUTPUT),
                     CTRL_REC_FLDNAME: '',
                     CTRL_REC_PRCL_GROUP_ID: -1,
                     CTRL_REC_PHASE_GROUP_ID: -1,
                     CTRL_PRCL_ACTIVE: False,
                     CTRL_PRCL_IMPORTPATH: '',
                     CTRL_PRCL_TYPE: None,
                     CTRL_PRCL_PHASE_ID: -1,
                     CTRL_PRCL_PHASE_START_TIME: np.inf,
                     CTRL_PRCL_PHASE_END_TIME: -np.inf}

        return _controls

    @staticmethod
    def _reset_recording_controls():
        """Reset all (shared) controls related to recording of data to file"""
        vxipc.CONTROL[CTRL_REC_FLDNAME] = ''
        vxipc.CONTROL[CTRL_REC_ACTIVE] = False
        vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID] = -1
        vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] = -1

    @staticmethod
    def _reset_protocol_controls():
        """Reset all (shared) controls related to protocol execution"""
        vxipc.CONTROL[CTRL_PRCL_ACTIVE] = False
        vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = ''
        vxipc.CONTROL[CTRL_PRCL_TYPE] = None
        vxipc.CONTROL[CTRL_PRCL_PHASE_ACTIVE] = False
        vxipc.CONTROL[CTRL_PRCL_PHASE_ID] = -1
        vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME] = np.inf
        vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME] = -np.inf

    def _register_process(self, target, **kwargs):
        """Register new modules to be spawned.

        :param target: modules class
        :param kwargs: optional keyword arguments for initialization of modules class
        """
        self._registered_processes.append((target, kwargs))
        vxipc.Pipes[target.name] = mp.Pipe()

    def initialize_process(self, target, **kwargs):

        process_name = target.name

        if process_name in self._processes:
            # Terminate modules
            log.info(f'Restart modules {process_name}')
            self._processes[process_name].terminate()

            # Set modules state
            # (this is the ONLY instance where a modules state may be set externally)
            getattr(vxipc.State, process_name).value = definitions.State.STOPPED

            # Delete references
            del self._processes[process_name]

        # Update keyword args
        kwargs.update(self._init_params)

        # Create subprocess
        # ctx = mp.get_context('fork')
        self._processes[process_name] = mp.Process(target=run_process, name=process_name, args=(target,), kwargs=kwargs)

        # Start subprocess
        self._processes[process_name].start()

        # Set state to IDLE
        self.set_state(definitions.State.IDLE)

    def start(self):

        # On Windows systems, show splashscreen to show that something is happening
        if sys.platform == 'win32':
            self.splashscreen.close()
            self.qt_app.processEvents()

        # Run controller
        self.run(interval=0.001)

        # Shutdown procedure
        log.debug('Wait for processes to terminate')
        while len(self._processes) > 0:

            # Check status of processes until last one is stopped
            for process_name in list(self._processes):

                # Wait on process if it hasn't stopped yet
                if not vxipc.in_state(STATE.STOPPED, process_name):
                    continue

                # Terminate process and delete references if it has stopped
                self._processes[process_name].terminate()
                del self._processes[process_name]
                del vxipc.Pipes[process_name]

        self._running = False
        self.set_state(STATE.STOPPED)

        return 0

    @staticmethod
    def set_compression_method(method):
        pass

    @staticmethod
    def set_compression_opts(opts):
        pass

    # Shared control properties

    # Recording

    @vxprocess.AbstractProcess.record_base_path.setter
    def record_base_path(self, val):
        vxipc.CONTROL[CTRL_REC_BASE_PATH] = val

    @vxprocess.AbstractProcess.recording_folder_name.setter
    def recording_folder_name(self, val):
        vxipc.CONTROL[CTRL_REC_FLDNAME] = val

    @vxprocess.AbstractProcess.recording_active.setter
    def recording_active(self, val):
        vxipc.CONTROL[CTRL_REC_ACTIVE] = val

    @vxprocess.AbstractProcess.record_phase_group_id.setter
    def record_phase_group_id(self, val):
        vxipc.CONTROL[CTRL_REC_PHASE_GROUP_ID] = val

    @vxprocess.AbstractProcess.record_protocol_group_id.setter
    def record_protocol_group_id(self, val):
        vxipc.CONTROL[CTRL_REC_PRCL_GROUP_ID] = val

    # Protocol

    @vxprocess.AbstractProcess.phase_id.setter
    def phase_id(self, val):
        vxipc.CONTROL[CTRL_PRCL_PHASE_ID] = val

    @vxprocess.AbstractProcess.phase_start_time.setter
    def phase_start_time(self, val):
        vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME] = val

    @vxprocess.AbstractProcess.phase_active.setter
    def phase_end_time(self, val):
        vxipc.CONTROL[CTRL_PRCL_PHASE_ACTIVE] = val

    @vxprocess.AbstractProcess.phase_end_time.setter
    def phase_end_time(self, val):
        vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME] = val

    @staticmethod
    def _handle_logging():
        while not vxlogger.get_queue().empty():

            # Fetch next record
            record = vxlogger.get_queue().get()

            try:
                vxlogger.add_to_file(record)
                vxlogger.add_to_history(record)
            except Exception as exc:
                import sys, traceback
                print('Exception in Logger:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def _all_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_process_list]

        return all(check)

    def _all_protocol_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_protocol_list]

        return all(check)

    def _any_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_process_list]

        return any(check)

    def _any_protocol_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_protocol_list]

        return any(check)

    @staticmethod
    def set_recording_path(path: str):
        if not vxipc.in_state(STATE.IDLE):
            log.warning(f'Failed to set new recording path to {path}. Controller busy.')
            return

        if vxipc.CONTROL[CTRL_REC_ACTIVE]:
            log.warning(f'Failed to set new recording path to {path}. Recording active.')
            return

        if os.path.exists(path) and os.path.isfile(path):
            log.warning(f'Failed to set new recording path to {path}. Path is existing file.')
            return

        log.info(f'Set new recording path to {path}')
        if not os.path.exists(path):
            log.info(f'Create new folder at {path}')
            os.mkdir(path)

        vxipc.CONTROL[CTRL_REC_BASE_PATH] = path

    @staticmethod
    def set_recording_folder(folder_name: str):
        illegal_chars = ['/', '\\']
        if not isinstance(folder_name, str) or any([s in folder_name for s in illegal_chars]):
            log.error(f'Recording folder name contains illegal characters {illegal_chars}')
            return

        log.info(f'Set recording folder to {folder_name}')
        vxipc.CONTROL[CTRL_REC_FLDNAME] = folder_name

    def start_recording(self):
        """Public method that can be called to request a recording to be started"""
        log.debug('Controller was requested to start new recording')
        vxipc.set_state(STATE.REC_START_REQ)

    def stop_recording(self):
        log.debug('Controller was requested to stop recording')
        vxipc.set_state(STATE.REC_STOP_REQ)

    def start_protocol(self, protocol_path: str):

        if not vxipc.in_state(STATE.IDLE):
            log.error('Protocol request failed. Controller is busy.')
            return

        # Reset everything to defaults
        self._reset_protocol_controls()

        log.debug(f'Protocol start requested for importpath {protocol_path}')
        vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = protocol_path

        # Set state to PRCL_START_REQ
        vxipc.set_state(STATE.PRCL_START_REQ)

    def _start_protocol(self):
        protocol = vxprotocol.get_protocol(self.protocol_import_path)

        # Abort protocol start if protocol cannot be imported
        if protocol is None:
            log.error(f'Failed to import protocol from import path {self.protocol_import_path}')
            self._reset_protocol_controls()
            vxipc.set_state(STATE.IDLE)
            return

        # Figure out protocol type
        if issubclass(protocol, vxprotocol.StaticProtocol):
            prcl_type = vxprotocol.StaticProtocol
        elif issubclass(protocol, vxprotocol.TriggeredProtocol):
            prcl_type = vxprotocol.TriggeredProtocol
        elif issubclass(protocol, vxprotocol.ContinuousProtocol):
            prcl_type = vxprotocol.ContinuousProtocol
        else:
            log.error(f'Failed to start protocol from import path {self.protocol_import_path}. '
                      f'Unknown type for protocol {protocol}')

            # Reset controls to defaults
            self._reset_protocol_controls()

            # We're done for now, go back to idle
            vxipc.set_state(STATE.IDLE)
            return

        # Increment record_protocol_group_id by 1
        self.record_protocol_group_id = self.record_protocol_group_id + 1

        # Set protocol type for all to see
        vxipc.CONTROL[CTRL_PRCL_TYPE] = prcl_type

        # Instantiate protocol
        self.current_protocol = protocol()

        # Do protocol type specific initializations
        prcl_type = vxipc.CONTROL[CTRL_PRCL_TYPE]
        if prcl_type == vxprotocol.StaticProtocol:
            pass

        elif prcl_type == vxprotocol.TriggeredProtocol:
            print('Setup trigger protocol')
            # Connect the _advance_phase method to the provided trigger and activate trigger
            self.current_protocol.phase_trigger.add_callback(self._trigger_protocol_advance_phase)

        elif prcl_type == vxprotocol.ContinuousProtocol:
            pass

        # Set state to PRCL_START
        log.info(f'Start {prcl_type.__name__} from import path {self.protocol_import_path}')

        # Go to PRCL_START state, to indicate to forks that a protocol has been set and should be prepared
        vxipc.set_state(STATE.PRCL_START)

    # Protocol stop

    def stop_protocol(self):

        if not vxipc.in_state(STATE.PRCL_IN_PROGRESS):
            return

        vxipc.set_state(STATE.PRCL_STOP_REQ)

    def _process_static_protocol(self):

        # If phase end time is below current time
        #  - either protocol just started (end time = -inf)
        #  - or the current phase just ended
        if self.phase_end_time < vxipc.get_time():

            # If any fork is still in an active phase, wait a turn
            if not self._all_protocol_forks_in_state(STATE.PRCL_STC_WAIT_FOR_PHASE):
                return

            # When all forks are done with the last phase (or if this is the first phase)

            # Check if previous phase was the last one in protocol,
            #  if so, request stop of protocol
            if self.phase_id >= (self.current_protocol.phase_count - 1):
                vxipc.set_state(STATE.PRCL_STOP_REQ)
                return

            # Increment phase ID by 1 and set new phase start/end time both to inf
            self.phase_id = self.phase_id + 1
            self.phase_start_time = np.inf
            self.phase_end_time = np.inf

            # Increment record_phase_group_id counter
            self.record_phase_group_id = self.record_phase_group_id + 1
            log.debug(f'Start record group {self.record_phase_group_id}')

            # Add debug info
            log.debug(f'Prepare phase {self.phase_id}')

        # If phase start equals end time, this should only happen for inf == inf (i.e. between phases)
        elif self.phase_start_time == self.phase_end_time:

            # If any fork is still in an active phase, wait a turn
            if not self._all_protocol_forks_in_state(STATE.PRCL_STC_PHASE_READY):
                return

            # TODO: the delay of start_time should be based on the slowest (protocolized) fork
            start_time = vxipc.get_time() + 0.020
            duration = self.current_protocol.current_phase.duration
            end_time = start_time + duration

            # Set for all
            self.phase_start_time = start_time
            self.phase_end_time = end_time
            log.info(f'Set phase {self.phase_id} to interval to [{start_time:.3f}, {end_time:.3f})')

        # If current time is between start and end time, a phase is currently running
        elif self.phase_start_time <= vxipc.get_time() < self.phase_end_time:
            pass

    def _process_trigger_protocol(self):
        pass

    def _trigger_protocol_advance_phase(self, index, time, state):

        # If the minimum phase_end_time is in the future, then disregard this trigger
        if self.phase_end_time > vxipc.get_time():
            return

        # Check if previous phase was the last one in protocol,
        #  if so, request stop of protocol
        if self.phase_id >= (self.current_protocol.phase_count - 1):
            vxipc.set_state(STATE.PRCL_STOP_REQ)
            return

        # Continue if there are more phases in protocol
        self.phase_id = self.phase_id + 1
        phase = self.current_protocol.get_phase(self.phase_id)
        log.info(f'Move to triggered phase {self.phase_id} at {time}')
        self.phase_start_time = time
        self.phase_end_time = time + phase.duration

        self.record_phase_group_id = self.record_phase_group_id + 1
        log.debug(f'Start record group {self.record_phase_group_id}')

    def main(self):
        pass

    def _eval_process_state(self):

        # First, handle log
        self._handle_logging()

        # If in state IDLE, just do that
        if vxipc.in_state(STATE.IDLE):
            self.idle()

        # Controller received request to start a recording
        elif vxipc.in_state(STATE.REC_START_REQ):

            # Only start recording if all forks are in idle
            if not self._all_forks_in_state(STATE.IDLE):
                return

            # If folder name hasn't been set yet, use default format
            if vxipc.CONTROL[CTRL_REC_FLDNAME] == '':
                vxipc.CONTROL[CTRL_REC_FLDNAME] = f'{time.strftime("%Y-%m-%d-%H-%M-%S")}'

            # Check recording path
            path = vxipc.get_recording_path()
            if os.path.exists(path):
                log.error(f'Unable to start new recording to path {path}. Path already exists')

                # Reset folder name
                self._reset_recording_controls()

                return

            # Create output folder
            log.debug(f'Create folder on path {path}')
            os.mkdir(path)

            # Set state to REC_START
            log.info(f'Controller starts recording to {path}')
            vxipc.set_state(STATE.REC_START)

        # Controller started recording REC_START
        # Waiting until all forks have gone to REC_STARTED
        # Then return to IDLE
        elif vxipc.in_state(STATE.REC_START):

            if not self._all_forks_in_state(STATE.REC_STARTED):
                return

            log.debug('All forks confirmed start of recording. Set recording to active.')
            vxipc.CONTROL[CTRL_REC_ACTIVE] = True

            # If all forks have signalled REC_STARTED, return to idle
            vxipc.set_state(STATE.IDLE)

        # Controller received request to stop recording REC_STOP_REQ
        # Evaluate and go to REC_STOP
        elif vxipc.in_state(STATE.REC_STOP_REQ):
            log.info(f'Stop recording to {vxipc.get_recording_path()}')
            vxipc.set_state(STATE.REC_STOP)

        # Controller stopped recording REC_STOP
        # Waiting until all forks have gone to REC_STOPPED
        # Then return to IDLE
        elif vxipc.in_state(STATE.REC_STOP):

            # Only stop recording if all forks are in REC_STOPPED
            if not self._all_forks_in_state(STATE.REC_STOPPED):
                return

            log.debug('All forks confirmed stop of recording. Set recording to inactive.')

            # Reset controls once everyone is done
            self._reset_recording_controls()

            # If all forks have signalled REC_STOPPED, return to IDLE
            vxipc.set_state(STATE.IDLE)

        # Controller received request to start a protocol
        # Evaluate and go to PRCL_START
        elif vxipc.in_state(STATE.PRCL_START_REQ):
            self._start_protocol()

        # Controller started protocol
        # Waiting until all forks have gone to PRCL_STARTED
        # Then go to PRCL_IN_PROGRESS
        elif vxipc.in_state(STATE.PRCL_START):

            # Only start protocol if all forks are in PRCL_STARTED
            if not self._all_protocol_forks_in_state(STATE.PRCL_STARTED):
                return

            # Set protocol to active
            vxipc.CONTROL[CTRL_PRCL_ACTIVE] = True

            if self.protocol_type == vxprotocol.StaticProtocol:
                pass
            elif self.protocol_type == vxprotocol.TriggeredProtocol:
                self.current_protocol.phase_trigger.set_active(True)
            elif self.protocol_type == vxprotocol.ContinuousProtocol:
                pass

            # Advance to PRCL_IN_PROGRESS
            vxipc.set_state(STATE.PRCL_IN_PROGRESS)

        # Controller has activated protocol
        # While in PRCL_IN_PROGESS, choose appropriate method to process based on protocol type
        elif vxipc.in_state(STATE.PRCL_IN_PROGRESS):
            prcl_type = vxipc.CONTROL[CTRL_PRCL_TYPE]
            if prcl_type == vxprotocol.StaticProtocol:
                self._process_static_protocol()
            elif prcl_type == vxprotocol.TriggeredProtocol:
                self._process_trigger_protocol()
            elif prcl_type == vxprotocol.ContinuousProtocol:
                pass

        # Controller received request to stop running protocol
        # Evaluate request and go to PRCL_STOP
        elif vxipc.in_state(STATE.PRCL_STOP_REQ):

            log.info(f'Stop protocol {self.protocol_import_path}')
            vxipc.set_state(STATE.PRCL_STOP)

        # Controller stopped protocol
        # Waiting until all forks have gone to PRCL_STOPPED
        # Then return to IDLE
        elif vxipc.in_state(STATE.PRCL_STOP):

            # Only return to idle if all forks are in PRCL_STOPPED
            if not self._all_protocol_forks_in_state(STATE.PRCL_STOPPED):
                return

            log.debug(f'Clean up protocol')

            # Reset everything to defaults
            self._reset_protocol_controls()

            # Set back to idle
            vxipc.set_state(STATE.IDLE)

    def commence_shutdown(self):
        log.debug('Shutdown requested. Checking.')

        # Check if any processes are still busy
        shutdown_state = True
        for p, _ in self._registered_processes:
            shutdown_state &= vxipc.in_state(STATE.IDLE, p.name) or vxipc.in_state(STATE.NA, p.name)

        # Check if recording or protocol is running
        shutdown_state &= not (vxipc.CONTROL[CTRL_REC_ACTIVE] or vxipc.CONTROL[CTRL_PRCL_ACTIVE])

        # If anything indicates that program is not ready for shutdown, ask for user confirmation
        if not shutdown_state:
            log.debug('Not ready for shutdown. Confirming.')
            vxipc.rpc(vxmodules.Gui.name, vxmodules.Gui.prompt_shutdown_confirmation)
            return

        # Otherwise, shut down
        self._force_shutdown()

    def _force_shutdown(self):
        log.debug('Shut down processes')
        self._shutdown = True
        vxipc.set_state(STATE.SHUTDOWN)
        # for process_name in self._processes:
        #     ipc.send(process_name, definitions.Signal.shutdown)

    @staticmethod
    def _render_splashscreen(pngpath: str) -> None:
        # Render SVG to PNG (qt's svg renderer has issues with blurred elements)
        iconpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.svg')
        renderer = QtSvg.QSvgRenderer(iconpath)
        image = QtGui.QImage(256, 256, QtGui.QImage.Format.Format_RGBA64)
        painter = QtGui.QPainter(image)
        image.fill(QtGui.QColor(0, 0, 0, 0))
        renderer.render(painter)
        image.save(pngpath)
        painter.end()
