from os.path import abspath
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QLabel

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.core import ipc, logging
from vxpy import modules
from vxpy.core.gui import IntegratedWidget


class ProcessMonitorWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self,  'Process monitor', *args)

        self.exposed.append(ProcessMonitorWidget.update_process_interval)

        self.state_labels = dict()
        self.state_widgets = dict()
        self.intval_widgets = dict()

        self._setup_ui()

    def _add_process(self, process_name):
        i = len(self.state_labels)
        self.state_labels[process_name] = QtWidgets.QLabel(process_name)
        self.state_labels[process_name].setStyleSheet('font-weight:bold;')
        self.layout().addWidget(self.state_labels[process_name], i * 2, 0)
        self.state_widgets[process_name] = QtWidgets.QLineEdit('')
        self.state_widgets[process_name].setDisabled(True)
        self.state_widgets[process_name].setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.state_widgets[process_name], i * 2, 1)
        self.intval_widgets[process_name] = QtWidgets.QLineEdit('')
        self.intval_widgets[process_name].setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.intval_widgets[process_name].setDisabled(True)
        self.layout().addWidget(self.intval_widgets[process_name], i * 2 + 1, 0, 1, 2)

    def _setup_ui(self):

        self.setFixedWidth(150)

        # Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        # self.setMinimumSize(QtCore.QSize(0,0))
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        # self.layout().setColumnMinimumWidth(2, 150)

        # Controller modules status
        self._add_process(PROCESS_CONTROLLER)
        # Camera modules status
        self._add_process(PROCESS_CAMERA)
        # Display modules status
        self._add_process(PROCESS_DISPLAY)
        # Gui modules status
        self._add_process(PROCESS_GUI)
        # IO modules status
        self._add_process(PROCESS_IO)
        # Worker modules status
        self._add_process(PROCESS_WORKER)
        # Add spacer
        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(vSpacer, 6, 0)

        # Set timer for GUI update
        self._tmr_updateGUI = QtCore.QTimer()
        self._tmr_updateGUI.setInterval(100)
        self._tmr_updateGUI.timeout.connect(self._update_states)
        self._tmr_updateGUI.start()


    def update_process_interval(self, process_name, target_inval, mean_inval, std_inval):
        if process_name in self.intval_widgets:
            self.intval_widgets[process_name].setText('{:.1f}/{:.1f} ({:.1f}) ms'
                                                         .format(mean_inval * 1000,
                                                                 target_inval * 1000,
                                                                 std_inval * 1000))
        else:
            print(process_name, '{:.2f} +/- {:.2f}ms'.format(mean_inval * 1000, std_inval * 1000))

    def _set_process_state(self, le: QtWidgets.QLineEdit, state: Enum):
        # Set text
        le.setText(state.name)

        # Set style
        if state == definitions.State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif state == definitions.State.STARTING:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif state == definitions.State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif state == definitions.State.STOPPED:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        elif state == definitions.State.RUNNING:
            le.setStyleSheet('color: #deb737; font-weight:bold;')
        else:
            le.setStyleSheet('color: #000000')

    def _update_states(self):
        for process_name, state_widget in self.state_widgets.items():
            self._set_process_state(state_widget, ipc.get_state(process_name))


class RecordingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Recordings', *args)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.setContentsMargins(0,0,0,0)
        # self.setMaximumWidth(600)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Minimum)
        # Set object name for stylesheet access via class
        self.wdgt = QtWidgets.QWidget()
        self.wdgt.setLayout(QtWidgets.QHBoxLayout())
        self.wdgt.setObjectName('RecordingWidget')
        self.layout().addWidget(self.wdgt)

        self.exposed.append(RecordingWidget.show_lab_notebook)
        self.exposed.append(RecordingWidget.close_lab_notebook)

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)

        self.lab_nb_folder = None
        # Basic properties
        self.default_controls_width = 300
        self.default_notebook_width = 300
        self.setCheckable(True)

        self.controls = QtWidgets.QWidget()
        self.controls.setFixedWidth(self.default_controls_width)
        self.controls.setLayout(QtWidgets.QGridLayout())
        self.wdgt.layout().addWidget(self.controls)

        self.lab_notebook = QtWidgets.QWidget()
        self.lab_notebook.setLayout(QtWidgets.QGridLayout())
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Experimenter'), 0, 0)
        self.nb_experimenter = QtWidgets.QLineEdit()
        self.lab_notebook.layout().addWidget(self.nb_experimenter, 1, 0)
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Notes'), 2, 0)
        self.nb_notes = QtWidgets.QTextEdit()
        self.lab_notebook.layout().addWidget(self.nb_notes, 3, 0, 1, 2)
        self.lab_notebook.hide()
        self.wdgt.layout().addWidget(self.lab_notebook)
        self.close_lab_notebook()

        # Current folder
        self.folder_wdgt = QtWidgets.QWidget()
        self.folder_wdgt.setLayout(QtWidgets.QGridLayout())
        self.folder_wdgt.layout().setContentsMargins(0, 0, 0, 0)

        self.folder_wdgt.layout().addWidget(QLabel('Base dir.'), 0, 0)
        self.base_dir = QtWidgets.QLineEdit('')
        self.base_dir.setDisabled(True)
        self.folder_wdgt.layout().addWidget(self.base_dir, 0, 1, 1, 2)

        self.select_folder = QtWidgets.QPushButton('Select...')
        self.select_folder.setDisabled(True)
        self.folder_wdgt.layout().addWidget(self.select_folder, 1, 1)
        self.open_folder = QtWidgets.QPushButton('Open')
        self.open_folder.clicked.connect(self.open_base_folder)
        self.folder_wdgt.layout().addWidget(self.open_folder, 1, 2)

        self.folder_wdgt.layout().addWidget(QLabel('Folder'), 2, 0)
        self.rec_folder = QtWidgets.QLineEdit()
        self.rec_folder.setEnabled(False)
        self.folder_wdgt.layout().addWidget(self.rec_folder, 2, 1, 1, 2)

        self.controls.layout().addWidget(self.folder_wdgt, 1, 0, 1, 2)
        self.hsep = QtWidgets.QFrame()
        self.hsep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.controls.layout().addWidget(self.hsep, 2, 0, 1, 2)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Left widget
        self.left_wdgt = QtWidgets.QWidget()
        self.left_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.left_wdgt.layout().setContentsMargins(0,0,0,0)
        self.controls.layout().addWidget(self.left_wdgt, 5, 0)

        # Data compression
        self.left_wdgt.layout().addWidget(QLabel('Compression'))
        self.compression_method = QtWidgets.QComboBox()
        self.compression_opts = QtWidgets.QComboBox()
        self.compression_method.addItems(['None', 'GZIP', 'LZF'])
        self.left_wdgt.layout().addWidget(self.compression_method)
        self.left_wdgt.layout().addWidget(self.compression_opts)
        self.compression_method.currentTextChanged.connect(self.set_compression_method)
        self.compression_method.currentTextChanged.connect(self.update_compression_opts)
        self.compression_opts.currentTextChanged.connect(self.set_compression_opts)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_start.clicked.connect(self.start_recording)
        self.left_wdgt.layout().addWidget(self.btn_start)
        # Pause
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.clicked.connect(self.pause_recording)
        self.left_wdgt.layout().addWidget(self.btn_pause)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.clicked.connect(self.finalize_recording)
        self.left_wdgt.layout().addWidget(self.btn_stop)
        self.left_wdgt.layout().addItem(vSpacer)

        # Show recorded routines
        self.rec_routines = QtWidgets.QGroupBox('Recorded attributes')
        self.rec_routines.setLayout(QtWidgets.QVBoxLayout())
        self.rec_attribute_list = QtWidgets.QListWidget()

        self.rec_routines.layout().addWidget(self.rec_attribute_list)
        # Update recorded attributes
        for match_string in config.CONF_REC_ATTRIBUTES:
            self.rec_attribute_list.addItem(QtWidgets.QListWidgetItem(match_string))
        # self.rec_routines.layout().addItem(vSpacer)
        self.controls.layout().addWidget(self.rec_routines, 5, 1)

        # Set timer for GUI update
        self.tmr_update_gui = QtCore.QTimer()
        self.tmr_update_gui.setInterval(200)
        self.tmr_update_gui.timeout.connect(self.update_ui)
        self.tmr_update_gui.start()

    def set_compression_method(self):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.set_compression_method, self.get_compression_method())

    def set_compression_opts(self):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.set_compression_opts, self.get_compression_opts())

    def open_base_folder(self):
        output_path = abspath(config.CONF_REC_OUTPUT_FOLDER)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(output_path.replace('\\', '/')))

    def show_lab_notebook(self):
        self.setFixedWidth(self.default_controls_width + self.default_notebook_width)
        self.lab_nb_folder = ipc.Control.Recording[definitions.RecCtrl.folder]
        self.lab_notebook.show()

    def close_lab_notebook(self):
        margins = self.controls.layout().contentsMargins().left() + \
                  self.controls.layout().contentsMargins().right() + \
                  self.wdgt.layout().contentsMargins().left() + \
                  self.wdgt.layout().contentsMargins().right()
        self.setFixedWidth(self.default_controls_width + margins)
        if self.lab_nb_folder is not None:
            experimenter = self.nb_experimenter.text()
            notes = self.nb_notes.toPlainText()
            with open(os.path.join(self.lab_nb_folder, 'lab_notebook.txt'), 'w') as f:
                f.write(f'Experimenter: {experimenter}\n---\nNotes\n{notes}')
            self.lab_nb_folder = None
        self.nb_notes.clear()
        self.lab_notebook.close()

    def start_recording(self):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.start_manual_recording)

    def pause_recording(self):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.pause_recording)

    def finalize_recording(self):
        # First: pause recording
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.pause_recording)

        # reply = QtWidgets.QMessageBox.question(self, 'Finalize recording', 'Give me session data and stuff...',
        #                                        QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard,
        #                                        QtWidgets.QMessageBox.StandardButton.Save)
        # if reply == QtWidgets.QMessageBox.StandardButton.Save:
        #     pass
        # else:
        #     reply = QtWidgets.QMessageBox.question(self, 'Confirm discard', 'Are you sure you want to DISCARD all recorded data?',
        #                                            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        #                                            QtWidgets.QMessageBox.StandardButton.No)
        #     if reply == QtWidgets.QMessageBox.StandardButton.Yes:
        #         print('Fine... I`ll trash it all..')
        #     else:
        #         print('Puh... good choice')

        # Finally: stop recording
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.stop_manual_recording)

    def toggle_enable(self, newstate):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.set_enable_recording, newstate)

    def get_compression_method(self):
        method = self.compression_method.currentText()
        if method == 'None':
            method = None
        else:
            method = method.lower()

        return method

    def get_compression_opts(self):
        method = self.compression_method.currentText()
        opts = self.compression_opts.currentText()

        shuffle = opts.lower().find('shuffle') >= 0
        if len(opts) > 0 and method == 'GZIP':
            opts = dict(shuffle=shuffle,
                        compression_opts=int(opts[0]))
        elif method == 'LZF':
            opts = dict(shuffle=shuffle)
        else:
            opts = dict()

        return opts

    def update_compression_opts(self):
        self.compression_opts.clear()

        compr = self.compression_method.currentText()
        if compr == 'None':
            self.compression_opts.addItem('None')
        elif compr == 'GZIP':
            levels = range(10)
            self.compression_opts.addItems([f'{i} (shuffle)' for i in levels])
            self.compression_opts.addItems([str(i) for i in levels])
        elif compr == 'LZF':
            self.compression_opts.addItems(['None', 'Shuffle'])

    def update_ui(self):
        """(Periodically) update UI based on shared configuration"""

        enabled = ipc.Control.Recording[definitions.RecCtrl.enabled]
        active = ipc.Control.Recording[definitions.RecCtrl.active]
        current_folder = ipc.Control.Recording[definitions.RecCtrl.folder]

        if active and enabled:
            self.setStyleSheet('QWidget#RecordingWidget {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.setStyleSheet('QWidget#RecordingWidgetQGroupBox#RecGroupBox {background: rgba(0, 0, 0, 0.0);}')

        # Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        # Set current folder
        self.rec_folder.setText(ipc.Control.Recording[definitions.RecCtrl.folder])

        # Set buttons dis-/enabled
        # Start
        self.btn_start.setEnabled(not(active) and enabled)
        self.btn_start.setText('Start' if ipc.in_state(definitions.State.IDLE, PROCESS_CONTROLLER) else 'Resume')
        # Pause // TODO: implement pause functionality during non-protocol recordings?
        #self._btn_pause.setEnabled(active and enabled)
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(bool(ipc.Control.Recording[definitions.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(ipc.Control.Protocol[definitions.ProtocolCtrl.name]):
            self.btn_stop.setEnabled(False)

        self.base_dir.setText(config.CONF_REC_OUTPUT_FOLDER)


class LoggingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Log', *args)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        self.txe_log = QtWidgets.QTextEdit()
        self.font = QtGui.QFont()
        self.font.setPointSize(10)
        self.font.setFamily('Courier')
        self.txe_log.setFont(self.font)
        self.txe_log.setReadOnly(True)
        # self.format = QtGui.QTextBlockFormat()
        # self.format.setIndent(10)
        # self.txe_log.textCursor().setBlockFormat(self.format)
        self.txe_log.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.layout().addWidget(self.txe_log)

        # Set initial log line count
        self.logccount = 0

        self.loglevelname_limit = 30

        # Set timer for updating of log
        self.timer_logging = QtCore.QTimer()
        self.timer_logging.timeout.connect(self.print_log)
        self.timer_logging.start(50)

    def print_log(self):

        if len(logging.get_history()) > self.logccount:
            for rec in logging.get_history()[self.logccount:]:

                self.logccount += 1

                # Skip for debug and unset
                if rec.levelno < 20:
                    continue

                # Info
                if rec.levelno == 20:
                    self.txe_log.setTextColor(QtGui.QColor('black'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)
                # Warning
                elif rec.levelno == 30:
                    self.txe_log.setTextColor(QtGui.QColor('orange'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Error and critical
                elif rec.levelno > 30:
                    self.txe_log.setTextColor(QtGui.QColor('red'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Fallback
                else:
                    self.txe_log.setTextColor(QtGui.QColor('black'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)

                # Crop name if necessary
                name = rec.name
                if len(name) > self.loglevelname_limit:
                    name = name[:5] + '..' + name[-(self.loglevelname_limit-7):]

                # Format line
                str_format = '{:7} {} {:' + str(self.loglevelname_limit) + '} {}'
                line = str_format.format(rec.levelname, rec.asctime[-12:], name, rec.msg)

                # Add line
                self.txe_log.append(line)