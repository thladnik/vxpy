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
import vxpy.core.ipc as vxipc
import vxpy.core.protocol as vxprotocol
from vxpy.core.dependency import register_camera_device, register_io_device, assert_device_requirements
from vxpy.core import process, ipc, logger
from vxpy.core import routine
from vxpy.core import run_process
from vxpy.core.attribute import Attribute

log = logger.getLogger(__name__)


class Controller(process.AbstractProcess):
    name = PROCESS_CONTROLLER

    configfile: str = None

    _processes: Dict[str, mp.Process] = dict()
    _registered_processes: List[Tuple[process.AbstractProcess, Dict]] = list()

    _active_protocols: List[str] = list()

    def __init__(self, _configuration_path):
        # Set up manager
        ipc.Manager = mp.Manager()

        # Set up logging
        logger.setup_log_queue(ipc.Manager.Queue())
        logger.setup_log_history(ipc.Manager.list())
        logger.setup_log_to_file(f'{time.strftime("%Y-%m-%d-%H-%M-%S")}.log')

        # Manually set up pipe for controller
        ipc.Pipes[self.name] = mp.Pipe()

        # Set up STATES
        ipc.State.Controller = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)
        ipc.State.Camera = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)
        ipc.State.Display = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)
        ipc.State.Gui = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)
        ipc.State.Io = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)
        ipc.State.Worker = ipc.Manager.Value(ctypes.c_int8, definitions.State.NA)

        # Initialize process
        process.AbstractProcess.__init__(self, _program_start_time=time.time(), _configuration_path=_configuration_path)

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
        _routines_to_load = dict()
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
            self._register_process(vxmodules.Io)
            _routines_to_load[PROCESS_IO] = config.CONF_IO_ROUTINES
        # Worker
        if config.CONF_WORKER_USE:
            self._register_process(vxmodules.Worker)
            _routines_to_load[PROCESS_WORKER] = config.CONF_WORKER_ROUTINES

        # Select subset of registered processes which should implement
        # the _run_protocol method
        _active_process_list = [p[0].__name__ for p in self._registered_processes]
        self._active_protocols = list(set(_active_process_list) & set(self._protocolized))
        log.info(f'Protocolized processes: {self._active_protocols}')

        # TODO: check if recording routines contains any entries
        #  for inactive processes or inactive routines on active processes
        #  print warning or just shut down completely in-case?

        ################################
        # Set up CONTROLS

        # General
        ipc.Control.General = ipc.Manager.dict()
        # Set avg. minimum sleep period
        times = list()
        for i in range(100):
            t = time.perf_counter()
            time.sleep(10 ** -10)
            times.append(time.perf_counter() - t)
        ipc.Control.General.update({definitions.GenCtrl.min_sleep_time: max(times)})
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

        # Recording
        ipc.Control.Recording = ipc.Manager.dict()
        ipc.Control.Recording.update({
            RecCtrl.record_group_counter: -1,
            RecCtrl.enabled: True,
            RecCtrl.active: False,
            RecCtrl.folder: ''})

        # Protocol
        ipc.Control.Protocol = ipc.Manager.dict({ProtocolCtrl.name: None,
                                                 ProtocolCtrl.phase_id: None,
                                                 ProtocolCtrl.phase_start: None,
                                                 ProtocolCtrl.phase_stop: None})

        # NEW UNIFIED CONTROL:
        vxipc.CONTROL = ipc.Manager.dict(self._shared_controls())

        # Set configured cameras
        if config.CONF_CAMERA_USE:
            for device_id in config.CONF_CAMERA_DEVICES:
                register_camera_device(device_id)

        # Set configured io devices
        if config.CONF_IO_USE:
            for device_id in config.CONF_IO_DEVICES:
                register_io_device(device_id)

        # Load routine modules
        self._routines = dict()
        for process_name, routine_list in _routines_to_load.items():
            self._routines[process_name] = dict()
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
                self._routines[process_name][routine_cls.__name__]: routine.Routine = routine_cls()

        # Compare required vs registered devices
        assert_device_requirements()

        # Set up routines
        for rs in self._routines.values():
            for r in rs.values():
                r.require()
                r.setup()

        self._init_params = dict(
            _program_start_time=self.program_start_time,
            _configuration_path=_configuration_path,
            _pipes=ipc.Pipes,
            _states={k: v for k, v
                     in ipc.State.__dict__.items()
                     if not (k.startswith('_'))},
            # _proxies=_proxies,
            _routines=self._routines,
            _controls={k: v for k, v
                       in ipc.Control.__dict__.items()
                       if not (k.startswith('_'))},
            _control=vxipc.CONTROL,
            _log_queue=logger._log_queue,
            _log_history=logger.get_history(),
            _attrs=Attribute.all
        )

        # Initialize all processes
        for target, kwargs in self._registered_processes:
            self.initialize_process(target, **kwargs)

        # Set up initial recording states
        self.set_compression_method(None)
        self.set_compression_opts(None)
        self.record_group_counter = -1

    @staticmethod
    def _shared_controls():
        _controls = {CTRL_REC_ACTIVE: False,
                     CTRL_REC_BASE_PATH: os.path.join(os.getcwd(), PATH_RECORDING_OUTPUT),
                     CTRL_REC_FLDNAME: '',
                     CTRL_REC_GROUP_ID: -1,
                     CTRL_PRCL_ACTIVE: False,
                     CTRL_PRCL_IMPORTPATH: '',
                     CTRL_PRCL_TYPE: None,
                     CTRL_PRCL_PHASE_ID: -1,
                     CTRL_PRCL_PHASE_START_TIME: np.inf,
                     CTRL_PRCL_PHASE_END_TIME: -np.inf}

        return _controls

    def _register_process(self, target, **kwargs):
        """Register new modules to be spawned.

        :param target: modules class
        :param kwargs: optional keyword arguments for initalization of modules class
        """
        self._registered_processes.append((target, kwargs))
        ipc.Pipes[target.name] = mp.Pipe()

    def initialize_process(self, target, **kwargs):

        process_name = target.name

        if process_name in self._processes:
            # Terminate modules
            log.info(f'Restart modules {process_name}')
            self._processes[process_name].terminate()

            # Set modules state
            # (this is the ONLY instance where a modules state may be set externally)
            getattr(ipc.State, process_name).value = definitions.State.STOPPED

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

        if sys.platform == 'win32':
            self.splashscreen.close()
            self.qt_app.processEvents()

        # Run controller
        self.run(interval=0.001)

        # Shutdown procedure
        log.debug('Wait for processes to terminate')
        while True:
            # Complete shutdown if all processes are deleted
            if not (bool(self._processes)):
                break

            # Check status of processes until last one is stopped
            for process_name in list(self._processes):
                if not (getattr(ipc.State, process_name).value == definitions.State.STOPPED):
                    continue

                # Terminate and delete references
                self._processes[process_name].terminate()
                del self._processes[process_name]
                del ipc.Pipes[process_name]

        self._running = False
        self.set_state(definitions.State.STOPPED)

        return 0

    @staticmethod
    def set_compression_method(method):
        ipc.Control.Recording[RecCtrl.compression_method] = method
        if method is None:
            ipc.Control.Recording[RecCtrl.compression_opts] = None
        log.info(f'Set compression method to {method}')

    @staticmethod
    def set_compression_opts(opts):
        if ipc.Control.Recording[RecCtrl.compression_method] is None:
            ipc.Control.Recording[RecCtrl.compression_opts] = None
            return
        ipc.Control.Recording[RecCtrl.compression_opts] = opts
        log.info(f'Set compression options to {opts}')

    def run_protocol_old(self, protocol_path):
        if not vxipc.in_state(STATE.IDLE):
            log.error(f'Unable to start protocol {protocol_path}. Controller not ready.')
            return

        # Set phase info
        ipc.Control.Protocol[ProtocolCtrl.phase_id] = None
        ipc.Control.Protocol[ProtocolCtrl.phase_start] = None
        ipc.Control.Protocol[ProtocolCtrl.phase_stop] = None
        # Set protocol class path
        ipc.Control.Protocol[ProtocolCtrl.name] = protocol_path

        # Go into PREPARE_PROTOCOL
        self.set_state(State.PREPARE_PROTOCOL)

    def end_protocol_phase(self):
        if not self.in_state(State.RUNNING):
            return

        if ipc.Control.Protocol[ProtocolCtrl.phase_stop] is None:
            ipc.Control.Protocol[ProtocolCtrl.phase_stop] = time.time()

        # Set record group
        ipc.Control.Recording[RecCtrl.record_group_counter] = -1

        log.info(f'End phase {ipc.Control.Protocol[ProtocolCtrl.phase_id]}')
        self.set_state(State.PHASE_END)

    def _start_protocol_phase(self):
        # Set phase_id within protocol
        phase_id = ipc.Control.Protocol[ProtocolCtrl.phase_id]
        if phase_id is None:
            phase_id = 0
        else:
            phase_id += 1
        ipc.Control.Protocol[ProtocolCtrl.phase_id] = phase_id

        # Add to record group counter
        self.record_group_counter += 1
        ipc.Control.Recording[RecCtrl.record_group_counter] = self.record_group_counter

    @staticmethod
    def _handle_logging():
        while not logger.get_queue().empty():

            # Fetch next record
            record = logger.get_queue().get()

            try:
                logger.add_to_file(record)
                logger.add_to_history(record)
            except Exception as exc:
                import sys, traceback
                print('Exception in Logger:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def _all_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_protocols]

        return all(check)

    def _any_forks_in_state(self, code: Union[State, STATE]):

        check = [vxipc.in_state(code, pname) for pname in self._active_protocols]

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
        log.info(f'Set recording folder to {folder_name}')
        vxipc.CONTROL[CTRL_REC_FLDNAME] = folder_name

    def start_recording(self):
        print('Controller was requested to start new recording')
        vxipc.set_state(STATE.REC_START_REQ)

    def stop_recording(self):
        print('Controller was requested to stop recording')
        vxipc.set_state(STATE.REC_STOP_REQ)

    def _start_recording(self):

        # Only start recording if all forks are in idle
        if not self._all_forks_in_state(STATE.IDLE):
            return

        # If foldername hasn't been set yet, use default format
        if vxipc.CONTROL[CTRL_REC_FLDNAME] == '':
            vxipc.CONTROL[CTRL_REC_FLDNAME] = f'{time.strftime("%Y-%m-%d-%H-%M-%S")}'
            
        # Check recording path
        path = vxipc.get_recording_path()
        if os.path.exists(path):
            log.error(f'Unable to start new recording to path {path}. '
                      f'Path already exists')

            # Reset folder name
            vxipc.CONTROL[CTRL_REC_FLDNAME] = ''

            return

        # Create output folder
        log.debug(f'Create folder on path {path}')
        os.mkdir(path)

        # Set state to REC_START
        log.info(f'Controller starts recording to {path}')
        vxipc.set_state(STATE.REC_START)

    def _started_recording(self):

        if not self._all_forks_in_state(STATE.REC_STARTED):
            return

        log.debug('All forks confirmed start of recording. Set recording to active.')
        vxipc.CONTROL[CTRL_REC_ACTIVE] = True

        # If all forks have signalled REC_STARTED, return to idle
        vxipc.set_state(STATE.IDLE)

    def _stop_recording(self):
        # DO RECORDING STARTING STUFF
        log.info(f'Stop recording to {vxipc.get_recording_path()}')
        vxipc.set_state(STATE.REC_STOP)

    def _stopped_recording(self):

        # Only stop recording if all forks are in REC_STOPPED
        if not self._all_forks_in_state(STATE.REC_STOPPED):
            return

        log.debug('All forks confirmed stop of recording. Set recording to inactive.')
        vxipc.CONTROL[CTRL_REC_ACTIVE] = False
        vxipc.CONTROL[CTRL_REC_FLDNAME] = ''

        # If all forks have signalled REC_STOPPED, return to IDLE
        vxipc.set_state(STATE.IDLE)

    def start_protocol(self, protocol_path: str):

        if not vxipc.in_state(STATE.IDLE):
            log.error('Protocol request failed. Controller is busy.')
            return

        # Reset everything to defaults
        self._reset_protocol_ctrls()

        log.debug(f'Protocol start requested for importpath {protocol_path}')
        vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = protocol_path

        # Set state to PRCL_START_REQ
        vxipc.set_state(STATE.PRCL_START_REQ)

    def stop_protocol(self):

        if not vxipc.in_state(STATE.PRCL_IN_PROGRESS):
            return

        vxipc.set_state(STATE.PRCL_STOP_REQ)

    @staticmethod
    def _reset_protocol_ctrls():
        vxipc.CONTROL[CTRL_PRCL_ACTIVE] = False
        vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = ''
        vxipc.CONTROL[CTRL_PRCL_TYPE] = None
        vxipc.CONTROL[CTRL_PRCL_PHASE_ID] = -1
        vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME] = np.inf
        vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME] = -np.inf

    def _start_protocol(self):
        protocol = vxprotocol.get_protocol(vxipc.CONTROL[CTRL_PRCL_IMPORTPATH])

        # Abort protocol start if protocol cannot be imported
        if protocol is None:
            log.error(f'Failed to import protocol from importpath {vxipc.CONTROL[CTRL_PRCL_IMPORTPATH]}')
            vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = ''
            vxipc.set_state(STATE.IDLE)
            return

        if issubclass(protocol, vxprotocol.StaticPhasicProtocol):
            prcl_type = vxprotocol.StaticPhasicProtocol
        elif issubclass(protocol, vxprotocol.ContinuousProtocol):
            prcl_type = vxprotocol.ContinuousProtocol
        elif issubclass(protocol, vxprotocol.TriggeredProtocol):
            prcl_type = vxprotocol.TriggeredProtocol
        else:
            log.error(f'Failed to start protocol from importpath {vxipc.CONTROL[CTRL_PRCL_IMPORTPATH]}. '
                      f'Unknown type for protocol {protocol}')
            vxipc.CONTROL[CTRL_PRCL_IMPORTPATH] = ''
            vxipc.set_state(STATE.IDLE)
            return

        vxipc.CONTROL[CTRL_PRCL_TYPE] = prcl_type

        self.current_protocol = protocol()

        log.info(f'Start {prcl_type.__name__} from importpath {self.current_protocol.__class__.__qualname__}')
        # Set state to PRCL_START
        vxipc.set_state(STATE.PRCL_START)

    def _started_protocol(self):

        # Only start protocol if all forks are in PRCL_STARTED
        if not self._all_forks_in_state(STATE.PRCL_STARTED):
            return

        vxipc.CONTROL[CTRL_PRCL_ACTIVE] = True
        vxipc.set_state(STATE.PRCL_IN_PROGRESS)

    def _stop_protocol(self):
        vxipc.set_state(STATE.PRCL_STOP)

    def _stopped_protocol(self):

        # Only return to idle if all forks are in PRCL_STOPPED
        if not self._all_forks_in_state(STATE.PRCL_STOPPED):
            return

        # Reset everything to defaults
        self._reset_protocol_ctrls()

        # Set back to idle
        vxipc.set_state(STATE.IDLE)

    def _process_static_phasic_protocol(self):

        t = vxipc.get_time()
        phase_end_time = vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME]
        phase_start_time = vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME]

        # If phase end time is below current time
        #  - either protocol just started (end time = -inf)
        #  - or the current phase just ended
        if phase_end_time < t:
            # Increment phase ID by 1 and set new phase end time to inf
            vxipc.CONTROL[CTRL_PRCL_PHASE_ID] += 1
            vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME] = np.inf

        # If phase end time and start times are in the future,
        # check if new start and end time need to be updated to run the next phase
        elif phase_start_time > t and phase_end_time > t:

            # If phase start equals end time, this should only happen for inf == inf (i.e. between phases)
            if phase_start_time == phase_end_time:
                new_start = vxipc.get_time() + 0.1

                log.info(f'Set new new phase start to {new_start}')

                vxipc.CONTROL[CTRL_PRCL_PHASE_START_TIME] = new_start
                vxipc.CONTROL[CTRL_PRCL_PHASE_END_TIME] = new_start + self.current_protocol.current_phase.duration

        # If current time is between start and end time, a phase is currently running
        elif phase_start_time <= t < phase_end_time:
            pass


    def main(self):
        pass

    def _eval_state(self):

        # First, handle log
        self._handle_logging()

        # If in state IDLE, just do that
        if vxipc.in_state(STATE.IDLE):
            self.idle()

        # Controller received request to start a recording
        elif vxipc.in_state(STATE.REC_START_REQ):
            self._start_recording()

        # Controller started recording REC_START
        # Waiting until all forks have gone to REC_STARTED
        # Then return to IDLE
        elif vxipc.in_state(STATE.REC_START):
            self._started_recording()

        # Controller received request to stop recording REC_STOP_REQ
        # Evaluate and go to REC_STOP
        elif vxipc.in_state(STATE.REC_STOP_REQ):
            self._stop_recording()

        # Controller stopped recording REC_STOP
        # Waiting until all forks have gone to REC_STOPPED
        # Then return to IDLE
        elif vxipc.in_state(STATE.REC_STOP):
            self._stopped_recording()

        # Controller received request to start a protocol
        # Evaluate and go to PRCL_START
        elif vxipc.in_state(STATE.PRCL_START_REQ):
            self._start_protocol()

        # Controller started protocol
        # Waiting until all forks have gone to PRCL_STARTED
        # Then go to PRCL_IN_PROGRESS
        elif vxipc.in_state(STATE.PRCL_START):
            self._started_protocol()

        # Controller has activated protocol
        # While in PRCL_IN_PROGESS, choose appropriate method to process based on protocol type
        elif vxipc.in_state(STATE.PRCL_IN_PROGRESS):
            prcl_type = vxipc.CONTROL[CTRL_PRCL_TYPE]
            if prcl_type == vxprotocol.StaticPhasicProtocol:
                self._process_static_phasic_protocol()
            elif prcl_type == vxprotocol.ContinuousProtocol:
                pass
            elif prcl_type == vxprotocol.TriggeredProtocol:
                pass

        # Controller received request to stop running protocol
        # Evaluate and go to PRCL_STOP
        elif vxipc.in_state(STATE.PRCL_STOP_REQ):
            self._stop_protocol()

        # Controller stopped protocol
        # Waiting until all forks have gone to PRCL_STOPPED
        # Then return to IDLE
        elif vxipc.in_state(STATE.PRCL_STOP):
            self._stopped_protocol()

    # def main_old(self):
    #
    #     ########
    #     # First: handle log
    #     while not logger.get_queue().empty():
    #
    #         # Fetch next record
    #         record = logger.get_queue().get()
    #
    #         try:
    #             logger.add_to_file(record)
    #             logger.add_to_history(record)
    #         except Exception:
    #             import sys, traceback
    #             print('Exception in Logger:', file=sys.stderr)
    #             traceback.print_exc(file=sys.stderr)
    #
    #     ########
    #     # PREPARE_PROTOCOL
    #     if self.in_state(definitions.State.PREPARE_PROTOCOL):
    #
    #         protocol_path = ipc.Control.Protocol[ProtocolCtrl.name]
    #         _protocol = get_protocol(protocol_path)
    #         if _protocol is None:
    #             log.error(f'Cannot get protocol {protocol_path}. Aborting ')
    #             self.set_state(definitions.State.PROTOCOL_ABORT)
    #             return
    #
    #         self.protocol = _protocol()
    #
    #         # Wait for processes to WAIT_FOR_PHASE (if they are not stopped)
    #         check = [not (ipc.in_state(definitions.State.WAIT_FOR_PHASE, process_name))
    #                  for process_name in self._active_protocols]
    #         if any(check):
    #             return
    #
    #         # Set next phase
    #         self._start_protocol_phase()
    #
    #         # Set PREPARE_PHASE
    #         self.set_state(definitions.State.PREPARE_PHASE)
    #
    #     ########
    #     # PREPARE_PHASE
    #     if self.in_state(definitions.State.PREPARE_PHASE):
    #
    #         # Wait for processes to be ready (have phase prepared)
    #         check = [not ipc.in_state(definitions.State.READY, process_name)
    #                  for process_name in self._active_protocols]
    #         if any(check):
    #             return
    #
    #         # Start phase
    #         phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]
    #         duration = self.protocol.fetch_phase_duration(phase_id)
    #
    #         # Set phase times
    #         now = time.time()
    #         fixed_delay = 0.01
    #         phase_start = now + fixed_delay
    #         ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = phase_start
    #         phase_stop = now + duration + fixed_delay if duration is not None else None
    #         ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = phase_stop
    #
    #         log.info(f'Run protocol phase {phase_id} at {(phase_start-self.program_start_time):.4f}')
    #
    #         # Set to running
    #         self.set_state(definitions.State.RUNNING)
    #
    #     ########
    #     # RUNNING
    #     elif self.in_state(definitions.State.RUNNING):
    #
    #         # If stop time is reached, set PHASE_END
    #         phase_stop = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop]
    #         if phase_stop is not None and phase_stop < time.time():
    #             self.end_protocol_phase()
    #             return
    #
    #     ########
    #     # PHASE_END
    #     elif self.in_state(definitions.State.PHASE_END):
    #
    #         # Reset phase start time
    #         ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = None
    #
    #         # If there are no further phases, end protocol
    #         phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]
    #         if (phase_id + 1) >= self.protocol.phase_count:
    #             self.set_state(definitions.State.PROTOCOL_END)
    #             return
    #
    #         # Else, continue with next phase
    #         self._start_protocol_phase()
    #
    #         # Move to PREPARE_PHASE (again)
    #         self.set_state(definitions.State.PREPARE_PHASE)
    #
    #     ########
    #     # PROTOCOL_END
    #     elif self.in_state(definitions.State.PROTOCOL_END):
    #
    #         # When all processes are in IDLE again, stop recording and
    #         # move Controller to IDLE
    #         check = [ipc.in_state(definitions.State.IDLE, process_name)
    #                  for process_name in self._active_protocols]
    #         if all(check):
    #             self.stop_recording()
    #
    #             ipc.Control.Protocol[definitions.ProtocolCtrl.name] = None
    #             ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id] = None
    #             ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = None
    #             ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = None
    #
    #             self.set_state(definitions.State.IDLE)
    #
    #     else:
    #         # If nothing's happning: sleep for a bit
    #         pass
    #         # time.sleep(0.05)

    def _start_shutdown(self):
        log.debug('Shutdown requested. Checking.')

        # Check if any processes are still busy
        shutdown_state = True
        for p, _ in self._registered_processes:
            shutdown_state &= self.in_state(definitions.State.IDLE, p.name) or self.in_state(definitions.State.NA, p.name)

        # Check if recording is running
        shutdown_state &= not (ipc.Control.Recording[definitions.RecCtrl.active])

        if not shutdown_state:
            log.debug('Not ready for shutdown. Confirming.')
            ipc.rpc(vxmodules.Gui.name, vxmodules.Gui.prompt_shutdown_confirmation)
            return

        self._force_shutdown()

    def _force_shutdown(self):
        log.debug('Shut down processes')
        self._shutdown = True
        for process_name in self._processes:
            ipc.send(process_name, definitions.Signal.shutdown)

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
