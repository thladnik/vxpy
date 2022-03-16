"""
MappApp ./modules/controller.py
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
import ctypes
import importlib
import multiprocessing as mp
from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
import time
from typing import List, Tuple

import vxpy
from vxpy import config
from vxpy import definitions
from vxpy.definitions import *
from vxpy import modules
from vxpy.api import gui_rpc
from vxpy.api.dependency import register_camera_device, register_io_device, assert_device_requirements
from vxpy.core import process, ipc, logger
from vxpy.core import routine
from vxpy.core import run_process
import vxpy.core.gui as vxgui
from vxpy.core.attribute import Attribute
from vxpy.core.protocol import get_protocol

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

        # Set up modules proxies (TODO: get rid of IPC.State)
        _proxies = {
            PROCESS_CONTROLLER: process.ProcessProxy(PROCESS_CONTROLLER),
            PROCESS_CAMERA: process.ProcessProxy(PROCESS_CAMERA),
            PROCESS_DISPLAY: process.ProcessProxy(PROCESS_DISPLAY),
            PROCESS_GUI: process.ProcessProxy(PROCESS_GUI),
            PROCESS_IO: process.ProcessProxy(PROCESS_IO),
        }

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
        # self.qt_app = QtWidgets.QApplication([])
        # pngpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.png')

        # Render SVG to PNG (qt's svg renderer has issues with blurred elements)
        # iconpath = os.path.join(str(vxpy.__path__[0]), 'vxpy_icon.svg')
        # renderer = QtSvg.QSvgRenderer(iconpath)
        # image = QtGui.QImage(512, 512, QtGui.QImage.Format.Format_RGBA64)
        # painter = QtGui.QPainter(image)
        # image.fill(QtGui.QColor(0, 0, 0, 0))
        # renderer.render(painter)
        # image.save(pngpath)
        # painter.end()

        # Show screen
        # TODO: Splashscreen blocks display of GUI under linux
        # self.splashscreen = QtWidgets.QSplashScreen(f=QtCore.Qt.WindowStaysOnTopHint, screen=self.qt_app.screens()[config.CONF_GUI_SCREEN])
        # self.splashscreen.setPixmap(QtGui.QPixmap(pngpath))
        # # splash.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.splashscreen.show()
        #
        # # Process events once
        # self.qt_app.processEvents()

        # Set up processes
        _routines_to_load = dict()
        # Camera
        if config.CONF_CAMERA_USE:
            self._register_process(modules.Camera)
            _routines_to_load[PROCESS_CAMERA] = config.CONF_CAMERA_ROUTINES
        # Display
        if config.CONF_DISPLAY_USE:
            self._register_process(modules.Display)
            _routines_to_load[PROCESS_DISPLAY] = config.CONF_DISPLAY_ROUTINES
        # GUI
        if config.CONF_GUI_USE:
            self._register_process(modules.Gui)
        # IO
        if config.CONF_IO_USE:
            self._register_process(modules.Io)
            _routines_to_load[PROCESS_IO] = config.CONF_IO_ROUTINES
        # Worker
        if config.CONF_WORKER_USE:
            self._register_process(modules.Worker)
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
        msg = 'Timing precision on system {0:3f}ms'.format(1000 * avg_dt)
        if avg_dt > 0.001:
            log.warning(msg)
        else:
            log.info(msg)

        # Recording
        ipc.Control.Recording = ipc.Manager.dict()
        ipc.Control.Recording.update({
            definitions.RecCtrl.enabled: True,
            definitions.RecCtrl.active: False,
            definitions.RecCtrl.folder: ''})

        # Protocol
        ipc.Control.Protocol = ipc.Manager.dict({definitions.ProtocolCtrl.name: None,
                                                 definitions.ProtocolCtrl.phase_id: None,
                                                 definitions.ProtocolCtrl.phase_start: None,
                                                 definitions.ProtocolCtrl.phase_stop: None})

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
                    log.error(f'Routine "{path}" not found.')
                    continue

                # Instantiate
                self._routines[process_name][routine_cls.__name__]: routine.Routine = routine_cls()

        # Set configured cameras
        if config.CONF_CAMERA_USE:
            for device_id in config.CONF_CAMERA_DEVICES:
                register_camera_device(device_id)

        # Set configured io devices
        if config.CONF_IO_USE:
            for device_id in config.CONF_IO_DEVICES:
                register_io_device(device_id)

        # Compare required vs registered devices
        assert_device_requirements()

        # Set up routines
        for rs in self._routines.values():
            for r in rs.values():
                r.setup()

        self._init_params = dict(
            _program_start_time=self.program_start_time,
            _configuration_path=_configuration_path,
            _pipes=ipc.Pipes,
            _states={k: v for k, v
                     in ipc.State.__dict__.items()
                     if not (k.startswith('_'))},
            _proxies=_proxies,
            _routines=self._routines,
            _controls={k: v for k, v
                       in ipc.Control.__dict__.items()
                       if not (k.startswith('_'))},
            _log_queue=logger._log_queue,
            _log_history=logger.get_history(),
            _attrs=Attribute.all
        )

        # Initialize all processes
        for target, kwargs in self._registered_processes:
            self.initialize_process(target, **kwargs)

        # Set up initial recording states
        self.manual_recording = False
        self.set_compression_method(None)
        self.set_compression_opts(None)
        self.record_group_counter = 0

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
            log.info('Restart modules {}'.format(process_name))
            self._processes[process_name].terminate()

            # Set modules state
            # (this is the ONLY instance where a modules state may be set externally)
            getattr(ipc.State, process_name).value = definitions.State.STOPPED

            # Delete references
            del self._processes[process_name]

        # Update keyword args
        kwargs.update(self._init_params)

        # Create subprocess
        self._processes[process_name] = mp.Process(target=run_process, name=process_name, args=(target,), kwargs=kwargs)

        # Start subprocess
        self._processes[process_name].start()

        # Set state to IDLE
        self.set_state(definitions.State.IDLE)

    def start(self):

        # self.splashscreen.close()
        # self.qt_app.processEvents()

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

    ################
    # Recording

    def start_manual_recording(self):
        self.manual_recording = True
        self.start_recording()

    def stop_manual_recording(self):
        self.manual_recording = False
        self.stop_recording()

    @staticmethod
    def set_recording_folder(folder_name: str):
        # TODO: checks
        log.info(f'Set recording folder to {folder_name}')
        ipc.Control.Recording[RecCtrl.folder] = folder_name

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

    @staticmethod
    def set_enable_recording(newstate):
        ipc.Control.Recording[RecCtrl.enabled] = newstate

    def start_recording(self):
        if ipc.Control.Recording[RecCtrl.active]:
            log.warning('Tried to start new recording while active')
            return False

        if not ipc.Control.Recording[RecCtrl.enabled]:
            log.warning('Recording not enabled. Session will not be saved to disk.')
            return True

        # Set current folder if none is given
        if not bool(ipc.Control.Recording[RecCtrl.folder]):
            ipc.Control.Recording[RecCtrl.folder] = f'{time.strftime("%Y-%m-%d-%H-%M-%S")}'

            # Reset record group perf_counter
            self.record_group_counter = 0

        # Create output folder
        rec_folder_path = os.path.join(config.CONF_REC_OUTPUT_FOLDER, ipc.Control.Recording[RecCtrl.folder])
        log.debug('Set output folder {}'.format(rec_folder_path))
        if not os.path.exists(rec_folder_path):
            log.debug('Create output folder {}'.format(rec_folder_path))
            os.mkdir(rec_folder_path)

        # Set state to recording
        log.info('Start recording')
        ipc.Control.Recording[definitions.RecCtrl.active] = True

        gui_rpc(vxgui.RecordingWidget.show_lab_notebook)

        return True

    @staticmethod
    def pause_recording():
        if not ipc.Control.Recording[definitions.RecCtrl.active]:
            log.warning('Tried to pause inactive recording.')
            return

        log.info('Pause recording')
        ipc.Control.Recording[definitions.RecCtrl.active] = False

    def stop_recording(self, sessiondata=None):
        if self.manual_recording:
            return

        if ipc.Control.Recording[definitions.RecCtrl.active]:
            ipc.Control.Recording[definitions.RecCtrl.active] = False

        gui_rpc(vxgui.RecordingWidget.close_lab_notebook)

        log.info('Stop recording')
        self.set_state(definitions.State.IDLE)
        ipc.Control.Recording[definitions.RecCtrl.folder] = ''

    def start_protocol(self, protocol_path):
        # If any relevant subprocesses are currently busy: abort
        if not (self.in_state(definitions.State.IDLE, PROCESS_DISPLAY)):
            processes = list()
            if not (self.in_state(definitions.State.IDLE, PROCESS_DISPLAY)):
                processes.append(PROCESS_DISPLAY)
            if not (self.in_state(definitions.State.IDLE, PROCESS_IO)):
                processes.append(PROCESS_IO)

            log.warning(
                          'One or more processes currently busy. Can not start new protocol.'
                          '(Processes: {})'.format(','.join(processes)))
            return

        # Start recording if enabled; abort if recording can't be started
        if ipc.Control.Recording[definitions.RecCtrl.enabled] \
                and not (ipc.Control.Recording[definitions.RecCtrl.active]):
            if not (self.start_recording()):
                return

        # Set phase info
        ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id] = None
        ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = None
        ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = None
        # Set protocol class path
        ipc.Control.Protocol[definitions.ProtocolCtrl.name] = protocol_path

        # Go into PREPARE_PROTOCOL
        self.set_state(definitions.State.PREPARE_PROTOCOL)

    def end_protocol_phase(self):
        if not self.in_state(definitions.State.RUNNING):
            return

        if ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] is None:
            ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = time.time()

        log.info(f'End phase {ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]}.')
        self.set_state(definitions.State.PHASE_END)

    def start_protocol_phase(self):
        # Set phase_id within protocol
        phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]
        if phase_id is None:
            phase_id = 0
        else:
            phase_id += 1
        ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id] = phase_id

        # Add to record group counter
        self.record_group_counter += 1
        ipc.Control.Recording[definitions.RecCtrl.record_group_counter] = self.record_group_counter

    def abort_protocol(self):
        # TODO: handle stuff?
        ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = time.time()
        self.set_state(definitions.State.PROTOCOL_END)

    def main(self):

        ########
        # First: handle log
        while not (logger.get_queue().empty()):

            # Fetch next record
            record = logger.get_queue().get()

            try:
                logger.add_to_file(record)
                logger.add_to_history(record)
            except Exception:
                import sys, traceback
                print('Exception in Logger:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

        ########
        # PREPARE_PROTOCOL
        if self.in_state(definitions.State.PREPARE_PROTOCOL):

            protocol_path = ipc.Control.Protocol[definitions.ProtocolCtrl.name]
            _protocol = get_protocol(protocol_path)
            if _protocol is None:
                log.error(f'Cannot get protocol {protocol_path}. Aborting ')
                self.set_state(definitions.State.PROTOCOL_ABORT)
                return

            self.protocol = _protocol()

            # Wait for processes to WAIT_FOR_PHASE (if they are not stopped)
            check = [not (ipc.in_state(definitions.State.WAIT_FOR_PHASE, process_name))
                     for process_name in self._active_protocols]
            if any(check):
                return

            # Set next phase
            self.start_protocol_phase()

            # Set PREPARE_PHASE
            self.set_state(definitions.State.PREPARE_PHASE)

        ########
        # PREPARE_PHASE
        if self.in_state(definitions.State.PREPARE_PHASE):

            # Wait for processes to be ready (have phase prepared)
            check = [not (ipc.in_state(definitions.State.READY, process_name))
                     for process_name in self._active_protocols]
            if any(check):
                return

            # Start phase
            phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]
            duration = self.protocol.fetch_phase_duration(phase_id)

            # Set phase times
            now = time.time()
            fixed_delay = 0.01
            phase_start = now + fixed_delay
            ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = phase_start
            phase_stop = now + duration + fixed_delay if duration is not None else None
            ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = phase_stop

            log.info(f'Run protocol phase {phase_id} at {(phase_start-self.program_start_time):.4f}')

            # Set to running
            self.set_state(definitions.State.RUNNING)

        ########
        # RUNNING
        elif self.in_state(definitions.State.RUNNING):

            # If stop time is reached, set PHASE_END
            phase_stop = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop]
            if phase_stop is not None and phase_stop < time.time():
                self.end_protocol_phase()
                return

        ########
        # PHASE_END
        elif self.in_state(definitions.State.PHASE_END):

            # Reset phase start time
            ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = None

            # If there are no further phases, end protocol
            phase_id = ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id]
            if (phase_id + 1) >= self.protocol.phase_count:
                self.set_state(definitions.State.PROTOCOL_END)
                return

            # Else, continue with next phase
            self.start_protocol_phase()

            # Move to PREPARE_PHASE (again)
            self.set_state(definitions.State.PREPARE_PHASE)

        ########
        # PROTOCOL_END
        elif self.in_state(definitions.State.PROTOCOL_END):

            # When all processes are in IDLE again, stop recording and
            # move Controller to IDLE
            check = [ipc.in_state(definitions.State.IDLE, process_name)
                     for process_name in self._active_protocols]
            if all(check):
                self.stop_recording()

                ipc.Control.Protocol[definitions.ProtocolCtrl.name] = None
                ipc.Control.Protocol[definitions.ProtocolCtrl.phase_id] = None
                ipc.Control.Protocol[definitions.ProtocolCtrl.phase_start] = None
                ipc.Control.Protocol[definitions.ProtocolCtrl.phase_stop] = None

                self.set_state(definitions.State.IDLE)

        else:
            # If nothing's happning: sleep for a bit
            pass
            # time.sleep(0.05)

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
            ipc.rpc(modules.Gui.name, modules.Gui.prompt_shutdown_confirmation)
            return

        self._force_shutdown()

    def _force_shutdown(self):
        log.debug('Shut down processes')
        self._shutdown = True
        for process_name in self._processes:
            ipc.send(process_name, definitions.Signal.shutdown)
