"""
MappApp ./utils/display_calibration.py
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
import cv2

from vxpy import config
from vxpy.definitions import *
from vxpy import definitions

def detect_fish_particle(im):
    return


def get_camera_properties(device_id):
    idx = config.Camera[definitions.CameraCfg.device_id].index(device_id)
    props = {
        definitions.CameraCfg.device_id: device_id,
        definitions.CameraCfg.manufacturer: config.Camera[definitions.CameraCfg.manufacturer][idx],
        definitions.CameraCfg.model: config.Camera[definitions.CameraCfg.model][idx],
        definitions.CameraCfg.format: config.Camera[definitions.CameraCfg.format][idx],
        definitions.CameraCfg.res_x: config.Camera[definitions.CameraCfg.res_x][idx],
        definitions.CameraCfg.res_y: config.Camera[definitions.CameraCfg.res_y][idx],
        definitions.CameraCfg.exposure: config.Camera[definitions.CameraCfg.exposure][idx],
        definitions.CameraCfg.gain: config.Camera[definitions.CameraCfg.gain][idx],
    }
    return props


def get_camera_resolution(device_id):
    idx = config.Camera[definitions.CameraCfg.device_id].index(device_id)
    return config.Camera[definitions.CameraCfg.res_x][idx], config.Camera[definitions.CameraCfg.res_y][idx]


def calculate_background_mog2(frames):

    mog = cv2.createBackgroundSubtractorMOG2()
    for frame in frames:
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        mog.apply(img)

    # Return background
    return mog.getBackgroundImage()