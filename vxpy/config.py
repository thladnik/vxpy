"""
vxPy ./config.py
Copyright (C) 2022 Tim Hladnik

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
from typing import List, Dict, Any

PRESERVED_ORDER: List[str] = []

CONF_CALIBRATION_PATH: str = ''

CONF_CAMERA_USE: bool = True
CONF_CAMERA_DEVICES: Dict[str, Dict[str, Any]] = {}
CONF_CAMERA_ROUTINES: List[str] = []

CONF_DISPLAY_USE: bool = True

CONF_DISPLAY_FPS: int = 60
CONF_DISPLAY_ROUTINES: List[str] = []

CONF_GUI_USE: bool = True
CONF_GUI_SCREEN: int = 0
CONF_GUI_ADDONS: Dict[str, List[str]] = {}

CONF_IO_USE: bool = True
CONF_IO_PINS: Dict[str, Dict[str, Any]] = {}
CONF_IO_MAX_SR: int = 500
CONF_IO_DEVICES: Dict[str, Dict[str, Any]]
CONF_IO_ROUTINES: List[str] = []

CONF_WORKER_USE: bool = True
CONF_WORKER_ROUTINES: List[str] = []

CONF_REC_ENABLE: bool = True
CONF_REC_OUTPUT_FOLDER: str = ''
CONF_REC_ATTRIBUTES: List[str] = []
