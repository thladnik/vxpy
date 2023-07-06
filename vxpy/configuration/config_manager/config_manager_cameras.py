import sys
from typing import Any, Dict, Tuple

import yaml
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

        self.rename_camera_btn = QtWidgets.QPushButton('')
        self.info.layout().addWidget(self.rename_camera_btn)
        self.rename_camera_btn.setDisabled(True)
        self.rename_camera_btn.clicked.connect(self.rename_camera)
        self.list.list_widget.itemSelectionChanged.connect(self.rename_camera_btn_update)

        self.info.layout().addWidget(QtWidgets.QLabel('Custom options (YAML format)'))
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

    def rename_camera_btn_update(self):
        items = self.list.list_widget.selectedItems()
        if len(items) == 0:
            self.rename_camera_btn.setDisabled(True)
            return

        self.rename_camera_btn.setEnabled(True)
        self.rename_camera_btn.setText(f'Rename device {items[0].text()}')

    def rename_camera(self):
        items = self.list.list_widget.selectedItems()

        if len(items) == 0:
            print('ERROR: select camera device to rename')
            return

        camera_id = items[0].text()

        new_camera_id, confirm = QtWidgets.QInputDialog.getText(self,
                                                                f'Rename unique camera device ID for {camera_id}',
                                                                'device_id', text=camera_id)

        if not confirm:
            return

        if new_camera_id in config.CAMERA_DEVICES:
            print('ERROR: new camera ID already in use')
            return

        # Retain config
        camera_conf = config.CAMERA_DEVICES[camera_id].copy()
        # Delete old entry
        del config.CAMERA_DEVICES[camera_id]
        # Create new config for new ID
        config.CAMERA_DEVICES[new_camera_id] = camera_conf

        # Reload and select new ID
        self.reload_cameras()
        for i in range(self.list.list_widget.count()):
            item = self.list.list_widget.item(i)
            if item.text() == new_camera_id:
                self.list.list_widget.setCurrentItem(item)
                break

            self.list.list_widget.setCurrentItem()

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
        self.opts.setText(yaml.dump(config.CAMERA_DEVICES[camera_id]))

    def save_camera_opts(self):
        items = self.list.list_widget.selectedItems()

        if len(items) == 0:
            return

        camera_id = items[0].text()

        try:
            opts_dict = yaml.safe_load(self.opts.toPlainText())
        except:
            print('ERROR: can not save camera options. Invalid format.')
        else:
            if not isinstance(opts_dict, dict):
                print('ERROR: can not save camera options. Not a dictionary.')
                return

            # Update config
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
                         'vxpy.devices.camera.basler_pylon.BaslerCamera',
                         'vxpy.devices.camera.virtual_camera.VirtualCamera']
        elif sys.platform == 'linux':
            api_paths = ['vxpy.devices.camera.tis_linux_gst.TISCamera',
                         'vxpy.devices.camera.basler_pylon.BaslerCamera',
                         'vxpy.devices.camera.virtual_camera.VirtualCamera']
        else:
            print(f'ERROR: no camera interfaces available for system {sys.platform}')
            return

        # Go through all camera APIs
        for api in api_paths:
            camera_cls = vxcamera.get_camera_interface(api)
            if camera_cls is None:
                print(f'ERROR: unable to load camera interface {api}')
                continue

            # Get list of available camera devices for API
            for camera in camera_cls.get_camera_list():
                opts = {'api': api,
                        **camera.get_settings()}
                self.list.add_item(f'{camera} ({api})', opts)

    def selection_confirmed(self):
        camera_id, confirm = QtWidgets.QInputDialog.getText(self, 'Input a unique ID for new camera', 'device_id')

        if not confirm:
            return

        self.new_camera_data = (camera_id, self.current_camera_item.data(QtCore.Qt.ItemDataRole.UserRole))

        self.accept()

    def queried_item(self, item: QtWidgets.QListWidgetItem):
        self.current_camera_item = item
