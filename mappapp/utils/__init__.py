import cv2

from mappapp import Config
from mappapp import Def

def detect_fish_particle(im):
    return


def get_camera_properties(device_id):
    idx = Config.Camera[Def.CameraCfg.device_id].index(device_id)
    props = {
        Def.CameraCfg.device_id: device_id,
        Def.CameraCfg.manufacturer: Config.Camera[Def.CameraCfg.manufacturer][idx],
        Def.CameraCfg.model: Config.Camera[Def.CameraCfg.model][idx],
        Def.CameraCfg.format: Config.Camera[Def.CameraCfg.format][idx],
        Def.CameraCfg.res_x: Config.Camera[Def.CameraCfg.res_x][idx],
        Def.CameraCfg.res_y: Config.Camera[Def.CameraCfg.res_y][idx],
        Def.CameraCfg.exposure: Config.Camera[Def.CameraCfg.exposure][idx],
        Def.CameraCfg.gain: Config.Camera[Def.CameraCfg.gain][idx],
    }
    return props


def get_camera_resolution(device_id):
    idx = Config.Camera[Def.CameraCfg.device_id].index(device_id)
    return Config.Camera[Def.CameraCfg.res_x][idx], Config.Camera[Def.CameraCfg.res_y][idx]


def calculate_background_mog2(frames):

    mog = cv2.createBackgroundSubtractorMOG2()
    for frame in frames:
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        mog.apply(img)

    # Return background
    return mog.getBackgroundImage()