"""
./vxpy/setup/res/routines/camera/detect_particles.py
Copyright (C) 2021 Tim Hladnik

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
import cv2
import numpy as np
from PySide6 import QtWidgets
import pyqtgraph as pg

from vxpy.api.attribute import ArrayAttribute, ArrayType, read_attribute
from vxpy.api.camera import find_config_for_camera_id, Format
from vxpy.api.dependency import require_camera_device
from vxpy.api.routine import CameraRoutine
from vxpy.api.ui import AddonWidget


class ParticleDetection(CameraRoutine):

    def __init__(self, *args, **kwargs):
        CameraRoutine.__init__(self, *args, **kwargs)

        # (optional) Make sure right camera is configured (easier debugging)
        require_camera_device('multiple_fish')

    def setup(self):
        # Get camera dimensions
        config = find_config_for_camera_id('multiple_fish')
        fmt = Format.from_str(config['format'])
        self.res_x = fmt.width
        self.res_y = fmt.height

        # Create an array attribute to store output image in
        self.frame_with_keypoints = ArrayAttribute('frame_with_keypoints', (self.res_y, self.res_x, 3), ArrayType.uint8)

    def initialize(self):
        # Mark output array attribute as something to be written to file
        self.frame_with_keypoints.add_to_file()

    def main(self, *args, **frames):
        # Read frame
        frame = frames.get('multiple_fish')

        # Make sure there is a frame
        if frame is None:
            return

        # Apply inv. threshold (filter for dark particles)
        ret, thresh = cv2.threshold(frame, 70, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours for minimum area size and draw on RGB new_frame
        new_frame = np.repeat(frame[:,:,np.newaxis], 3, axis=-1)
        for cnt in contours:
            if cv2.contourArea(cnt) > 300:
                cv2.drawContours(new_frame, [cnt], -1, (255, 0, 0), 2)

        # Write frame with drawn contours to attribute
        self.frame_with_keypoints.write(new_frame)


class ParticleDetectionWidget(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        # Add graphics widget
        self.widget = pg.GraphicsLayoutWidget()
        self.layout().addWidget(self.widget)

        # Add plot item to graphics widget
        self.plot = self.widget.addPlot(0,0,1,10)
        self.plot.hideAxis('left')
        self.plot.hideAxis('bottom')
        self.plot.setAspectLocked(True)

        # Add image item to plot
        self.item = pg.ImageItem()
        self.plot.addItem(self.item)

    def update_frame(self):
        # Read the attribute
        i, t, v = read_attribute('frame_with_keypoints')

        # Make sure there's is a frame
        if t[0] is None:
            return
        frame = v[0]

        # Update image item
        self.item.setImage(frame)