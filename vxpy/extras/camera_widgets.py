"""
vxPy ./addons/frames_widgets.py
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
import numpy as np
from PySide6 import QtWidgets
import pyqtgraph as pg

from vxpy import config
import vxpy.core.ui as vxgui
import vxpy.core.attribute as vxattribute


class CameraStreamAddon(vxgui.CameraAddonWidget):

    display_name = 'Cameras'

    def __init__(self, *args, **kwargs):
        vxgui.CameraAddonWidget.__init__(self, *args, **kwargs)

        self.central_widget.setLayout(QtWidgets.QHBoxLayout())

        # Add tab widget
        self.tab_camera_views = QtWidgets.QTabWidget()
        self.tab_camera_views.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
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
        self.setLayout(QtWidgets.QVBoxLayout())

        self.ctrl_panel = QtWidgets.QWidget()
        self.ctrl_panel.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Maximum)
        self.ctrl_panel.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.ctrl_panel)

        # Add Rotate/flip controls
        self._rotation = 0
        self.cb_rotation = QtWidgets.QComboBox()
        self.ctrl_panel.layout().addWidget(QtWidgets.QLabel('Rotation'))
        self.cb_rotation.addItems(['None', '90CCW', '180', '270CCW'])
        self.cb_rotation.currentIndexChanged.connect(lambda i: self.set_rotation(i))
        self.cb_rotation.currentIndexChanged.connect(self.update_frame)
        self.ctrl_panel.layout().addWidget(self.cb_rotation)
        self._flip_ud = False
        self.check_flip_ud = QtWidgets.QCheckBox('Flip vertical')
        self.check_flip_ud.stateChanged.connect(lambda s: self.set_flip_ud(s))
        self.check_flip_ud.stateChanged.connect(self.update_frame)
        self.ctrl_panel.layout().addWidget(self.check_flip_ud)
        self._flip_lr = False
        self.check_flip_lr = QtWidgets.QCheckBox('Flip horizontal')
        self.check_flip_lr.stateChanged.connect(lambda s: self.set_flip_lr(s))
        self.check_flip_lr.stateChanged.connect(self.update_frame)
        self.ctrl_panel.layout().addWidget(self.check_flip_lr)
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.ctrl_panel.layout().addItem(spacer)

        # Add graphics widget
        self.graphics_widget = GraphicsWidget(self.main, parent=self)
        self.layout().addWidget(self.graphics_widget)

    def update_frame(self):
        idx, time, frame = vxattribute.read_attribute(f'{self.device_id}_frame')

        if frame is None:
            return

        frame = np.rot90(frame.squeeze(), self._rotation)
        if self._flip_lr:
            frame = np.fliplr(frame)
        if self._flip_ud:
            frame = np.flipud(frame)

        self.graphics_widget.image_item.setImage(frame)

    def set_rotation(self, dir):
        self._rotation = dir

    def set_flip_ud(self, flip):
        self._flip_ud = flip

    def set_flip_lr(self, flip):
        self._flip_lr = flip


class GraphicsWidget(pg.GraphicsLayoutWidget):

    def __init__(self, main, **kwargs):
        pg.GraphicsLayoutWidget.__init__(self, **kwargs)

        # Add plot
        self.image_plot = self.addPlot(0, 0, 1, 10)

        # Set up plot image item
        self.image_item = pg.ImageItem()
        self.image_plot.invertY(True)
        self.image_plot.hideAxis('left')
        self.image_plot.hideAxis('bottom')
        self.image_plot.setAspectLocked(True)
        self.image_plot.addItem(self.image_item)
