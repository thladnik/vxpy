import pprint

import yaml
from PySide6 import QtCore, QtWidgets
from vxpy import config
from vxpy import utils
from vxpy.utils import widgets
import vxpy.core.routine as vxroutine
import vxpy.extras


class RoutineManager(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self.setLayout(QtWidgets.QHBoxLayout())

        # Controls
        self.controls = QtWidgets.QWidget()
        self.controls.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.controls)
        self.add_routine_btn = QtWidgets.QPushButton('Add routine')
        self.add_routine_btn.clicked.connect(self._new_routine)
        self.controls.layout().addWidget(self.add_routine_btn)
        self.remove_routine_btn = QtWidgets.QPushButton('Remove routine')
        self.remove_routine_btn.clicked.connect(self._remove_routine)
        self.controls.layout().addWidget(self.remove_routine_btn)
        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Maximum,
                                       QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.controls.layout().addItem(spacer)

        # Routine list
        self.routine_list = widgets.SearchableListWidget()
        self.layout().addWidget(self.routine_list)

        # Routine info
        self.routine_info = QtWidgets.QWidget()
        self.routine_info.setMaximumWidth(600)
        self.routine_info.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.routine_info)
        self.routine_doc = QtWidgets.QTextEdit()
        self.routine_doc.setReadOnly(True)
        self.routine_info.layout().addWidget(self.routine_doc)

        self.routine_info.layout().addWidget(QtWidgets.QLabel('Custom options (YAML format)'))
        self.routine_opts = QtWidgets.QTextEdit()
        self.routine_info.layout().addWidget(self.routine_opts)
        self.save_routine_opts_btn = QtWidgets.QPushButton('Save options')
        self.save_routine_opts_btn.clicked.connect(self.save_routine_opts)
        self.routine_info.layout().addWidget(self.save_routine_opts_btn)

        self.routine_list.list_widget.itemSelectionChanged.connect(self.update_routine_info)

        # Load initially
        self.reload_routines()

    def reload_routines(self):
        self.routine_list.clear()
        for path in config.ROUTINES.keys():
            self.routine_list.add_item(path)

    def _new_routine(self):

        dialog = AvailableRoutines(self)
        answer = dialog.exec_()
        routine_path = dialog.current_routine_path
        if answer and routine_path is not None:
            self._add_routine(routine_path)

    def _remove_routine(self):
        items = self.routine_list.list_widget.selectedItems()
        if len(items) == 0:
            print('WARNING: select routine to remove')
            return

        routine_path = items[0].text()
        print(f'Remove routine {routine_path}')
        if not routine_path in config.ROUTINES:
            return

        del config.ROUTINES[routine_path]

        self.reload_routines()
        self.update_routine_info()

    def _add_routine(self, routine_path):
        print(f'Add routine {routine_path}')
        if routine_path in config.ROUTINES:
            print(f'ERROR: Unable to add routine {routine_path} to routine config. '
                  f'Already in list')
            return

        config.ROUTINES[routine_path] = {}

        self.reload_routines()

    def update_routine_info(self):
        items = self.routine_list.list_widget.selectedItems()

        if len(items) == 0:
            self.routine_doc.clear()
            self.routine_opts.clear()
            return

        routine_path = items[0].text()

        routine_cls = vxroutine.get_routine(routine_path)
        self.routine_doc.setText(f'{routine_cls.__name__}\n---\n\n{routine_cls.__doc__}')
        self.routine_opts.setText(yaml.dump(config.ROUTINES[routine_path]))

    def save_routine_opts(self):
        items = self.routine_list.list_widget.selectedItems()

        if len(items) == 0:
            return

        routine_path = items[0].text()

        try:
            opts_dict = yaml.safe_load(self.routine_opts.toPlainText())
        except:
            print('ERROR: can not save routine options. No valid YAML format.')
        else:
            if not isinstance(opts_dict, dict):
                print('ERROR: can not save routine options. Not a dictionary.')
                return

            if routine_path in config.ROUTINES:
                config.ROUTINES[routine_path] = opts_dict


class AvailableRoutines(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())
        self.setWindowTitle('Select routine to add')
        self.resize(800, 600)

        self.list = widgets.SearchableListWidget()
        self.list.list_widget.itemClicked.connect(self.queried_item)
        self.layout().addWidget(self.list, 0, 0)

        self.layout().addWidget(QtWidgets.QGroupBox('INFO'), 0, 1)

        opts = QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        self.button_box = QtWidgets.QDialogButtonBox(opts)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout().addWidget(self.button_box, 1, 0, 1, 2)

        self.reload_routines()

        self.current_routine_path: str = None

    def reload_routines(self):
        # Add to list
        excl_types = [vxroutine.Routine,
                      vxroutine.CameraRoutine, vxroutine.DisplayRoutine,
                      vxroutine.IoRoutine, vxroutine.WorkerRoutine]

        routine_paths = utils.get_imports_from('plugins', vxroutine.Routine, excl_types=excl_types)
        routine_paths.extend(utils.get_imports_from(vxpy.extras, vxroutine.Routine, excl_types=excl_types))
        self.list.clear()
        for path, _type in routine_paths:
            if path in config.ROUTINES.keys():
                continue
            self.list.add_item(path)

    def queried_item(self, item: QtWidgets.QListWidgetItem):
        self.current_routine_path = item.text()
