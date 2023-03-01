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
CALIBRATION_PATH: str = ''
CAMERA_USE: bool = True
CAMERA_DEVICES: Dict[str, Dict[str, Any]] = {}
DISPLAY_USE: bool = True
DISPLAY_FPS: int = 60
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
