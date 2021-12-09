"""
MappApp ./utils/__init__.py
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
from vxpy.Def import *
from vxpy import Def

def detect_fish_particle(im):
    return


def get_camera_properties(device_id):
    idx = config.Camera[Def.CameraCfg.device_id].index(device_id)
    props = {
        Def.CameraCfg.device_id: device_id,
        Def.CameraCfg.manufacturer: config.Camera[Def.CameraCfg.manufacturer][idx],
        Def.CameraCfg.model: config.Camera[Def.CameraCfg.model][idx],
        Def.CameraCfg.format: config.Camera[Def.CameraCfg.format][idx],
        Def.CameraCfg.res_x: config.Camera[Def.CameraCfg.res_x][idx],
        Def.CameraCfg.res_y: config.Camera[Def.CameraCfg.res_y][idx],
        Def.CameraCfg.exposure: config.Camera[Def.CameraCfg.exposure][idx],
        Def.CameraCfg.gain: config.Camera[Def.CameraCfg.gain][idx],
    }
    return props


def get_camera_resolution(device_id):
    idx = config.Camera[Def.CameraCfg.device_id].index(device_id)
    return config.Camera[Def.CameraCfg.res_x][idx], config.Camera[Def.CameraCfg.res_y][idx]


def calculate_background_mog2(frames):

    mog = cv2.createBackgroundSubtractorMOG2()
    for frame in frames:
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        mog.apply(img)

    # Return background
    return mog.getBackgroundImage()