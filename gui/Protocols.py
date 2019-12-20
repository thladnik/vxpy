import importlib
import os
from PyQt5 import QtCore, QtWidgets

import Definition
import StaticProtocol

class Protocols(QtWidgets.QWidget):

    def __init__(self, main):
        self.main = main
        QtWidgets.QWidget.__init__(self, parent=None, flags=QtCore.Qt.Window)

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
                if not(key.startswith('_')) and data.mro()[1] == StaticProtocol.StimulationProtocol:
                    self._cb_protocols.addItem('%s>%s' % (file, key))


    def startStimulationProtocol(self):
        protocol_name = self._cb_protocols.currentText().split('>')
        protocol = getattr(importlib.import_module('%s.%s' % (Definition.Path.Protocol, protocol_name[0])), protocol_name[1])

        self.main._rpcToProcess(Definition.Process.Display, Definition.Process.Display.startNewStimulationProtocol, protocol)
