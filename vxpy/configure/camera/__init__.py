"""
MappApp ./setup/display_calibration.py
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
from inspect import isclass
from typing import Union

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from vxpy import definitions
from vxpy.configure import acc
from vxpy.configure.utils import ModuleWidget
from vxpy.core.routine import Routine
from vxpy.definitions import *
from vxpy.devices import camera as camdev


# class CameraWidget(ModuleWidget):
#
#     def __init__(self, parent):
#         ModuleWidget.__init__(self, definitions.CameraCfg.name, parent=parent)
#         self.setLayout(QtWidgets.QGridLayout())
#         self.camera = None
#         # import json
#         # camdata = json.loads('{"api": "mappapp.devices.camera.tis.gst_linux", "serial": "25610433", "id": "zf_behavior", "format": "GRAY16_LE(640x480)@100", "exposure": 5.0, "gain": 1.5}')
#         # dev = mappapp.core.camera.open_device(camdata)
#
#         # Add new camera
#         self.btn_add_cam = QtWidgets.QPushButton('Add camera')
#         self.btn_add_cam.clicked.connect(self.add_camera)
#         self.layout().addWidget(self.btn_add_cam, 0, 3)
#
#         # Remove camera
#         self.btn_remove_cam = QtWidgets.QPushButton('Remove')
#         self.btn_remove_cam.clicked.connect(self.remove_camera)
#         self.btn_remove_cam.setEnabled(False)
#         self.layout().addWidget(self.btn_remove_cam, 0, 4)
#
#         # Camera list
#         self.camera_list = QtWidgets.QListWidget()
#         self.camera_list.setMaximumWidth(200)
#         self.camera_list.doubleClicked.connect(self.edit_camera)
#         self.camera_list.clicked.connect(self.open_stream)
#         self.camera_list.currentTextChanged.connect(self.toggle_cam_remove_btn)
#         self.layout().addWidget(QtWidgets.QLabel('Devices'), 1, 3, 1, 2)
#         self.layout().addWidget(self.camera_list, 2, 3, 1, 2)
#
#         # Camera stream
#         self.camera_stream = QtWidgets.QGroupBox('Camera stream')
#         self.camera_stream.setLayout(QtWidgets.QHBoxLayout())
#         self.layout().addWidget(self.camera_stream, 0, 5, 3, 1)
#         self.imview = pg.GraphicsView(parent=self)
#         self.imitem = pg.ImageItem()
#         self.imview.addItem(self.imitem)
#         self.camera_stream.layout().addWidget(self.imview)
#
#         self.stream_timer = QtCore.QTimer()
#         self.stream_timer.setInterval(50)
#         self.stream_timer.timeout.connect(self.update_stream)
#         self.stream_timer.start()
#
#     def load_settings_from_config(self):
#         self.camera = self.res_x = self.res_y = None
#         self.update_routine_list()
#         self.update_camera_list()
#         self.update_stream()
#
#     def update_routine_list(self):
#         self.avail_routine_list.clear()
#         self.used_routine_list.clear()
#
#         # Get routines listed in configuration
#         used_routines = list()
#         for fname, routines in acc.cur_conf.getParsed(definitions.CameraCfg.name, definitions.CameraCfg.routines).items():
#             for cname in routines:
#                 used_routines.append('{}.{}'.format(fname, cname))
#
#         # Get all available routines for camera
#         modules_list = list()
#         for fname in os.listdir(os.path.join(definitions.PATH_PACKAGE, PATH_ROUTINES, definitions.CameraCfg.name)):
#             if fname.startswith('_') \
#                 or fname.startswith('.') \
#                    or not(fname.endswith('.py')):
#                 continue
#
#             modules_list.append(fname.replace('.py', ''))
#
#         importpath = '.'.join([PATH_ROUTINES,
#                                definitions.CameraCfg.name.lower()])
#
#         modules = __import__(importpath, fromlist=modules_list)
#
#         avail_routines = list()
#         for fname in dir(modules):
#             if fname.startswith('_'):
#                 continue
#
#             file = getattr(modules, fname)
#
#             for cname in dir(file):
#                 attr = getattr(file, cname)
#                 if not(isclass(attr))\
#                         or not(issubclass(attr, Routine)) \
#                         or attr == Routine:
#                     if cname == 'Frames':
#                         import IPython
#                         IPython.embed()
#                     continue
#
#                 avail_routines.append('.'.join([fname, cname]))
#
#         # Calculate difference (available routines that are already used)
#         unused_routines = list(set(avail_routines) - set(used_routines))
#
#         self.avail_routine_list.addItems(unused_routines)
#
#         self.used_routine_list.addItems(used_routines)
#
#     def toggle_routine_remove_btn(self, p_str):
#         self.btn_remove_routine.setEnabled(bool(p_str))
#
#     def remove_routine(self):
#
#         routines = acc.cur_conf.getParsed(definitions.CameraCfg.name, definitions.CameraCfg.routines)
#
#         rname = self.used_routine_list.currentItem().text()
#         file_, class_ = rname.split('.')
#
#         # Show confirmation dialog
#         dialog = QtWidgets.QMessageBox()
#         dialog.setIcon(QtWidgets.QMessageBox.Information)
#         dialog.setText('Remove routine "{}"?'
#                        .format(rname))
#         dialog.setWindowTitle("Remove routine")
#         dialog.setStandardButtons(QtWidgets.QMessageBox.Ok
#                                   | QtWidgets.QMessageBox.Cancel)
#
#         if not(dialog.exec() == QtWidgets.QMessageBox.Ok):
#             return
#
#         # Remove routine
#         if file_ in routines and class_ in routines[file_]:
#             del routines[file_][routines[file_].index(class_)]
#
#         # If last routine from this file was remove, delete file key too
#         if not(bool(routines[file_])):
#             del routines[file_]
#
#         acc.cur_conf.setParsed(definitions.CameraCfg.name,
#                                definitions.CameraCfg.routines,
#                                routines)
#
#         self.load_settings_from_config()
#
#     def add_routine(self):
#         rname = self.avail_routine_list.currentText()
#
#         if not(bool(rname)):
#             return
#
#         file_, class_ = rname.split('.')
#
#         # Get routines
#         routines = acc.cur_conf.getParsed(definitions.CameraCfg.name,
#                                           definitions.CameraCfg.routines)
#
#         # Add new routine
#         if file_ not in routines:
#             routines[file_] = []
#         if class_ not in routines[file_]:
#             routines[file_].append(class_)
#
#         # Set routines
#         acc.cur_conf.setParsed(definitions.CameraCfg.name,
#                                definitions.CameraCfg.routines,
#                                routines)
#
#         # Update GUI
#         self.load_settings_from_config()
#
#     def update_camera_list(self):
#
#         self.camera_list.clear()
#         self.camera_list.addItems(acc.cur_conf.getParsed(definitions.CameraCfg.name,
#                                                          definitions.CameraCfg.device_id))
#
#     def toggle_cam_remove_btn(self, p_str):
#         self.btn_remove_cam.setEnabled(bool(p_str))
#
#     def remove_camera(self):
#
#         device_id = self.camera_list.currentItem().text()
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#         device_list = section[definitions.CameraCfg.device_id]
#
#         if not(device_id in device_list):
#             return
#
#         # Show confirmation dialog
#         dialog = QtWidgets.QMessageBox()
#         dialog.setIcon(QtWidgets.QMessageBox.Information)
#         dialog.setText('Remove camera device "{}"?'
#                        .format(device_id))
#         dialog.setWindowTitle("Remove camera")
#         dialog.setStandardButtons(QtWidgets.QMessageBox.Ok
#                                   | QtWidgets.QMessageBox.Cancel)
#
#         if not(dialog.exec() == QtWidgets.QMessageBox.Ok):
#             return
#
#         # Delete camera device from config
#         idx = device_list.index(device_id)
#
#         del device_list[idx]
#         manufacturer = section[definitions.CameraCfg.manufacturer]
#         del manufacturer[idx]
#         model = section[definitions.CameraCfg.model]
#         del model[idx]
#         format_ = section[definitions.CameraCfg.format]
#         del format_[idx]
#         res_x = section[definitions.CameraCfg.res_x]
#         del res_x[idx]
#         res_y = section[definitions.CameraCfg.res_y]
#         del res_y[idx]
#         gain = section[definitions.CameraCfg.gain]
#         del gain[idx]
#         exposure = section[definitions.CameraCfg.exposure]
#         del exposure[idx]
#
#         # Update config
#         name = definitions.CameraCfg.name
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.device_id, device_list)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.manufacturer, manufacturer)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.model, model)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.format, format_)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.res_x, res_x)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.res_y, res_y)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.gain, gain)
#         acc.cur_conf.setParsed(name, definitions.CameraCfg.exposure, exposure)
#
#         self.update_camera_list()
#
#     def add_camera(self):
#         row_idx = self.camera_list.count()
#
#         self.edit_camera(row_idx)
#
#     def edit_camera(self, idx: Union[int, QtCore.QModelIndex]):
#
#         if isinstance(idx, QtCore.QModelIndex):
#             row_idx = idx.row()
#         else:
#             row_idx = idx
#
#         ### Open dialog
#         dialog = EditCameraWidget(row_idx)
#         if not(dialog.exec_() == QtWidgets.QDialog.Accepted):
#             return
#
#         ### Update configuration
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#         ## Add new camera
#         if row_idx >= len(section[definitions.CameraCfg.device_id]):
#             action = 'Add'
#             for key, value in dialog.data.items():
#                 if not(key in section):
#                     continue
#                 section[key].append(value)
#         ## Update existing camera
#         else:
#             action = 'Update'
#             for key, value in dialog.data.items():
#                 if not(key in section):
#                     continue
#                 section[key][row_idx] = value
#
#         print('{} camera {}: {}'.format(action,
#                                         dialog.data[definitions.CameraCfg.device_id],
#                                         dialog.data))
#
#         for key, value in section.items():
#             acc.cur_conf.setParsed(definitions.CameraCfg.name, key, value)
#
#         self.update_camera_list()
#
#     def open_stream(self, idx: Union[int, QtCore.QModelIndex]):
#
#         if isinstance(idx, QtCore.QModelIndex):
#             row_idx = idx.row()
#         else:
#             row_idx = idx
#
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#
#         if self.camera is not None:
#             self.camera.stop()
#
#         import vxpy.devices.camera
#         try:
#             cam = getattr(vxpy.devices.camera_aio, section[definitions.CameraCfg.manufacturer][row_idx])
#             self.camera = cam(section[definitions.CameraCfg.model][row_idx], section[definitions.CameraCfg.format][row_idx])
#             self.res_x, self.res_y = section[definitions.CameraCfg.res_x][row_idx], section[definitions.CameraCfg.res_y][row_idx]
#             self.camera_stream.setMinimumWidth(section[definitions.CameraCfg.res_y][row_idx] + 30)
#             gain = section[definitions.CameraCfg.gain][row_idx]
#             exposure = section[definitions.CameraCfg.exposure][row_idx]
#             self.camera.set_gain(gain)
#             self.camera.set_exposure(exposure)
#             ### Provoke exception
#             self.camera.snap_image()
#             self.camera.get_image()
#         except Exception as exc:
#             print('Could not access device {}. Exception: {}'.format(section[definitions.CameraCfg.device_id][row_idx], exc))
#             import traceback
#             print(traceback.print_exc())
#             self.camera = self.res_x = self.res_y = None
#
#     def update_stream(self):
#         import numpy as np
#         if self.camera is None:
#             self.imitem.setImage(np.zeros((1,1)))
#             return
#
#         self.camera.snap_image()
#         im = self.camera.get_image()
#         im = im[:self.res_y, :self.res_x]
#         self.imitem.setImage(im)
#
#     def closed_main_window(self):
#         if self.camera is not None:
#             self.camera.stop()
#
# class EditCameraWidget(QtWidgets.QDialog):
#
#     def __init__(self, camera_idx):
#         QtWidgets.QDialog.__init__(self, flags=QtCore.Qt.WindowStaysOnTopHint)
#         self.camera_idx = camera_idx
#
#         self.setLayout(QtWidgets.QGridLayout())
#         self.setWindowTitle('Camera properties')
#
#         # Add fields
#         # Device ID
#         self.layout().addWidget(QtWidgets.QLabel('Device ID'), 0, 0)
#         self.device_id = QtWidgets.QLineEdit()
#         self.layout().addWidget(self.device_id, 0, 1)
#         # Manufacturer
#         self.layout().addWidget(QtWidgets.QLabel('Manufacturer'), 5, 0)
#         self.manufacturer = QtWidgets.QComboBox()
#         self.manufacturer.addItems([camdev.TISCamera.__name__,camdev.VirtualCamera.__name__])
#         self.manufacturer.currentTextChanged.connect(self.update_models)
#         self.layout().addWidget(self.manufacturer, 5, 1)
#         # Models
#         self.layout().addWidget(QtWidgets.QLabel('Model'), 10, 0)
#         self.model = QtWidgets.QComboBox()
#         self.model.currentTextChanged.connect(self.check_model)
#         self.model.currentTextChanged.connect(self.update_formats)
#         self.layout().addWidget(self.model, 10, 1)
#         # Formats
#         self.layout().addWidget(QtWidgets.QLabel('Format'), 15, 0)
#         self.vidformat = QtWidgets.QComboBox()
#         self.vidformat.currentTextChanged.connect(self.check_format)
#         self.layout().addWidget(self.vidformat, 15, 1)
#         # Exposure
#         self.layout().addWidget(QtWidgets.QLabel('Exposure [ms]'), 20, 0)
#         self.exposure = QtWidgets.QDoubleSpinBox()
#         self.exposure.setMinimum(0.001)
#         self.exposure.setMaximum(9999)
#         self.layout().addWidget(self.exposure, 20, 1)
#         # Exposure
#         self.layout().addWidget(QtWidgets.QLabel('Gain'), 25, 0)
#         self.gain = QtWidgets.QDoubleSpinBox()
#         self.gain.setMinimum(0.001)
#         self.gain.setMaximum(9999)
#         self.layout().addWidget(self.gain, 25, 1)
#
#
#         # Add buttons
#         self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel,
#                                              QtCore.Qt.Horizontal, self)
#         self.buttons.accepted.connect(self.check_fields)
#         self.buttons.rejected.connect(self.reject)
#
#         self.layout().addWidget(self.buttons, 50, 0, 1, 2)
#
#         self.update_fields()
#
#         self.show()
#
#     def update_models(self):
#         self.model.clear()
#
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#         select_models = section[definitions.CameraCfg.model]
#
#         avail_models = getattr(camdev,self.manufacturer.currentText()).get_models()
#
#         if self.camera_idx < len(select_models) and not(select_models[self.camera_idx] in avail_models):
#             avail_models.append(select_models[self.camera_idx])
#
#         self.model.addItems(avail_models)
#
#     def check_model(self, m):
#         if m in getattr(camdev,self.manufacturer.currentText()).get_models():
#             self.model.setStyleSheet('')
#         else:
#             self.model.setStyleSheet('QComboBox {color: red;}')
#
#     def update_formats(self):
#         self.vidformat.clear()
#
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#         select_formats = section[definitions.CameraCfg.format]
#
#         avail_formats = getattr(camdev,self.manufacturer.currentText()).get_formats(self.model.currentText())
#         if self.camera_idx < len(select_formats) and not(select_formats[self.camera_idx] in avail_formats):
#             avail_formats.append(select_formats[self.camera_idx])
#
#         self.vidformat.addItems(avail_formats)
#
#     def check_format(self, f):
#         if f in getattr(camdev,self.manufacturer.currentText()).get_formats(self.model.currentText()):
#             self.vidformat.setStyleSheet('')
#         else:
#             self.vidformat.setStyleSheet('QComboBox {color: red;}')
#
#     def update_fields(self):
#
#         section = acc.cur_conf.getParsedSection(definitions.CameraCfg.name)
#
#         # If this is a new camera (index not in range)
#         if self.camera_idx >= len(section[definitions.CameraCfg.device_id]):
#             # self.exposure.setValue(Default.Configuration[definitions.CameraCfg.name][definitions.CameraCfg.exposure])
#             # self.gain.setValue(Default.Configuration[definitions.CameraCfg.name][definitions.CameraCfg.gain])
#             return
#
#         # Set current value
#         # Device ID
#         self.device_id.setText(section[definitions.CameraCfg.device_id][self.camera_idx])
#         # Manufacturer
#         if self.manufacturer.currentText() != section[definitions.CameraCfg.manufacturer][self.camera_idx]:
#             self.manufacturer.setCurrentText(section[definitions.CameraCfg.manufacturer][self.camera_idx])
#         else:
#             # Manually emit to trigger consecutive list updates
#             self.manufacturer.currentTextChanged.emit(section[definitions.CameraCfg.manufacturer][self.camera_idx])
#         # Model
#         self.model.setCurrentText(section[definitions.CameraCfg.model][self.camera_idx])
#         # Format
#         self.vidformat.setCurrentText(section[definitions.CameraCfg.format][self.camera_idx])
#         # Exposure
#         self.exposure.setValue(section[definitions.CameraCfg.exposure][self.camera_idx])
#         # Gain
#         self.gain.setValue(section[definitions.CameraCfg.gain][self.camera_idx])
#
#     def check_fields(self):
#
#         data = dict()
#         data[definitions.CameraCfg.device_id] = self.device_id.text()
#         data[definitions.CameraCfg.manufacturer] = self.manufacturer.currentText()
#         data[definitions.CameraCfg.model] = self.model.currentText()
#         data[definitions.CameraCfg.format] = self.vidformat.currentText()
#         data[definitions.CameraCfg.exposure] = self.exposure.value()
#         data[definitions.CameraCfg.gain] = self.gain.value()
#
#         check = True
#         check &= bool(data[definitions.CameraCfg.device_id])
#         check &= bool(data[definitions.CameraCfg.manufacturer])
#         check &= bool(data[definitions.CameraCfg.model])
#         check &= bool(data[definitions.CameraCfg.format])
#         check &= not(data[definitions.CameraCfg.exposure] == 0.0)
#         check &= not(data[definitions.CameraCfg.gain] == 0.0)
#
#         ### Extract resolution from format
#         import re
#         s = re.search('\((.*?)x(.*?)\)', data[definitions.CameraCfg.format])
#         data[definitions.CameraCfg.res_x] = int(s.group(1))
#         data[definitions.CameraCfg.res_y] = int(s.group(2))
#
#         if check:
#             self.data = data
#             self.accept()
#         else:
#             print('Camera configuration faulty.')