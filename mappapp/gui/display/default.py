"""
MappApp ./gui/core.py - GUI addons meant to be integrated into the main window.
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
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtWidgets import QLabel
import time

from mappapp import process
from mappapp import protocols,IPC,Def
from mappapp.core.gui import AddonWidget


class Protocols(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())

        # File list
        self._lwdgt_files = QtWidgets.QListWidget()
        self._lwdgt_files.itemSelectionChanged.connect(self.update_file_list)
        self.layout().addWidget(QLabel('Files'), 0, 0)
        self.layout().addWidget(self._lwdgt_files, 1, 0)
        # Protocol list
        self.lwdgt_protocols = QtWidgets.QListWidget()
        #self._lwdgt_protocols.itemSelectionChanged.connect(self._updateProtocolInfo)
        self.layout().addWidget(QLabel('Protocols'), 0, 1)
        self.layout().addWidget(self.lwdgt_protocols, 1, 1)

        # Protocol (phase) progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setTextVisible(False)
        self.layout().addWidget(self.progress, 0, 2)

        # Start button
        self.wdgt_controls = QtWidgets.QWidget()
        self.layout().addWidget(self.wdgt_controls, 1, 2)
        self.wdgt_controls.setLayout(QtWidgets.QVBoxLayout())
        self.wdgt_controls.btn_start = QtWidgets.QPushButton('Start protocol')
        self.wdgt_controls.btn_start.clicked.connect(self.start_protocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_start)
        # Abort protocol button
        self.wdgt_controls.btn_abort = QtWidgets.QPushButton('Abort protocol')
        self.wdgt_controls.btn_abort.clicked.connect(self.abort_protocol)
        self.wdgt_controls.layout().addWidget(self.wdgt_controls.btn_abort)

        # Spacer
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.wdgt_controls.layout().addItem(vSpacer)

        # Set update timer
        self._tmr_update = QtCore.QTimer()
        self._tmr_update.setInterval(200)
        self._tmr_update.timeout.connect(self.update_ui)
        self._tmr_update.start()

        # Once set up: compile file list for first time
        self._compile_file_list()

    def _compile_file_list(self):
        self._lwdgt_files.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for file in protocols.all():
            self._lwdgt_files.addItem(file)

    def update_file_list(self):
        self.lwdgt_protocols.clear()
        self.wdgt_controls.btn_start.setEnabled(False)

        for protocol in protocols.read(protocols.open_(self._lwdgt_files.currentItem().text())):
            self.lwdgt_protocols.addItem(protocol.__name__)

    def update_ui(self):

        # Enable/Disable control elements
        ctrl_is_idle = IPC.in_state(Def.State.IDLE, Def.Process.Controller)
        self.wdgt_controls.btn_start.setEnabled(ctrl_is_idle and len(self.lwdgt_protocols.selectedItems()) > 0)
        self.lwdgt_protocols.setEnabled(ctrl_is_idle)
        self._lwdgt_files.setEnabled(ctrl_is_idle)
        protocol_is_running = bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])
        self.wdgt_controls.btn_abort.setEnabled(protocol_is_running)

        # Update progress
        start_phase = IPC.Control.Protocol[Def.ProtocolCtrl.phase_start]
        if not(start_phase is None):
            self.progress.setEnabled(True)
            phase_diff = time.time() - start_phase
            self.progress.setMaximum(int((IPC.Control.Protocol[Def.ProtocolCtrl.phase_stop] - start_phase) * 10))
            if phase_diff > 0.:
                self.progress.setValue(int(phase_diff * 10))

        if not(bool(IPC.Control.Protocol[Def.ProtocolCtrl.name])):
            self.progress.setEnabled(False)

    def start_protocol(self):
        file_name = self._lwdgt_files.currentItem().text()
        protocol_name = self.lwdgt_protocols.currentItem().text()

        # Start recording
        self.main.recordings.start_recording()

        # Start protocol
        IPC.rpc(Def.Process.Controller, process.Controller.start_protocol, '.'.join([file_name, protocol_name]))

    def abort_protocol(self):
        IPC.rpc(Def.Process.Controller, process.Controller.abortProtocol)

