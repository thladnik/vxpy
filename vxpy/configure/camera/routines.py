from PySide6 import QtCore, QtWidgets

class Settings(QtWidgets.QGroupBox):

    def __init__(self):
        QtWidgets.QGroupBox.__init__(self, 'Routine settings')

        self.setLayout(QtWidgets.QHBoxLayout())

        # Available routines
        self.layout().addWidget(QtWidgets.QLabel('Available routines'))
        self.avail_routine_list = QtWidgets.QComboBox()
        self.layout().addWidget(self.avail_routine_list)

        # Add
        self.btn_add_routine = QtWidgets.QPushButton('Add routine')
        self.btn_add_routine.clicked.connect(self.add_routine)
        self.layout().addWidget(self.btn_add_routine)

        self.layout().addWidget(QtWidgets.QLabel('Selected routines'))
        # Remove
        self.btn_remove_routine = QtWidgets.QPushButton('Remove selected')
        self.btn_remove_routine.clicked.connect(self.remove_routine)
        self.btn_remove_routine.setEnabled(False)
        self.layout().addWidget(self.btn_remove_routine)

        # Used routines
        self.used_routine_list = QtWidgets.QListWidget()
        self.used_routine_list.setMaximumWidth(400)
        self.used_routine_list.currentTextChanged.connect(self.toggle_routine_remove_btn)
        self.layout().addWidget(QtWidgets.QLabel('Routines'))
        self.layout().addWidget(self.used_routine_list)