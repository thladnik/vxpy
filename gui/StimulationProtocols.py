import importlib
import os
from PyQt5 import QtCore, QtWidgets

import MappApp_Definition as madef
import MappApp_Protocol as maprot

class StimulationProtocols(QtWidgets.QWidget):

    def __init__(self, main):
        super().__init__(parent=main, flags=QtCore.Qt.Window)

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

        for file in os.listdir(madef.Paths.Protocol):
            file = file.replace('.py', '')
            protocol_file = importlib.import_module('%s.%s' % (madef.Paths.Protocol, file))
            for key, data in protocol_file.__dict__.items():
                if not(key.startswith('_')) and data.mro()[1] == maprot.StimulationProtocol:
                    self._cb_protocols.addItem('%s>%s' % (file, key))


    def startStimulationProtocol(self):
        protocol_name = self._cb_protocols.currentText().split('>')

        protocol = getattr(importlib.import_module('%s.%s' % (madef.Paths.Protocol, protocol_name[0])), protocol_name[1])

        self.parent().ctrl.listener.sendToClient(madef.Processes.DISPLAY,
                                        [macom.Display.Code.SetNewStimulationProtocol, protocol])
