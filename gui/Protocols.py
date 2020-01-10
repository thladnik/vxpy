"""
MappApp ./gui/Protocols.py - GUI widget for selection and execution of stimulation protocols.
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

import Definition
import process.Display
import Protocol

class Protocols(QtWidgets.QWidget):

    def __init__(self, _main):
        self._main = _main
        QtWidgets.QWidget.__init__(self, parent=_main, flags=QtCore.Qt.Window)

        self.setupUi()

    def setupUi(self):

        ## Setup widget
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setMinimumSize(400, 100)
        self.setWindowTitle('Stimulation Protocols')

        # Protocol list
        self._cb_protocols = QtWidgets.QComboBox()
        self._compileProtocolList()
        self.layout().addWidget(self._cb_protocols)

        # Start button
        self._btn_startProtocol = QtWidgets.QPushButton('Start protocol')
        self._btn_startProtocol.clicked.connect(self.startStimulationProtocol)
        self.layout().addWidget(self._btn_startProtocol)

    def _compileProtocolList(self):
        self._cb_protocols.clear()

        for file in os.listdir(Definition.Path.Protocol):
            file = file.replace('.py', '')
            protocol_file = importlib.import_module('%s.%s' % (Definition.Path.Protocol, file))
            for key, data in protocol_file.__dict__.items():
                if not(key.startswith('_')) and data.mro()[1] == Protocol.StaticStimulationProtocol:
                    self._cb_protocols.addItem('%s>%s' % (file, key))


    def startStimulationProtocol(self):
        protocol_name = self._cb_protocols.currentText().split('>')
        protocol = getattr(importlib.import_module('%s.%s' % (Definition.Path.Protocol, protocol_name[0])), protocol_name[1])

        self._main.rpc(Definition.Process.Display, process.Display.Main.startNewStimulationProtocol, protocol)
