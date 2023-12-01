"""Camera capture plugin for reading camera frames from devices and
displaying them in the UI
"""
from __future__ import annotations
from typing import Dict, List

import cv2
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets

from vxpy import config
import vxpy.core.attribute as vxattribute
import vxpy.core.devices.camera as vxcamera
import vxpy.core.routine as vxroutine
import vxpy.core.ui as vxgui
from vxpy.utils.widgets import IntSliderWidget, UniformWidth, Checkbox


class Frames(vxroutine.CameraRoutine):
    device_list: List[vxcamera.CameraDevice] = []
    frame_postfix = '_frame'

    flip_ud: Dict[str, bool] = {}
    flip_lr: Dict[str, bool] = {}
    rotation: Dict[str, int] = {}

    def __init__(self, *args, **kwargs):
        vxroutine.CameraRoutine.__init__(self, *args, **kwargs)

    def require(self):
        # Fetch all cameras by device_id and append to list
        for device_id in config.CAMERA_DEVICES:
            self.device_list.append(vxcamera.get_camera_by_id(device_id))
            self.flip_ud[device_id] = False
            self.flip_lr[device_id] = False
            self.rotation[device_id] = 0

        # Set one array attribute per camera device
        for device in self.device_list:
            vxattribute.ArrayAttribute(f'{device.device_id}{self.frame_postfix}',
                                       (device.width, device.height), vxattribute.ArrayType.uint8)

    def initialize(self):
        # Add all frame attributes to candidate list for save to disk
        for device in self.device_list:
            vxattribute.get_attribute(f'{device.device_id}{self.frame_postfix}').add_to_file()

    def main(self, **frames):

        for device_id, frame_data in frames.items():

            if frame_data is None:
                continue

            # Fetch attribute object
            frame_attr = vxattribute.get_attribute(f'{device_id}{self.frame_postfix}')

            # Update shared attributes
            if frame_data.ndim > 2:
                frame = frame_data[:, :, 0].T
            else:
                frame = frame_data[:, :].T

            # Transform
            if self.flip_lr[device_id]:
                frame = np.fliplr(frame)
            if self.flip_ud[device_id]:
                frame = np.flipud(frame)

            rot_angle = self.rotation[device_id]
            if 0 < rot_angle < 360:
                rot_mat = cv2.getRotationMatrix2D((frame.shape[1] / 2, frame.shape[0] / 2), rot_angle, 1.0)
                frame = cv2.warpAffine(frame, rot_mat, frame.shape[::-1], flags=cv2.INTER_LINEAR)

            # Write
            frame_attr.write(frame)


class FrameUI(vxgui.CameraAddonWidget):

    display_name = 'Cameras'

    def __init__(self, *args, **kwargs):
        vxgui.CameraAddonWidget.__init__(self, *args, **kwargs)

        self.central_widget.setLayout(QtWidgets.QHBoxLayout())

        # Add tab widget
        self.tab_camera_views = QtWidgets.QTabWidget()
        self.central_widget.layout().addWidget(self.tab_camera_views)

        # Add one view per camera device
        self.view_wdgts = {}
        for device_id in config.CAMERA_DEVICES:
            self.view_wdgts[device_id] = CameraWidget(self, device_id, parent=self)
            self.tab_camera_views.addTab(self.view_wdgts[device_id], device_id.upper())

        self.connect_to_timer(self.update_frame)

    def update_frame(self):
        for widget in self.view_wdgts.values():
            widget.update_frame()


class CameraWidget(QtWidgets.QWidget):
    def __init__(self, main, device_id, **kwargs):
        QtWidgets.QWidget.__init__(self, **kwargs)
        self.main = main
        self.device_id = device_id

        # Set layout
        self.setLayout(QtWidgets.QHBoxLayout())

        self.settings = QtWidgets.QGroupBox('Frame settings')
        self.settings.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum,
                                    QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.settings.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.settings)

        self.label_width = UniformWidth()

        # Add Rotate/flip controls
        self.rotation = IntSliderWidget(self, label='Rotation [° CCW]', label_width=self.label_width,
                                        default=0, limits=(0, 360))
        self.rotation.connect_callback(self.set_rotation)
        self.settings.layout().addWidget(self.rotation)
        self.check_flip_ud = Checkbox(self, 'Flip vertical', label_width=self.label_width,
                                      default=Frames.instance().flip_ud[self.device_id])
        self.check_flip_ud.connect_callback(self.set_flip_ud)
        self.settings.layout().addWidget(self.check_flip_ud)
        self.check_flip_lr = Checkbox(self, 'Flip horizontal', label_width=self.label_width,
                                      default=Frames.instance().flip_lr[self.device_id])
        self.check_flip_lr.connect_callback(self.set_flip_lr)
        self.settings.layout().addWidget(self.check_flip_lr)

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.settings.layout().addItem(spacer)

        # Add graphics widget
        self.graphics_widget = GraphicsWidget(self.main, parent=self)
        self.layout().addWidget(self.graphics_widget)

    def update_frame(self):
        idx, time, frame = vxattribute.read_attribute(f'{self.device_id}_frame')

        if frame is None:
            return

        self.graphics_widget.image_item.setImage(frame.squeeze())

    def set_rotation(self, value):
        Frames.instance().rotation[self.device_id] = value

    def set_flip_ud(self, value):
        Frames.instance().flip_ud[self.device_id] = value

    def set_flip_lr(self, value):
        Frames.instance().flip_lr[self.device_id] = value


class GraphicsWidget(pg.GraphicsLayoutWidget):

    def __init__(self, main, **kwargs):
        pg.GraphicsLayoutWidget.__init__(self, **kwargs)

        # Add plot
        self.image_plot = self.addPlot(0, 0)

        # Set up plot image item
        self.image_item = pg.ImageItem()
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)
        self.image_plot.addItem(self.image_item)
