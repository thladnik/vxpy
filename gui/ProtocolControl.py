"""
MappApp ./gui/ProtocolControl.py - GUI widget for selection and execution of stimulation protocols.
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

import importlib
import os
from PyQt5 import QtCore, QtWidgets

import Controller
import Def
import IPC
import protocols

class Protocols(QtWidgets.QWidget):

    def __init__(self, _main):
        self.main = _main
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)

        self.setupUi()

    def setupUi(self):

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        self.setMinimumSize(400, 100)
        self.setWindowTitle('Stimulation Protocols')

        # File list
        self._lwdgt_files = QtWidgets.QListWidget()
        self._lwdgt_files.setFixedWidth(200)
        self._lwdgt_files.itemSelectionChanged.connect(self._compileProtocolList)
        self.layout().addWidget(self._lwdgt_files, 0, 0, 2, 1)
        # Protocol list
        self._lwdgt_protocols = QtWidgets.QListWidget()
        self._lwdgt_protocols.setFixedWidth(200)
        self._lwdgt_protocols.itemSelectionChanged.connect(self._updateProtocolInfo)
        self.layout().addWidget(self._lwdgt_protocols, 0, 1, 2, 1)

        # Start button
        self._btn_start_protocol = QtWidgets.QPushButton('Start protocol')
        self._btn_start_protocol.clicked.connect(self.startStimulationProtocol)
        self.layout().addWidget(self._btn_start_protocol, 0, 2)

        ### Once set up: compile file list for first time
        self._compileFileList()

    def _compileFileList(self):
        self._lwdgt_files.clear()
        self._btn_start_protocol.setEnabled(False)

        for file in protocols.all():
            self._lwdgt_files.addItem(file)

    def _compileProtocolList(self):
        self._lwdgt_protocols.clear()
        self._btn_start_protocol.setEnabled(False)

        for protocol in protocols.read(protocols.open(self._lwdgt_files.currentItem().text())):
            self._lwdgt_protocols.addItem(protocol._name)

    def _updateProtocolInfo(self):
        self._btn_start_protocol.setEnabled(IPC.inState(Def.State.IDLE, Def.Process.Controller))

    def startStimulationProtocol(self):
        file_name = self._lwdgt_files.currentItem().text()
        protocol_name = self._lwdgt_protocols.currentItem().text()

        self.main.rpc(Def.Process.Controller, Controller.Controller.startProtocol,
                      '.'.join([file_name[:-3], protocol_name]))
