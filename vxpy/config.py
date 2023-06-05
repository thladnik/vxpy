"""Configuration module
"""
from typing import List, Dict, Any

PRESERVED_ORDER: List[str] = []
CONFIG_FILEPATH: str = ''

PATH_CALIBRATION: str = ''
PATH_EXAMPLES: str = ''
CAMERA_USE: bool = True
CAMERA_DEVICES: Dict[str, Dict[str, Any]] = {}
DISPLAY_USE: bool = True
DISPLAY_FPS: int = 60
DISPLAY_GL_VERSION: str = '420 core'
DISPLAY_TRANSFORM: str = 'DirectTransform'
DISPLAY_WIN_SCREEN_ID: int = 0
DISPLAY_WIN_SIZE_HEIGHT_PX: int = 600
DISPLAY_WIN_SIZE_WIDTH_PX: int = 600
DISPLAY_WIN_POS_X: int = 0
DISPLAY_WIN_POS_Y: int = 0
GUI_USE: bool = True
GUI_REFRESH: int = 30
GUI_FPS: int = 20
GUI_SCREEN: int = 0
GUI_ADDONS: Dict[str, Dict[str, Any]] = {}
IO_USE: bool = True
IO_PINS: Dict[str, Dict[str, Any]] = {}
IO_MAX_SR: int = 500
IO_DEVICES: Dict[str, Dict[str, Any]]
WORKER_USE: bool = True
REC_ENABLE: bool = True
REC_OUTPUT_FOLDER: str = ''
REC_ATTRIBUTES: Dict[str, Dict[str, Any]] = {}
ROUTINES: Dict[str, Dict[str, Any]] = {}
