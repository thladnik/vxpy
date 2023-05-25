import pprint
import sys
from typing import Any, Dict, Tuple

from PySide6 import QtCore, QtWidgets
from vxpy import config
from vxpy import utils
from vxpy.utils import widgets
import vxpy.core.devices.camera as vxcamera
import vxpy.extras


class CameraManager(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

        self.setLayout(QtWidgets.QHBoxLayout())

        # Controls
        self.controls = QtWidgets.QWidget()
        self.controls.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.controls)
        self.add_camera_btn = QtWidgets.QPushButton('Add camera')
        self.add_camera_btn.clicked.connect(self._new_routine)
        self.controls.layout().addWidget(self.add_camera_btn)
        self.remove_camera_btn = QtWidgets.QPushButton('Remove camera')
        self.remove_camera_btn.clicked.connect(self._remove_camera)
        self.controls.layout().addWidget(self.remove_camera_btn)
        spacer = QtWidgets.QSpacerItem(1, 1,
                                       QtWidgets.QSizePolicy.Policy.Maximum,
                                       QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.controls.layout().addItem(spacer)

        # List
        self.list = widgets.SearchableListWidget()
        self.layout().addWidget(self.list)

        # Infos panel
        self.info = QtWidgets.QWidget()
        self.info.setMaximumWidth(600)
        self.info.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.info)
        self.doc = QtWidgets.QTextEdit()
        self.doc.setReadOnly(True)
        self.info.layout().addWidget(self.doc)

        self.info.layout().addWidget(QtWidgets.QLabel('Custom options (Python dictionary)'))
        self.opts = QtWidgets.QTextEdit()
        self.info.layout().addWidget(self.opts)
        self.save_opts_btn = QtWidgets.QPushButton('Save options')
        self.save_opts_btn.clicked.connect(self.save_camera_opts)
        self.info.layout().addWidget(self.save_opts_btn)

        self.list.list_widget.itemSelectionChanged.connect(self.update_camera_info)

        # Load initially
        self.reload_cameras()

    def reload_cameras(self):
        self.list.clear()
        for path in config.CAMERA_DEVICES:
            self.list.add_item(path)

    def _new_routine(self):

        dialog = AvailableCameras(self)
        answer = dialog.exec_()
        camera_id, camera_opts = dialog.new_camera_data
        if answer and camera_id is not None:
            self.add_camera(camera_id, camera_opts)

    def _remove_camera(self):
        items = self.list.list_widget.selectedItems()
        if len(items) == 0:
            print('WARNING: select routine to remove')
            return

        camera_id = items[0].text()
        print(f'Remove routine {camera_id}')
        if not camera_id in config.CAMERA_DEVICES:
            return

        del config.CAMERA_DEVICES[camera_id]

        self.reload_cameras()
        self.update_camera_info()

    def add_camera(self, camera_id: str, camera_opts):
        print(f'Add camera {camera_id}')
        if camera_id in config.ROUTINES:
            print(f'ERROR: Unable to add camera {camera_id} to routine config. '
                  f'Already in list')
            return

        config.CAMERA_DEVICES[camera_id] = camera_opts

        self.reload_cameras()

    def update_camera_info(self):
        items = self.list.list_widget.selectedItems()

        if len(items) == 0:
            self.doc.clear()
            self.opts.clear()
            return

        camera_id = items[0].text()

        if camera_id not in config.CAMERA_DEVICES:
            return

        camera_api = config.CAMERA_DEVICES[camera_id]['api']
        camera_cls = vxcamera.get_camera_interface(camera_api)

        self.doc.setText(f'{camera_cls.__name__}\n---\n\n{camera_cls.__doc__}')
        self.opts.setText(pprint.pformat(config.CAMERA_DEVICES[camera_id], indent=4, width=150))

    def save_camera_opts(self):
        items = self.list.list_widget.selectedItems()

        if len(items) == 0:
            return

        camera_id = items[0].text()
        opts = self.opts.toPlainText()

        try:
            opts_dict = eval(opts)
        except:
            print('ERROR: can not save camera options. No valid python format.')
        else:
            if not isinstance(opts_dict, dict):
                print('ERROR: can not save camera options. Not a dictionary.')
                return

            if camera_id in config.CAMERA_DEVICES:
                config.CAMERA_DEVICES[camera_id] = opts_dict


class AvailableCameras(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())
        self.setWindowTitle('Select camera to add')
        self.resize(800, 600)

        self.list = widgets.SearchableListWidget()
        self.list.list_widget.itemClicked.connect(self.queried_item)
        self.layout().addWidget(self.list, 0, 0)

        self.layout().addWidget(QtWidgets.QGroupBox('INFO'), 0, 1)

        opts = QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        self.button_box = QtWidgets.QDialogButtonBox(opts)
        self.button_box.accepted.connect(self.selection_confirmed)
        self.button_box.rejected.connect(self.reject)
        self.layout().addWidget(self.button_box, 1, 0, 1, 2)

        self.reload_cameras()

        self.new_camera_data: Tuple[str, Dict[str, Any]] = ('', {})
        self.current_camera_item: str = None

    def reload_cameras(self):
        self.list.clear()

        if sys.platform == 'win32':
            api_paths = ['vxpy.devices.camera.tis_windows_tisgrabber.TISCamera',
                         'vxpy.devices.camera.basler_pylon.BaslerCamera']
        elif sys.platform == 'linux':
            api_paths = ['vxpy.devices.camera.tis_linux_gst.TISCamera',
                         'vxpy.devices.camera.basler_pylon.BaslerCamera']
        else:
            print(f'ERROR: no camera interfaces available for system {sys.platform}')
            return

        for api in api_paths:
            camera_cls = vxcamera.get_camera_interface(api)
            if camera_cls is None:
                print(f'ERROR: unable to load camera interface {api}')
                continue

            for camera in camera_cls.get_camera_list():
                opts = {'api': api,
                        'model': camera.properties['model'],
                        'serial': camera.properties['serial']}
                self.list.add_item(f'{camera} ({api})', opts)

        # Add to list
        # excl_types = [vxcamera.CameraDevice]

        # routine_paths = utils.get_imports_from('plugins', vxcamera.CameraDevice, excl_types=excl_types)
        # routine_paths.extend(utils.get_imports_from(vxpy.extras, vxcamera.CameraDevice, excl_types=excl_types))
        # self.list.clear()
        # for path, _type in routine_paths:
        #     if path in config.ROUTINES.keys():
        #         continue
        #     self.list.add_item(path)

    def selection_confirmed(self):
        camera_id, confirm = QtWidgets.QInputDialog.getText(self, 'Input a unique ID for new camera', 'device_id')

        if not confirm:
            return

        self.new_camera_data = (camera_id, self.current_camera_item.data(QtCore.Qt.ItemDataRole.UserRole))

        self.accept()

    def queried_item(self, item: QtWidgets.QListWidgetItem):
        self.current_camera_item = item
