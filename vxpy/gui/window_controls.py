
from os.path import abspath
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QLabel

from vxpy import Config
from vxpy import Def
from vxpy.core import ipc
from vxpy import Logging
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

        self.setFixedWidth(240)

        # Setup widget
        self.setLayout(QtWidgets.QGridLayout())
        # self.setMinimumSize(QtCore.QSize(0,0))
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        # self.layout().setColumnMinimumWidth(2, 150)

        # Controller modules status
        self._add_process(Def.Process.Controller)
        # Camera modules status
        self._add_process(Def.Process.Camera)
        # Display modules status
        self._add_process(Def.Process.Display)
        # Gui modules status
        self._add_process(Def.Process.Gui)
        # IO modules status
        self._add_process(Def.Process.Io)
        # Worker modules status
        self._add_process(Def.Process.Worker)
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

    def _set_process_state(self,le: QtWidgets.QLineEdit,code):
        # Set text
        le.setText(Def.MapStateToStr[code] if code in Def.MapStateToStr else '')

        # Set style
        if code == Def.State.IDLE:
            le.setStyleSheet('color: #3bb528; font-weight:bold;')
        elif code == Def.State.STARTING:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.READY:
            le.setStyleSheet('color: #3c81f3; font-weight:bold;')
        elif code == Def.State.STOPPED:
            le.setStyleSheet('color: #d43434; font-weight:bold;')
        elif code == Def.State.RUNNING:
            le.setStyleSheet('color: #deb737; font-weight:bold;')
        else:
            le.setStyleSheet('color: #000000')

    def _update_states(self):
        for process_name, state_widget in self.state_widgets.items():
            self._set_process_state(state_widget, ipc.get_state(process_name))


class RecordingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Recordings', *args)
        # Create inner widget
        self.setLayout(QtWidgets.QVBoxLayout())

        self.exposed.append(RecordingWidget.show_lab_notebook)
        self.exposed.append(RecordingWidget.close_lab_notebook)

        self.wdgt = QtWidgets.QWidget()
        self.wdgt.setLayout(QtWidgets.QGridLayout())
        self.wdgt.setObjectName('RecordingWidget')
        self.layout().addWidget(self.wdgt)

        vSpacer = QtWidgets.QSpacerItem(1,1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)

        # Basic properties
        self.setCheckable(True)
        self.setMaximumWidth(400)

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

        self.wdgt.layout().addWidget(self.folder_wdgt, 1, 0, 1, 2)
        self.hsep = QtWidgets.QFrame()
        self.hsep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.wdgt.layout().addWidget(self.hsep, 2, 0, 1, 2)

        # GroupBox
        self.clicked.connect(self.toggle_enable)

        # Left widget
        self.left_wdgt = QtWidgets.QWidget()
        self.left_wdgt.setLayout(QtWidgets.QVBoxLayout())
        self.left_wdgt.layout().setContentsMargins(0,0,0,0)
        self.wdgt.layout().addWidget(self.left_wdgt, 5, 0)

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
        for match_string in Config.Recording[Def.RecCfg.attributes]:
            self.rec_attribute_list.addItem(QtWidgets.QListWidgetItem(match_string))
        self.rec_routines.layout().addItem(vSpacer)
        self.wdgt.layout().addWidget(self.rec_routines, 5, 1)

        # Set timer for GUI update
        self.tmr_update_gui = QtCore.QTimer()
        self.tmr_update_gui.setInterval(200)
        self.tmr_update_gui.timeout.connect(self.update_ui)
        self.tmr_update_gui.start()

    def set_compression_method(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.set_compression_method, self.get_compression_method())

    def set_compression_opts(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.set_compression_opts, self.get_compression_opts())

    def open_base_folder(self):
        output_path = abspath(Config.Recording[Def.RecCfg.output_folder])
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(output_path.replace('\\', '/')))

    def show_lab_notebook(self):
        self.lab_notebook = QtWidgets.QWidget()
        self.lab_notebook.resize(400,400)
        self.lab_notebook.show()

    def close_lab_notebook(self):
        self.lab_notebook.close()

    def start_recording(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.start_manual_recording)

    def pause_recording(self):
        ipc.rpc(Def.Process.Controller, modules.Controller.pause_recording)

    def finalize_recording(self):
        # First: pause recording
        ipc.rpc(Def.Process.Controller, modules.Controller.pause_recording)

        reply = QtWidgets.QMessageBox.question(self, 'Finalize recording', 'Give me session data and stuff...',
                                               QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard,
                                               QtWidgets.QMessageBox.StandardButton.Save)
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            print('Save metadata and stuff...')
        else:
            reply = QtWidgets.QMessageBox.question(self, 'Confirm discard', 'Are you sure you want to DISCARD all recorded data?',
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.No)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                print('Fine... I`ll trash it all..')
            else:
                print('Puh... good choice')

        # Finally: stop recording
        print('Stop recording...')
        ipc.rpc(Def.Process.Controller, modules.Controller.stop_manual_recording)

    def toggle_enable(self, newstate):
        ipc.rpc(Def.Process.Controller, modules.Controller.set_enable_recording, newstate)

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

        enabled = ipc.Control.Recording[Def.RecCtrl.enabled]
        active = ipc.Control.Recording[Def.RecCtrl.active]
        current_folder = ipc.Control.Recording[Def.RecCtrl.folder]

        if active and enabled:
            self.wdgt.setStyleSheet('QWidget#RecordingWidget {background: rgba(179, 31, 18, 0.5);}')
        else:
            self.wdgt.setStyleSheet('QWidget#RecordingWidgetQGroupBox#RecGroupBox {background: rgba(0, 0, 0, 0.0);}')

        # Set enabled
        self.setCheckable(not(active) and not(bool(current_folder)))
        self.setChecked(enabled)

        # Set current folder
        self.rec_folder.setText(ipc.Control.Recording[Def.RecCtrl.folder])

        # Set buttons dis-/enabled
        # Start
        self.btn_start.setEnabled(not(active) and enabled)
        self.btn_start.setText('Start' if ipc.in_state(Def.State.IDLE, Def.Process.Controller) else 'Resume')
        # Pause // TODO: implement pause functionality during non-protocol recordings?
        #self._btn_pause.setEnabled(active and enabled)
        self.btn_pause.setEnabled(False)
        # Stop
        self.btn_stop.setEnabled(bool(ipc.Control.Recording[Def.RecCtrl.folder]) and enabled)
        # Overwrite stop button during protocol
        if bool(ipc.Control.Protocol[Def.ProtocolCtrl.name]):
            self.btn_stop.setEnabled(False)

        self.base_dir.setText(Config.Recording[Def.RecCfg.output_folder])


class LoggingWidget(IntegratedWidget):

    def __init__(self, *args):
        IntegratedWidget.__init__(self, 'Log', *args)

        self.setLayout(QtWidgets.QHBoxLayout())

        self.txe_log = QtWidgets.QTextEdit()
        self.txe_log.setReadOnly(True)
        self.txe_log.setFontFamily('Courier')
        self.layout().addWidget(self.txe_log)

        # Set initial log line count
        self.logccount = 0

        # Set timer for updating of log
        self.timer_logging = QtCore.QTimer()
        self.timer_logging.timeout.connect(self.print_log)
        self.timer_logging.start(50)

    def print_log(self):
        if ipc.Log.File is None:
            return

        if len(ipc.Log.History) > self.logccount:
            for rec in ipc.Log.History[self.logccount:]:

                self.logccount += 1

                # Skip for debug and unset
                if rec['levelno'] < 20:
                    continue

                # Info
                if rec['levelno'] == 20:
                    self.txe_log.setTextColor(QtGui.QColor('black'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)
                # Warning
                elif rec['levelno'] == 30:
                    self.txe_log.setTextColor(QtGui.QColor('orange'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Error and critical
                elif rec['levelno'] > 30:
                    self.txe_log.setTextColor(QtGui.QColor('red'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Bold)
                # Fallback
                else:
                    self.txe_log.setTextColor(QtGui.QColor('black'))
                    self.txe_log.setFontWeight(QtGui.QFont.Weight.Normal)

                # Add
                line = '{}  {:10}  {:10}  {}'.format(rec['asctime'], rec['name'], rec['levelname'], rec['msg'])
                self.txe_log.append(line)