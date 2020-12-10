"""
MappApp ./Startup.py - Startup script is used for creation and
modification of program configuration files.
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

import argparse
from configparser import ConfigParser
from inspect import isclass
import os
import sys
from typing import Union
import numpy as np
import pyqtgraph as pg

from PyQt5 import QtCore, QtWidgets

import Def
import Default
from helper import Basic
import process.Controller
from routines.__init__ import AbstractRoutine

import wres

current_config = Basic.ConfigParser()

import Logging
import Config
Logging.write = lambda *args, **kwargs: None

################################################################
################################
# MODULES

class ModuleWidget(QtWidgets.QWidget):

    def __init__(self, module_name, *_args, **_kwargs):
        QtWidgets.QWidget.__init__(self, *_args, **_kwargs)

        self.module_name = module_name

    def get_setting(self, option_name):
        global current_config
        return current_config.getParsed(self.module_name, option_name)

    def update_setting(self, option, value):
        global current_config
        current_config.setParsed(self.module_name, option, value)

    def closed_main_window(self):
        """Method called by default in MainWindow on closeEvent"""
        pass

    def load_settings_from_config(self):
        """Method called by default in MainWindow when selecting new configuration"""
        pass


################################
# CAMERA

from devices import Camera
class CameraWidget(ModuleWidget):

    def __init__(self, parent):
        ModuleWidget.__init__(self, Def.CameraCfg.name, parent=parent)
        self.setLayout(QtWidgets.QGridLayout())
        self.camera = None

        # Routine selection ComboBox
        self.avail_routine_list = QtWidgets.QComboBox()
        self.layout().addWidget(self.avail_routine_list, 0, 0)

        # Add new routine
        self.btn_add_routine = QtWidgets.QPushButton('Add routine')
        self.btn_add_routine.clicked.connect(self.add_routine)
        self.layout().addWidget(self.btn_add_routine, 0, 1)

        # Remove routine
        self.btn_remove_routine = QtWidgets.QPushButton('Remove')
        self.btn_remove_routine.clicked.connect(self.remove_routine)
        self.btn_remove_routine.setEnabled(False)
        self.layout().addWidget(self.btn_remove_routine, 0, 2)

        # Routine list
        self.used_routine_list = QtWidgets.QListWidget()
        self.used_routine_list.setMaximumWidth(400)
        self.used_routine_list.currentTextChanged.connect(self.toggle_routine_remove_btn)
        self.layout().addWidget(QtWidgets.QLabel('Routines'), 1, 0, 1, 3)
        self.layout().addWidget(self.used_routine_list, 2, 0, 1, 3)

        # Add new camera
        self.btn_add_cam = QtWidgets.QPushButton('Add camera')
        self.btn_add_cam.clicked.connect(self.add_camera)
        self.layout().addWidget(self.btn_add_cam, 0, 3)

        # Remove camera
        self.btn_remove_cam = QtWidgets.QPushButton('Remove')
        self.btn_remove_cam.clicked.connect(self.remove_camera)
        self.btn_remove_cam.setEnabled(False)
        self.layout().addWidget(self.btn_remove_cam, 0, 4)

        # Camera list
        self.camera_list = QtWidgets.QListWidget()
        self.camera_list.setMaximumWidth(200)
        self.camera_list.doubleClicked.connect(self.edit_camera)
        self.camera_list.clicked.connect(self.open_stream)
        self.camera_list.currentTextChanged.connect(self.toggle_cam_remove_btn)
        self.layout().addWidget(QtWidgets.QLabel('Devices'), 1, 3, 1, 2)
        self.layout().addWidget(self.camera_list, 2, 3, 1, 2)

        # Camera stream
        self.camera_stream = QtWidgets.QGroupBox('Camera stream')
        self.camera_stream.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.camera_stream, 0, 5, 3, 1)
        self.imview = pg.GraphicsView(parent=self)
        self.imitem = pg.ImageItem()
        self.imview.addItem(self.imitem)
        self.camera_stream.layout().addWidget(self.imview)

        self.stream_timer = QtCore.QTimer()
        self.stream_timer.setInterval(50)
        self.stream_timer.timeout.connect(self.update_stream)
        self.stream_timer.start()

    def load_settings_from_config(self):
        self.camera = self.res_x = self.res_y = None
        self.update_routine_list()
        self.update_camera_list()
        self.update_stream()

    def update_routine_list(self):
        global current_config

        self.avail_routine_list.clear()
        self.used_routine_list.clear()

        # Get routines listed in configuration
        used_routines = list()
        for fname, routines in current_config.getParsed(
                Def.CameraCfg.name,
                Def.CameraCfg.routines).items():
            for cname in routines:
                used_routines.append('{}.{}'.format(fname, cname))

        # Get all available routines for camera
        routine_path = Def.Path.Routines
        modules_list = list()
        for fname in os.listdir(os.path.join(routine_path,
                                             Def.CameraCfg.name.lower())):
            if fname.startswith('_') \
                or fname.startswith('.') \
                   or not(fname.endswith('.py')):
                continue

            modules_list.append(fname.replace('.py', ''))

        importpath = '.'.join([Def.Path.Routines,
                               Def.CameraCfg.name.lower()])

        modules = __import__(importpath, fromlist=modules_list)

        avail_routines = list()
        for fname in dir(modules):
            if fname.startswith('_'):
                continue

            file = getattr(modules, fname)

            for cname in dir(file):
                attr = getattr(file, cname)
                if not(isclass(attr))\
                        or not(issubclass(attr, AbstractRoutine)) \
                        or attr == AbstractRoutine:
                    continue

                avail_routines.append('.'.join([fname, cname]))

        # Calculate difference (available routines that are already used)
        unused_routines = list(set(avail_routines) - set(used_routines))

        self.avail_routine_list.addItems(unused_routines)

        self.used_routine_list.addItems(used_routines)

    def toggle_routine_remove_btn(self, p_str):
        self.btn_remove_routine.setEnabled(bool(p_str))

    def remove_routine(self):
        global current_config

        routines = current_config.getParsed(Def.CameraCfg.name, Def.CameraCfg.routines)

        rname = self.used_routine_list.currentItem().text()
        file_, class_ = rname.split('.')

        # Show confirmation dialog
        dialog = QtWidgets.QMessageBox()
        dialog.setIcon(QtWidgets.QMessageBox.Information)
        dialog.setText('Remove routine "{}"?'
                       .format(rname))
        dialog.setWindowTitle("Remove routine")
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok
                                  | QtWidgets.QMessageBox.Cancel)

        if not(dialog.exec() == QtWidgets.QMessageBox.Ok):
            return

        # Remove routine
        if file_ in routines and class_ in routines[file_]:
            del routines[file_][routines[file_].index(class_)]

        # If last routine from this file was remove, delete file key too
        if not(bool(routines[file_])):
            del routines[file_]

        current_config.setParsed(Def.CameraCfg.name,
                                 Def.CameraCfg.routines,
                                 routines)

        self.load_settings_from_config()

    def add_routine(self):
        rname = self.avail_routine_list.currentText()

        if not(bool(rname)):
            return

        global current_config

        file_, class_ = rname.split('.')

        # Get routines
        routines = current_config.getParsed(Def.CameraCfg.name,
                                            Def.CameraCfg.routines)

        # Add new routine
        if file_ not in routines:
            routines[file_] = []
        if class_ not in routines[file_]:
            routines[file_].append(class_)

        # Set routines
        current_config.setParsed(Def.CameraCfg.name,
                                 Def.CameraCfg.routines,
                                 routines)

        # Update GUI
        self.load_settings_from_config()

    def update_camera_list(self):
        global current_config

        self.camera_list.clear()
        self.camera_list.addItems(current_config.getParsed(Def.CameraCfg.name,
                                                           Def.CameraCfg.device_id))

    def toggle_cam_remove_btn(self, p_str):
        self.btn_remove_cam.setEnabled(bool(p_str))

    def remove_camera(self):
        global current_config
        device_id = self.camera_list.currentItem().text()
        section = current_config.getParsedSection(Def.CameraCfg.name)
        device_list = section[Def.CameraCfg.device_id]

        if not(device_id in device_list):
            return

        # Show confirmation dialog
        dialog = QtWidgets.QMessageBox()
        dialog.setIcon(QtWidgets.QMessageBox.Information)
        dialog.setText('Remove camera device "{}"?'
                       .format(device_id))
        dialog.setWindowTitle("Remove camera")
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok
                                  | QtWidgets.QMessageBox.Cancel)

        if not(dialog.exec() == QtWidgets.QMessageBox.Ok):
            return

        # Delete camera device from config
        idx = device_list.index(device_id)

        del device_list[idx]
        manufacturer = section[Def.CameraCfg.manufacturer]
        del manufacturer[idx]
        model = section[Def.CameraCfg.model]
        del model[idx]
        format_ = section[Def.CameraCfg.format]
        del format_[idx]
        res_x = section[Def.CameraCfg.res_x]
        del res_x[idx]
        res_y = section[Def.CameraCfg.res_y]
        del res_y[idx]
        gain = section[Def.CameraCfg.gain]
        del gain[idx]
        exposure = section[Def.CameraCfg.exposure]
        del exposure[idx]

        # Update config
        name = Def.CameraCfg.name
        current_config.setParsed(name, Def.CameraCfg.device_id, device_list)
        current_config.setParsed(name, Def.CameraCfg.manufacturer, manufacturer)
        current_config.setParsed(name, Def.CameraCfg.model, model)
        current_config.setParsed(name, Def.CameraCfg.format, format_)
        current_config.setParsed(name, Def.CameraCfg.res_x, res_x)
        current_config.setParsed(name, Def.CameraCfg.res_y, res_y)
        current_config.setParsed(name, Def.CameraCfg.gain, gain)
        current_config.setParsed(name, Def.CameraCfg.exposure, exposure)

        self.update_camera_list()

    def add_camera(self):
        row_idx = self.camera_list.count()

        self.edit_camera(row_idx)

    def edit_camera(self, idx: Union[int, QtCore.QModelIndex]):
        global current_config
        if isinstance(idx, QtCore.QModelIndex):
            row_idx = idx.row()
        else:
            row_idx = idx

        ### Open dialog
        dialog = EditCameraWidget(row_idx)
        if not(dialog.exec_() == QtWidgets.QDialog.Accepted):
            return

        ### Update configuration
        section = current_config.getParsedSection(Def.CameraCfg.name)
        ## Add new camera
        if row_idx >= len(section[Def.CameraCfg.device_id]):
            action = 'Add'
            for key, value in dialog.data.items():
                if not(key in section):
                    continue
                section[key].append(value)
        ## Update existing camera
        else:
            action = 'Update'
            for key, value in dialog.data.items():
                if not(key in section):
                    continue
                section[key][row_idx] = value

        print('{} camera {}: {}'.format(action,
                                        dialog.data[Def.CameraCfg.device_id],
                                        dialog.data))

        for key, value in section.items():
            current_config.setParsed(Def.CameraCfg.name, key, value)

        self.update_camera_list()

    def open_stream(self, idx: Union[int, QtCore.QModelIndex]):
        global current_config
        if isinstance(idx, QtCore.QModelIndex):
            row_idx = idx.row()
        else:
            row_idx = idx

        section = current_config.getParsedSection(Def.CameraCfg.name)

        if self.camera is not None:
            self.camera.stop()

        import devices.Camera
        try:
            cam = getattr(devices.Camera, section[Def.CameraCfg.manufacturer][row_idx])
            self.camera = cam(section[Def.CameraCfg.model][row_idx], section[Def.CameraCfg.format][row_idx])
            self.res_x, self.res_y = section[Def.CameraCfg.res_x][row_idx], section[Def.CameraCfg.res_y][row_idx]
            self.camera_stream.setMinimumWidth(section[Def.CameraCfg.res_y][row_idx]+30)
            gain = section[Def.CameraCfg.gain][row_idx]
            exposure = section[Def.CameraCfg.exposure][row_idx]
            print(gain, exposure)
            self.camera.set_gain(gain)
            self.camera.set_exposure(exposure)
            ### Provoke exception
            self.camera.snap_image()
            self.camera.get_image()
        except Exception as exc:
            print('Could not access device {}. Exception: {}'.format(section[Def.CameraCfg.device_id][row_idx], exc))
            import traceback
            print(traceback.print_exc())
            self.camera = self.res_x = self.res_y = None

    def update_stream(self):
        if self.camera is None:
            self.imitem.setImage(np.zeros((1,1)))
            return

        self.camera.snap_image()
        im = self.camera.get_image()
        im = im[:self.res_y, :self.res_x]
        self.imitem.setImage(im)

    def closed_main_window(self):
        if self.camera is not None:
            self.camera.stop()

class EditCameraWidget(QtWidgets.QDialog):

    def __init__(self, camera_idx):
        QtWidgets.QDialog.__init__(self, flags=QtCore.Qt.WindowStaysOnTopHint)
        self.camera_idx = camera_idx

        self.setLayout(QtWidgets.QGridLayout())
        self.setWindowTitle('Camera properties')

        # Add fields
        # Device ID
        self.layout().addWidget(QtWidgets.QLabel('Device ID'), 0, 0)
        self.device_id = QtWidgets.QLineEdit()
        self.layout().addWidget(self.device_id, 0, 1)
        # Manufacturer
        self.layout().addWidget(QtWidgets.QLabel('Manufacturer'), 5, 0)
        self.manufacturer = QtWidgets.QComboBox()
        self.manufacturer.addItems([Camera.TISCamera.__name__, Camera.VirtualCamera.__name__])
        self.manufacturer.currentTextChanged.connect(self.update_models)
        self.layout().addWidget(self.manufacturer, 5, 1)
        # Models
        self.layout().addWidget(QtWidgets.QLabel('Model'), 10, 0)
        self.model = QtWidgets.QComboBox()
        self.model.currentTextChanged.connect(self.check_model)
        self.model.currentTextChanged.connect(self.update_formats)
        self.layout().addWidget(self.model, 10, 1)
        # Formats
        self.layout().addWidget(QtWidgets.QLabel('Format'), 15, 0)
        self.vidformat = QtWidgets.QComboBox()
        self.vidformat.currentTextChanged.connect(self.check_format)
        self.layout().addWidget(self.vidformat, 15, 1)
        # Exposure
        self.layout().addWidget(QtWidgets.QLabel('Exposure [ms]'), 20, 0)
        self.exposure = QtWidgets.QDoubleSpinBox()
        self.exposure.setMinimum(0.001)
        self.exposure.setMaximum(9999)
        self.layout().addWidget(self.exposure, 20, 1)
        # Exposure
        self.layout().addWidget(QtWidgets.QLabel('Gain'), 25, 0)
        self.gain = QtWidgets.QDoubleSpinBox()
        self.gain.setMinimum(0.001)
        self.gain.setMaximum(9999)
        self.layout().addWidget(self.gain, 25, 1)


        # Add buttons
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel,
                                             QtCore.Qt.Horizontal, self)
        self.buttons.accepted.connect(self.check_fields)
        self.buttons.rejected.connect(self.reject)

        self.layout().addWidget(self.buttons, 50, 0, 1, 2)

        self.update_fields()

        self.show()

    def update_models(self):
        self.model.clear()

        global current_config
        section = current_config.getParsedSection(Def.CameraCfg.name)
        select_models = section[Def.CameraCfg.model]

        avail_models = getattr(Camera, self.manufacturer.currentText()).get_models()

        if self.camera_idx < len(select_models) and not(select_models[self.camera_idx] in avail_models):
            avail_models.append(select_models[self.camera_idx])

        self.model.addItems(avail_models)

    def check_model(self, m):
        if m in getattr(Camera, self.manufacturer.currentText()).get_models():
            self.model.setStyleSheet('')
        else:
            self.model.setStyleSheet('QComboBox {color: red;}')

    def update_formats(self):
        self.vidformat.clear()

        global current_config
        section = current_config.getParsedSection(Def.CameraCfg.name)
        select_formats = section[Def.CameraCfg.format]

        avail_formats = getattr(Camera, self.manufacturer.currentText()).get_formats(self.model.currentText())
        if self.camera_idx < len(select_formats) and not(select_formats[self.camera_idx] in avail_formats):
            avail_formats.append(select_formats[self.camera_idx])

        self.vidformat.addItems(avail_formats)

    def check_format(self, f):
        if f in getattr(Camera, self.manufacturer.currentText()).get_formats(self.model.currentText()):
            self.vidformat.setStyleSheet('')
        else:
            self.vidformat.setStyleSheet('QComboBox {color: red;}')

    def update_fields(self):
        global current_config
        section = current_config.getParsedSection(Def.CameraCfg.name)

        # If this is a new camera (index not in range)
        if self.camera_idx >= len(section[Def.CameraCfg.device_id]):
            self.exposure.setValue(Default.Configuration[Def.CameraCfg.name][Def.CameraCfg.exposure])
            self.gain.setValue(Default.Configuration[Def.CameraCfg.name][Def.CameraCfg.gain])
            return

        # Set current value
        # Device ID
        self.device_id.setText(section[Def.CameraCfg.device_id][self.camera_idx])
        # Manufacturer
        if self.manufacturer.currentText() != section[Def.CameraCfg.manufacturer][self.camera_idx]:
            self.manufacturer.setCurrentText(section[Def.CameraCfg.manufacturer][self.camera_idx])
        else:
            # Manually emit to trigger consecutive list updates
            self.manufacturer.currentTextChanged.emit(section[Def.CameraCfg.manufacturer][self.camera_idx])
        # Model
        self.model.setCurrentText(section[Def.CameraCfg.model][self.camera_idx])
        # Format
        self.vidformat.setCurrentText(section[Def.CameraCfg.format][self.camera_idx])
        # Exposure
        self.exposure.setValue(section[Def.CameraCfg.exposure][self.camera_idx])
        # Gain
        self.gain.setValue(section[Def.CameraCfg.gain][self.camera_idx])

    def check_fields(self):

        data = dict()
        data[Def.CameraCfg.device_id] = self.device_id.text()
        data[Def.CameraCfg.manufacturer] = self.manufacturer.currentText()
        data[Def.CameraCfg.model] = self.model.currentText()
        data[Def.CameraCfg.format] = self.vidformat.currentText()
        data[Def.CameraCfg.exposure] = self.exposure.value()
        data[Def.CameraCfg.gain] = self.gain.value()

        check = True
        check &= bool(data[Def.CameraCfg.device_id])
        check &= bool(data[Def.CameraCfg.manufacturer])
        check &= bool(data[Def.CameraCfg.model])
        check &= bool(data[Def.CameraCfg.format])
        check &= not(data[Def.CameraCfg.exposure] == 0.0)
        check &= not(data[Def.CameraCfg.gain] == 0.0)

        ### Extract resolution from format
        import re
        s = re.search('\((.*?)x(.*?)\)', data[Def.CameraCfg.format])
        data[Def.CameraCfg.res_x] = int(s.group(1))
        data[Def.CameraCfg.res_y] = int(s.group(2))

        if check:
            self.data = data
            self.accept()
        else:
            print('Camera configuration faulty.')



################################
# DISPLAY

from vispy import app, gloo

class Canvas(app.Canvas):

    def __init__(self, _interval, *args, **kwargs):
        app.Canvas.__init__(self, *args, **kwargs)
        self.tick = 0
        self.measure_fps(0.1, self.show_fps)
        self.visual = None
        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_clear_color((0.0, 0.0, 0.0, 1.0))

        self.timer = app.Timer(_interval, connect=self.on_timer, start=True)

        self.show()

    def on_draw(self, event):
        pass

    def on_timer(self, event):
        gloo.clear()
        if self.visual is not None:
            self.visual.draw(0.0)
        self.update()

    def show_fps(self, fps):
        pass
        #print("FPS {:.2f}".format(fps))

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)


class DisplayWidget(ModuleWidget):

    visual = None

    def __init__(self, parent):
        ModuleWidget.__init__(self, Def.DisplayCfg.name, parent=parent)
        global current_config

        app.use_app('pyqt5')

        # Create canvas
        self.canvas = Canvas(1/60)

        # Set timer for window updates
        self.tmr_glwindow = QtCore.QTimer()
        self.tmr_glwindow.setInterval(100)
        self.tmr_glwindow.timeout.connect(self.trigger_on_draw)
        self.tmr_glwindow.start()

        # Set layout
        self.setLayout(QtWidgets.QGridLayout())

        # Screen settings
        def button_reset():
            btn_reset_normal = QtWidgets.QPushButton('Reset to normal')
            btn_reset_normal.clicked.connect(self.canvas._native_window.showNormal)
            btn_reset_normal.clicked.connect(
                lambda: self.canvas._native_window.resize(512, 512))
            btn_reset_normal.clicked.connect(
                lambda: current_config.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.window_fullscreen, False))
            return btn_reset_normal

        self.fullscreen_select = QtWidgets.QGroupBox('Fullscreen selection')
        self.layout().addWidget(self.fullscreen_select, 0, 0, 1, 2)
        self.fullscreen_select.setLayout(QtWidgets.QGridLayout())
        #self.fullscreen_select.btn_reset_normal = button_reset()
        #self.fullscreen_select.layout().addWidget(self.fullscreen_select.btn_reset_normal, 0, 1)
        self.screen_settings = DisplayScreenSelection(self)
        self.fullscreen_select.layout().addWidget(self.screen_settings, 1, 0, 1, 2)

        self.calibration = DisplayCalibration(self)
        self.layout().addWidget(self.calibration, 0, 2)

        # Global settings
        self.global_settings = GlobalDisplaySettings(self)
        self.layout().addWidget(self.global_settings, 1, 0)

        # Spherical settings
        self.spherical_settings = SphericalDisplaySettings(self)
        self.layout().addWidget(self.spherical_settings, 1, 1)

        # Planar settings
        self.planar_settings = PlanarDisplaySettings(self)
        self.layout().addWidget(self.planar_settings, 1, 2)

    def trigger_on_draw(self):
        app.process_events()

    def load_settings_from_config(self):
        self.global_settings.load_settings_from_config()
        self.spherical_settings.load_settings_from_config()
        self.planar_settings.load_settings_from_config()
        self.update_window()

    def update_window(self):
        section = Def.DisplayCfg.name
        global current_config

        Config.Display = current_config.getParsedSection(Def.DisplayCfg.name)

        # Update size
        w, h = current_config.getParsed(section, Def.DisplayCfg.window_width), \
               current_config.getParsed(section, Def.DisplayCfg.window_height),
        self.canvas.size = (w, h)

        # Update position
        x, y = current_config.getParsed(section, Def.DisplayCfg.window_pos_x), \
               current_config.getParsed(section, Def.DisplayCfg.window_pos_y)
        self.canvas.position = (x, y)

    def closed_main_window(self):
        self.canvas.timer.stop()
        self.canvas.close()

    def on_draw(self, dt):

        if not(self.visual is None):
            self.visual.draw(0.0)


class DisplayScreenSelection(QtWidgets.QGroupBox):

    def __init__(self, parent: DisplayWidget):
        QtWidgets.QGroupBox.__init__(self, 'Fullscreen selection (double click)')
        self.main = parent

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.screens = list()
        self.screen_frames = list()
        for screen in winapp.screens():
            geo = screen.geometry()
            self.screens.append((geo.x(), geo.y(), geo.width(), geo.height()))

        self.screens_norm = self.screens

    def mouseDoubleClickEvent(self, *args, **kwargs):
        for i, (screen_norm, screen) in enumerate(zip(self.screens_norm, self.screens)):
            rect = QtCore.QRectF(*screen_norm)

            if rect.contains(QtCore.QPoint(args[0].x(), args[0].y())):

                print('Set display to fullscreen on screen {}'.format(i))
                global current_config, winapp

                self.main.global_settings.spn_win_x.setValue(screen[0])
                self.main.global_settings.spn_win_y.setValue(screen[1])
                self.main.global_settings.spn_win_width.setValue(screen[2])
                self.main.global_settings.spn_win_height.setValue(screen[3])


                # Update window settings
                #self.main.global_settings.spn_win_x.setValue(screen[0])
                #self.main.global_settings.spn_win_y.setValue(screen[1])
                #self.main.global_settings.spn_win_width.setValue(screen[2])
                #self.main.global_settings.spn_win_height.setValue(screen[3])
                winapp.processEvents()

                # Set fullscreen
                self.main.canvas.fullscreen = True
                #scr_handle = self.main.canvas.screens()[i]
                #self.main.canvas._native_window.windowHandle().setScreen(scr_handle)
                #self.main.canvas._native_window.showFullScreen()

                current_config.setParsed(Def.DisplayCfg.name, Def.DisplayCfg.window_fullscreen, True)


    def paintEvent(self, QPaintEvent):
        if len(self.screens) == 0:
            return

        global winapp
        from PyQt5.QtGui import QPainter, QColor, QFont

        screens = np.array(self.screens).astype(np.float32)
        ### Norm position
        ## x
        xmax = screens[:,2].sum()
        ymax = screens[:,3].sum()
        usemax = max(xmax, ymax)
        screens[:,0] -= screens[:,0].min()
        screens[:,0] = screens[:,0] / usemax
        screens[:,0] *= self.size().width()
        ## y
        screens[:,1] -= screens[:,1].min()
        screens[:,1] = screens[:,1] / usemax
        screens[:,1] *= self.size().height()
        ## Norm width/height
        screens[:,2] = screens[:,2] / usemax * self.size().width()
        screens[:,3] = screens[:,3] / usemax * self.size().height()

        screens = screens.astype(int)

        self.screens_norm = screens

        self.painter = QPainter()
        for i, screen in enumerate(screens):

            rect = QtCore.QRect(*screen)

            self.painter.begin(self)

            self.painter.setBrush(QtCore.Qt.Dense4Pattern)
            self.painter.drawRect(rect)

            self.painter.setPen(QColor(168, 34, 3))
            self.painter.setFont(QFont('Decorative', 30))
            self.painter.drawText(rect, QtCore.Qt.AlignCenter, str(i))

            self.painter.end()


class DisplayCalibration(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Display calibration')
        self.main = parent

        self.setLayout(QtWidgets.QVBoxLayout())

        ### Planar checkerboard
        self.grp_pla_checker = QtWidgets.QGroupBox('Planar Checkerboard')
        self.grp_pla_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_pla_checker)
        ## Rows
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. rows [1/mm]'), 0, 0)
        self.grp_pla_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_rows.setValue(5)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_rows, 0, 1)
        ## Cols
        self.grp_pla_checker.layout().addWidget(QtWidgets.QLabel('Num. cols [1/mm]'), 1, 0)
        self.grp_pla_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_pla_checker.dspn_cols.setValue(5)
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.dspn_cols, 1, 1)
        ## Show button
        self.grp_pla_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_pla_checker.btn_show.clicked.connect(
            lambda: self.show_planar_checkerboard(self.grp_pla_checker.dspn_rows.value(),
                                                  self.grp_pla_checker.dspn_cols.value())
        )
        self.grp_pla_checker.layout().addWidget(self.grp_pla_checker.btn_show, 2, 0, 1, 2)

        ### Spherical checkerboard
        self.grp_sph_checker = QtWidgets.QGroupBox('Spherical Checkerboard')
        self.grp_sph_checker.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.grp_sph_checker)
        ## Rows
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. rows'), 0, 0)
        self.grp_sph_checker.dspn_rows = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_rows.setValue(5)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_rows, 0, 1)
        ## Cols
        self.grp_sph_checker.layout().addWidget(QtWidgets.QLabel('Num. cols'), 1, 0)
        self.grp_sph_checker.dspn_cols = QtWidgets.QSpinBox()
        self.grp_sph_checker.dspn_cols.setValue(5)
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.dspn_cols, 1, 1)
        ## Show button
        self.grp_sph_checker.btn_show = QtWidgets.QPushButton('Show')
        self.grp_sph_checker.btn_show.clicked.connect(
            lambda: self.show_spherical_checkerboard(self.grp_sph_checker.dspn_rows.value(),
                                                     self.grp_sph_checker.dspn_cols.value())
        )
        self.grp_sph_checker.layout().addWidget(self.grp_sph_checker.btn_show, 2, 0, 1, 2)

        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout().addItem(vSpacer)

    def show_planar_checkerboard(self, rows, cols):
        from Protocol import StaticProtocol
        from visuals.planar.Calibration import Checkerboard
        protocol = StaticProtocol(None)
        self.main.canvas.visual = Checkerboard(self.main.canvas, **{Checkerboard.u_rows : rows,
                                                             Checkerboard.u_cols : cols})


    def show_spherical_checkerboard(self, rows, cols):
        from Protocol import StaticProtocol
        from visuals.spherical.Calibration import BlackWhiteCheckerboard
        protocol = StaticProtocol(None)
        self.main.canvas.visual = BlackWhiteCheckerboard(self.main.canvas,
                                                  **{BlackWhiteCheckerboard.u_rows : rows,
                                                     BlackWhiteCheckerboard.u_cols : cols})



class GlobalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Global')
        self.main = parent

        global current_config

        ### Set layout
        self.setLayout(QtWidgets.QGridLayout())

        # Window x pos
        self.layout().addWidget(QtWidgets.QLabel('Window x-Position'), 0, 0)
        self.spn_win_x = QtWidgets.QSpinBox()
        self.spn_win_x.setMinimum(-9999)
        self.spn_win_x.setMaximum(9999)
        self.spn_win_x.setSingleStep(1)
        self.spn_win_x.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_pos_x,
                                                                             self.spn_win_x.value()))
        self.spn_win_x.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.spn_win_x, 0, 1)

        # Window y pos
        self.layout().addWidget(QtWidgets.QLabel('Window y-Position'), 1, 0)
        self.spn_win_y = QtWidgets.QSpinBox()
        self.spn_win_y.setMinimum(-9999)
        self.spn_win_y.setMaximum(9999)
        self.spn_win_y.setSingleStep(1)
        self.spn_win_y.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_pos_y,
                                                                             self.spn_win_y.value()))
        self.spn_win_y.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.spn_win_y, 1, 1)

        # Window width
        self.layout().addWidget(QtWidgets.QLabel('Window width'), 20, 0)
        self.spn_win_width = QtWidgets.QSpinBox()
        self.spn_win_width.setMinimum(1)
        self.spn_win_width.setMaximum(9999)
        self.spn_win_width.setSingleStep(1)
        self.spn_win_width.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_width,
                                                                             self.spn_win_width.value()))
        self.spn_win_width.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.spn_win_width, 20, 1)

        # Window height
        self.layout().addWidget(QtWidgets.QLabel('Window height'), 21, 0)
        self.spn_win_height = QtWidgets.QSpinBox()
        self.spn_win_height.setMinimum(1)
        self.spn_win_height.setMaximum(9999)
        self.spn_win_height.setSingleStep(1)
        self.spn_win_height.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.window_height,
                                                                             self.spn_win_height.value()))
        self.spn_win_height.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.spn_win_height, 21, 1)

        self.btn_use_current_window = QtWidgets.QPushButton('Use current window settings')
        self.btn_use_current_window.clicked.connect(self.use_current_window_settings)
        self.layout().addWidget(self.btn_use_current_window, 25, 0, 1, 2)

        # X Position
        self.layout().addWidget(QtWidgets.QLabel('X-position'), 40, 0)
        self.dspn_x_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_x_pos.setDecimals(3)
        self.dspn_x_pos.setMinimum(-1.0)
        self.dspn_x_pos.setMaximum(1.0)
        self.dspn_x_pos.setSingleStep(.001)
        self.dspn_x_pos.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.glob_x_pos,
                                                                             self.dspn_x_pos.value()))
        self.dspn_x_pos.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.dspn_x_pos, 40, 1)

        # Y position
        self.layout().addWidget(QtWidgets.QLabel('Y-position'), 50, 0)
        self.dspn_y_pos = QtWidgets.QDoubleSpinBox()
        self.dspn_y_pos.setDecimals(3)
        self.dspn_y_pos.setMinimum(-1.0)
        self.dspn_y_pos.setMaximum(1.0)
        self.dspn_y_pos.setSingleStep(.001)
        self.dspn_y_pos.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.glob_y_pos,
                                                                             self.dspn_y_pos.value()))
        self.dspn_y_pos.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(self.dspn_y_pos, 50, 1)


    def use_current_window_settings(self):

        geo = self.main.canvas._native_window.geometry()
        fgeo = self.main.canvas._native_window.frameGeometry()

        self.spn_win_width.setValue(geo.width())
        self.spn_win_height.setValue(geo.height())

        self.spn_win_x.setValue(fgeo.x())
        self.spn_win_y.setValue(fgeo.y())

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name
        global current_config

        self.spn_win_x.setValue(current_config.getParsed(section, Def.DisplayCfg.window_pos_x))
        self.spn_win_y.setValue(current_config.getParsed(section, Def.DisplayCfg.window_pos_y))
        self.spn_win_width.setValue(current_config.getParsed(section, Def.DisplayCfg.window_width))
        self.spn_win_height.setValue(current_config.getParsed(section, Def.DisplayCfg.window_height))
        self.dspn_x_pos.setValue(current_config.getParsed(section, Def.DisplayCfg.glob_x_pos))
        self.dspn_y_pos.setValue(current_config.getParsed(section, Def.DisplayCfg.glob_y_pos))


class SphericalDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Spherical')
        self.main = parent

        ## Setup widget
        self.setLayout(QtWidgets.QGridLayout())

        ## Radial position (distance from center)
        self.dspn_radial_offset = QtWidgets.QDoubleSpinBox()
        self.dspn_radial_offset.setDecimals(3)
        self.dspn_radial_offset.setMinimum(-1.0)
        self.dspn_radial_offset.setMaximum(1.0)
        self.dspn_radial_offset.setSingleStep(.001)
        self.dspn_radial_offset.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_pos_glob_radial_offset,
                                                                             self.dspn_radial_offset.value()))
        self.dspn_radial_offset.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Radial offset'), 0, 0)
        self.layout().addWidget(self.dspn_radial_offset, 0, 1)

        # Elevation
        self.dspn_view_elev_angle = QtWidgets.QDoubleSpinBox()
        self.dspn_view_elev_angle.setDecimals(1)
        self.dspn_view_elev_angle.setSingleStep(0.1)
        self.dspn_view_elev_angle.setMinimum(-90.0)
        self.dspn_view_elev_angle.setMaximum(90.0)
        self.dspn_view_elev_angle.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_elev_angle,
                                                                             self.dspn_view_elev_angle.value()))
        self.dspn_view_elev_angle.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Elevation [deg]'), 5, 0)
        self.layout().addWidget(self.dspn_view_elev_angle, 5, 1)

        # Azimuth
        self.dspn_view_azim_angle = QtWidgets.QDoubleSpinBox()
        self.dspn_view_azim_angle.setDecimals(1)
        self.dspn_view_azim_angle.setSingleStep(0.1)
        self.dspn_view_azim_angle.setMinimum(-90.0)
        self.dspn_view_azim_angle.setMaximum(90.0)
        self.dspn_view_azim_angle.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_azim_angle,
                                                                             self.dspn_view_azim_angle.value()))
        self.dspn_view_azim_angle.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Azimuth [deg]'), 10, 0)
        self.layout().addWidget(self.dspn_view_azim_angle, 10, 1)

        # View distance(from origin of sphere)
        self.dspn_view_distance = QtWidgets.QDoubleSpinBox()
        self.dspn_view_distance.setDecimals(1)
        self.dspn_view_distance.setSingleStep(.1)
        self.dspn_view_distance.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_distance,
                                                                             self.dspn_view_distance.value()))
        self.dspn_view_distance.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Distance [a.u.]'), 15, 0)
        self.layout().addWidget(self.dspn_view_distance, 15, 1)

        # View scale
        self.dspn_view_fov = QtWidgets.QDoubleSpinBox()
        self.dspn_view_fov.setDecimals(1)
        self.dspn_view_fov.setMinimum(1)
        self.dspn_view_fov.setMaximum(360)
        self.dspn_view_fov.setSingleStep(0.1)
        self.dspn_view_fov.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                                   Def.DisplayCfg.sph_view_fov,
                                                                                   self.dspn_view_fov.value()))
        self.dspn_view_fov.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('FOV [deg]'), 17, 0)
        self.layout().addWidget(self.dspn_view_fov, 17, 1)

        # View scale
        self.dspn_view_scale = QtWidgets.QDoubleSpinBox()
        self.dspn_view_scale.setDecimals(3)
        self.dspn_view_scale.setSingleStep(0.001)
        self.dspn_view_scale.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.sph_view_scale,
                                                                             self.dspn_view_scale.value()))
        self.dspn_view_scale.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Scale [a.u.]'), 20, 0)
        self.layout().addWidget(self.dspn_view_scale, 20, 1)

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name
        global current_config

        self.dspn_radial_offset.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_pos_glob_radial_offset))
        self.dspn_view_elev_angle.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_elev_angle))
        self.dspn_view_azim_angle.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_azim_angle))
        self.dspn_view_distance.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_distance))
        self.dspn_view_fov.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_fov))
        self.dspn_view_scale.setValue(current_config.getParsed(section, Def.DisplayCfg.sph_view_scale))


class PlanarDisplaySettings(QtWidgets.QGroupBox):

    def __init__(self, parent):
        QtWidgets.QGroupBox.__init__(self, 'Planar')
        self.main = parent

        self.setLayout(QtWidgets.QGridLayout())

        # X extent
        self.dspn_x_extent = QtWidgets.QDoubleSpinBox()
        self.dspn_x_extent.setDecimals(3)
        self.dspn_x_extent.setMinimum(0.0)
        self.dspn_x_extent.setSingleStep(.001)
        self.dspn_x_extent.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_xextent,
                                                                             self.dspn_x_extent.value()))
        self.dspn_x_extent.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('X-Extent [rel]'), 0, 0)
        self.layout().addWidget(self.dspn_x_extent, 0, 1)
        # Y extent
        self.dspn_y_extent = QtWidgets.QDoubleSpinBox()
        self.dspn_y_extent.setDecimals(3)
        self.dspn_y_extent.setMinimum(0.0)
        self.dspn_y_extent.setSingleStep(.001)
        self.dspn_y_extent.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_yextent,
                                                                             self.dspn_y_extent.value()))
        self.dspn_y_extent.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Y-Extent [rel]'), 1, 0)
        self.layout().addWidget(self.dspn_y_extent, 1, 1)
        # Small side dimensions
        self.dspn_small_side = QtWidgets.QDoubleSpinBox()
        self.dspn_small_side.setDecimals(3)
        self.dspn_small_side.setSingleStep(.001)
        self.dspn_small_side.valueChanged.connect(lambda: current_config.setParsed(Def.DisplayCfg.name,
                                                                             Def.DisplayCfg.pla_small_side,
                                                                             self.dspn_small_side.value()))
        self.dspn_small_side.valueChanged.connect(self.main.update_window)
        self.layout().addWidget(QtWidgets.QLabel('Small side [mm]'), 2, 0)
        self.layout().addWidget(self.dspn_small_side, 2, 1)

    def load_settings_from_config(self):
        section = Def.DisplayCfg.name
        global current_config

        self.dspn_x_extent.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_xextent))
        self.dspn_y_extent.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_yextent))
        self.dspn_small_side.setValue(current_config.getParsed(section, Def.DisplayCfg.pla_small_side))


################################################################
################################
### STARTUP MAIN WINDOW

class ModuleCheckbox(QtWidgets.QCheckBox):

    def __init__(self, module_name, *_args):
        QtWidgets.QCheckBox.__init__(self, module_name.upper(), *_args)
        self.module_name = module_name

        self.toggled.connect(self.react_to_toggle)

    def react_to_toggle(self, bool):
        print('Set module \"{}\" usage to {}'.format(self.text(), bool))
        global current_config
        current_config.setParsed(self.module_name, Def.Cfg.use, bool)



class StartupConfiguration(QtWidgets.QMainWindow):

    _availModules = {Def.CameraCfg.name  : CameraWidget,
                     Def.DisplayCfg.name : DisplayWidget,
                     Def.GuiCfg.name     : ModuleWidget,
                     Def.IoCfg.name      : ModuleWidget,
                     Def.RecCfg.name     : ModuleWidget}

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.setWindowTitle('MappApp - Startup configuration')

        self._configfile = None
        self._currentConfigChanged = False

        self.setup_ui()


    def setup_ui(self):
        global current_config
        vSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        hSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        ## Setup window
        self.resize(1200, 1000)

        ## Set central widget
        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        ########
        ### Config file selection
        self.gb_select = QtWidgets.QGroupBox('Select config file...')
        self.gb_select.setLayout(QtWidgets.QHBoxLayout())
        self.centralWidget().layout().addWidget(self.gb_select)

        # Selection
        self.gb_select.layout().addWidget(QtWidgets.QLabel('Select configuration file: '))
        self.gb_select.cb_select = QtWidgets.QComboBox()
        self.gb_select.cb_select.currentTextChanged.connect(self.open_configfile)
        self.gb_select.layout().addWidget(self.gb_select.cb_select)
        # New
        self.gb_select.btn_new = QtWidgets.QPushButton('Add new...')
        self.gb_select.btn_new.clicked.connect(self._add_configfile)
        self.gb_select.layout().addWidget(self.gb_select.btn_new)
        # Use
        self.gb_select.btn_use = QtWidgets.QPushButton('Use')
        self.gb_select.btn_use.clicked.connect(self.start_application)
        self.gb_select.layout().addWidget(self.gb_select.btn_use)


        ########
        ### Change configurations for current file
        self.gb_edit = QtWidgets.QGroupBox('Change config')
        self.gb_edit.setLayout(QtWidgets.QGridLayout())
        self.centralWidget().layout().addWidget(self.gb_edit)

        ####
        ### Module selection
        self.gb_edit.gb_select_mod = QtWidgets.QGroupBox('Select modules')
        self.gb_edit.gb_select_mod.setMaximumWidth(200)
        self.gb_edit.gb_select_mod.setLayout(QtWidgets.QVBoxLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.gb_select_mod, 0, 0)

        ## Set configs widget
        self.gb_edit.tab_modules = QtWidgets.QTabWidget(self)
        self.gb_edit.tab_modules.setLayout(QtWidgets.QGridLayout())
        self.gb_edit.layout().addWidget(self.gb_edit.tab_modules, 0, 1, 1, 2)
        #self.gb_edit.layout().addItem(hSpacer, 1, 1, 1, 2)

        ### Add all available modules
        self.module_checkboxes = dict()
        self.module_widgets = dict()
        for name, widget in self._availModules.items():

            cb = ModuleCheckbox(name)
            cb.setChecked(False)
            self.module_checkboxes[name] = cb
            self.gb_edit.gb_select_mod.layout().addWidget(self.module_checkboxes[name])

            if widget.__name__ == 'ModuleWidget':
                wdgt = widget(name, self)
            else:
                wdgt = widget(self)


            self.module_widgets[name] = wdgt
            self.gb_edit.tab_modules.addTab(self.module_widgets[name], name.upper())

        ### Spacer
        self.gb_edit.gb_select_mod.layout().addItem(vSpacer)

        self.btn_save_config = QtWidgets.QPushButton('Save changes')
        self.btn_save_config.clicked.connect(current_config.saveToFile)
        self.gb_edit.layout().addWidget(self.btn_save_config, 1, 1)

        self.btn_start_app = QtWidgets.QPushButton('Save and start')
        self.btn_start_app.clicked.connect(self.save_and_start_application)
        self.gb_edit.layout().addWidget(self.btn_start_app, 1, 2)

        # Update and show
        self.update_configfile_list()
        self.show()

    def update_configfile_list(self):
        self.gb_select.cb_select.clear()
        for fname in os.listdir(Def.Path.Config):
            self.gb_select.cb_select.addItem(fname[:-4])

    def _add_configfile(self):
        name, confirmed = QtWidgets.QInputDialog.getText(self, 'Create new configs file', 'Config name', QtWidgets.QLineEdit.Normal, '')

        if confirmed and name != '':
            if name[-4:] != '.ini':
                fname = '%s.ini' % name
            else:
                fname = name
                name = name[:-4]

            if fname not in os.listdir(Def.Path.Config):
                with open(os.path.join(Def.Path.Config, fname), 'w') as fobj:
                    parser = ConfigParser()
                    parser.write(fobj)
            self.update_configfile_list()
            self.gb_select.cb_select.setCurrentText(name)


    def open_configfile(self):

        name = self.gb_select.cb_select.currentText()

        if name == '':
            return

        print('Open config {}'.format(name))
        global current_config

        self._configfile = '{}.ini'.format(name)
        current_config.read(self._configfile)

        ### Set display config for visual compat.
        Config.Display = current_config.getParsedSection(Def.DisplayCfg.name)

        ### Update module selection
        for module_name, checkbox in self.module_checkboxes.items():
            use = current_config.getParsed(module_name, Def.Cfg.use)
            checkbox.setChecked(use)
            self.module_widgets[module_name].setEnabled(use)

        ### Update module settings
        for module_name, wdgt in self.module_widgets.items():
            if hasattr(wdgt, 'load_settings_from_config'):
                print('Load settings for module \"{}\" from config file'.format(module_name))
                wdgt.load_settings_from_config()
            else:
                print('Could not load settings for module \"{}\" from config file'.format(module_name))


    def closeEvent(self, event):
        answer = None
        if self._currentConfigChanged:
            answer = QtWidgets.QMessageBox.question(self, 'Unsaved changes', 'Would you like to save the current changes?',
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel ,
                                           QtWidgets.QMessageBox.No)
            if answer == QtWidgets.QMessageBox.Yes and not(self.configuration is None):
                global current_config
                current_config.saveToFile()

        ### Close widgetts
        for wdgt_name, wdgt in self.module_widgets.items():
            wdgt.closed_main_window()

        ### Close MainWindow
        event.accept()

    def save_and_start_application(self):
        global current_config
        current_config.saveToFile()
        self.start_application()

    def start_application(self):
        print('Start application')
        global configfile
        configfile = self._configfile
        self.close()


if __name__ == '__main__':

    from sys import platform


    if platform == 'win32':

        ### Set windows timer precision as high as possible
        minres, maxres, curres = wres.query_resolution()
        with wres.set_resolution(maxres):

            skip_setup = False

            parser = argparse.ArgumentParser()
            parser.add_argument('--ini', action='store', dest='ini_file', type=str)
            args = parser.parse_args(sys.argv[1:])

            if not(args.ini_file is None):
                process.Controller.configfile = args.ini_file
                skip_setup = True

            if skip_setup:
                ctrl = process.Controller()

            else:

                configfile = None
                winapp = QtWidgets.QApplication([])
                startupwin = StartupConfiguration()
                winapp.exec_()

                if configfile is None:
                    exit()

                import process.Controller
                process.Controller.configfile = configfile
                ctrl = process.Controller()
    else:
        print('Sorry, probably not gonna work on \"{}\"'.format(platform))


