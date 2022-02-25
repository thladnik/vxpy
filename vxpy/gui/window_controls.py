import os
from os.path import abspath
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QLabel
import h5gview

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions
from vxpy.core import ipc, logger
from vxpy import modules
from vxpy.core.gui import IntegratedWidget

log = logger.getLogger(__name__)


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

    @staticmethod
    def _set_process_state(le: QtWidgets.QLineEdit, state: Enum):
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

        # Set object name for stylesheet access via class
        self.wdgt = QtWidgets.QWidget()
        self.wdgt.setLayout(QtWidgets.QGridLayout())
        self.wdgt.setObjectName('RecordingWidget')
        self.layout().addWidget(self.wdgt)

        # Add exposed methods
        self.exposed.append(RecordingWidget.show_lab_notebook)
        self.exposed.append(RecordingWidget.close_lab_notebook)

        v_spacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)

        self.lab_nb_folder = None
        self.h5views: Dict[str, h5gview.ui.Main] = {}

        # Basic properties
        self.default_controls_width = 300
        self.default_notebook_width = 300
        self.setCheckable(True)

        # Create folder widget and add to widget
        self.folder_wdgt = QtWidgets.QWidget()
        self.folder_wdgt.setLayout(QtWidgets.QGridLayout())
        self.folder_wdgt.layout().setContentsMargins(0, 0, 0, 0)
        self.wdgt.layout().addWidget(self.folder_wdgt, 0, 0)

        # Current base folder for recordings
        self.base_dir = QtWidgets.QLineEdit('')
        self.base_dir.setDisabled(True)
        self.folder_wdgt.layout().addWidget(QLabel('Base folder'), 0, 0)
        self.folder_wdgt.layout().addWidget(self.base_dir, 0, 1)

        # Button: Open base folder
        self.btn_open_base_folder = QtWidgets.QPushButton('Open base folder')
        self.btn_open_base_folder.clicked.connect(self.open_base_folder)
        self.folder_wdgt.layout().addWidget(self.btn_open_base_folder, 1, 1)

        # Button: Open last recording
        self.btn_open_recording = QtWidgets.QPushButton('Open last recording')
        self.btn_open_recording.setDisabled(True)
        self.btn_open_recording.clicked.connect(self._open_last_recording)
        self.folder_wdgt.layout().addWidget(self.btn_open_recording, 2, 1)

        self.folder_wdgt.layout().addWidget(QLabel('Folder'), 3, 0)
        self.rec_folder = QtWidgets.QLineEdit()
        self.rec_folder.setEnabled(False)
        self.folder_wdgt.layout().addWidget(self.rec_folder, 3, 1)

        # Add separator
        self.hsep = QtWidgets.QFrame()
        self.hsep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.wdgt.layout().addWidget(self.hsep, 1, 0)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Controls widget
        self.controls = QtWidgets.QWidget()
        self.controls.setFixedWidth(self.default_controls_width)
        self.controls.setLayout(QtWidgets.QHBoxLayout())
        self.wdgt.layout().addWidget(self.controls, 2, 0)

        # Create left widget and add to controls
        self.interact_widget = QtWidgets.QWidget()
        self.interact_widget.setLayout(QtWidgets.QVBoxLayout())
        self.interact_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.controls.layout().addWidget(self.interact_widget)

        # Data compression
        self.interact_widget.layout().addWidget(QLabel('Compression'))
        self.compression_method = QtWidgets.QComboBox()
        self.compression_opts = QtWidgets.QComboBox()
        self.compression_method.addItems(['None', 'GZIP', 'LZF'])
        self.interact_widget.layout().addWidget(self.compression_method)
        self.interact_widget.layout().addWidget(self.compression_opts)
        self.compression_method.currentTextChanged.connect(self.set_compression_method)
        self.compression_method.currentTextChanged.connect(self.update_compression_opts)
        self.compression_opts.currentTextChanged.connect(self.set_compression_opts)

        # Buttons
        # Start
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_start.clicked.connect(self.start_recording)
        self.interact_widget.layout().addWidget(self.btn_start)
        # Pause
        self.btn_pause = QtWidgets.QPushButton('Pause')
        self.btn_pause.clicked.connect(self.pause_recording)
        self.interact_widget.layout().addWidget(self.btn_pause)
        # Stop
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.clicked.connect(self.finalize_recording)
        self.interact_widget.layout().addWidget(self.btn_stop)
        self.interact_widget.layout().addItem(v_spacer)

        # Show recorded routines
        self.rec_routines = QtWidgets.QGroupBox('Recorded attributes')
        self.rec_routines.setLayout(QtWidgets.QVBoxLayout())
        self.rec_attribute_list = QtWidgets.QListWidget()

        self.rec_routines.layout().addWidget(self.rec_attribute_list)
        # Update recorded attributes
        for match_string in config.CONF_REC_ATTRIBUTES:
            self.rec_attribute_list.addItem(QtWidgets.QListWidgetItem(match_string))
        self.controls.layout().addWidget(self.rec_routines)

        # Lab notebook (opened when recording is active)
        self.lab_notebook = QtWidgets.QWidget()
        self.lab_notebook.setLayout(QtWidgets.QVBoxLayout())
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Experimenter'))
        self.nb_experimenter = QtWidgets.QLineEdit()
        self.lab_notebook.layout().addWidget(self.nb_experimenter)
        self.lab_notebook.layout().addWidget(QtWidgets.QLabel('Notes'))
        self.nb_notes = QtWidgets.QTextEdit()
        self.lab_notebook.layout().addWidget(self.nb_notes)
        self.lab_notebook.hide()
        self.wdgt.layout().addWidget(self.lab_notebook, 0, 1, 3, 1)
        self.close_lab_notebook()

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

    @staticmethod
    def start_recording():
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.start_manual_recording)

    @staticmethod
    def pause_recording():
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.pause_recording)

    @staticmethod
    def finalize_recording():
        # First: pause recording
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.pause_recording)

        # Finally: stop recording
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.stop_manual_recording)

    @staticmethod
    def toggle_enable(newstate):
        ipc.rpc(PROCESS_CONTROLLER, modules.Controller.set_enable_recording, newstate)

    def get_compression_method(self):
        method = self.compression_method.currentText()
        if method == 'None':
            method = None
        else:
            method = method.lower()

        return method

    def _open_last_recording(self):
        base_path = abspath(config.CONF_REC_OUTPUT_FOLDER)
        recording_list = []
        for s in os.listdir(base_path):
            rec_path = os.path.join(base_path, s)
            if not os.path.isdir(rec_path):
                continue
            recording_list.append(rec_path)

        if len(recording_list) == 0:
            log.warning('Cannot open recording. No valid folders in base directory.')
            return

        last_recording = sorted(recording_list)[-1]
        file_list = [os.path.join(last_recording, s) for s in os.listdir(last_recording) if s.endswith('.hdf5')]

        self.h5views[last_recording] = h5gview.open_ui(file_list)

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
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(bool(ipc.Control.Recording[definitions.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(ipc.Control.Protocol[definitions.ProtocolCtrl.name]):
            self.btn_stop.setEnabled(False)

        self.base_dir.setText(config.CONF_REC_OUTPUT_FOLDER)
        self.btn_open_recording.setEnabled(bool(os.listdir(abspath(config.CONF_REC_OUTPUT_FOLDER))))


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

        if len(logger.get_history()) > self.logccount:
            for rec in logger.get_history()[self.logccount:]:

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