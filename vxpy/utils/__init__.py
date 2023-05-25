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
import importlib
import inspect
from types import ModuleType
from typing import List, Tuple, Union

import cv2

from vxpy.definitions import *
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


def get_imports_from(root: Union[str, ModuleType], incl_type: Union[type, List[type]],
                     excl_types: List[type] = None) -> List[Tuple[str, type]]:
    """Get a list of possible imports on a given root path that are of a specific type.

    Args:
        root (Union[str, ModuleType]): either a relative path in the current
            working directory, or a vxpy module

        incl_type (List[type]): type or list of types that should be included in result
        excl_types (List[type], optional): list of types to be explicitly excluded

    Returns:
          complete_list (List[Tuple[str, type]]): list of tuples containing the
          importpath and type
    """

    if not isinstance(incl_type, list):
        incl_type = [incl_type]

    complete_list = []
    if isinstance(root, ModuleType):
        for _submodule_name in root.__all__:
            try:
                _submodule = importlib.import_module(f'{root.__name__}.{_submodule_name}')
                complete_list.extend(scan_module(_submodule, incl_type, excl_types=excl_types))
            except Exception as exc:
                log.warning(f'Failed {_submodule_name} // {exc}')

        return complete_list

    # Import from files on a relative given path
    module_list = os.listdir(root)

    # Split
    path_parts = root.split(os.sep)

    # Scan all available containers on path
    for _container_name in module_list:
        _container_name = str(_container_name)
        if _container_name.startswith('_'):
            continue

        # Import module
        try:
            if os.path.isdir(os.path.join(*[*path_parts, _container_name])):
                _module = importlib.import_module('.'.join([*path_parts, _container_name]))
            else:
                _module = importlib.import_module('.'.join([*path_parts, _container_name.split('.')[0]]))

            complete_list.extend(scan_module(_module, incl_type, excl_types=excl_types))
        except Exception as _exception:
            log.warning(f'Failed to load module from {path_parts, _container_name}')

    return complete_list


def scan_module(_module: ModuleType, _type: List[type],  excl_types: List[type] = None):

    # Go through all classes in _module
    _list = []
    for _classname, _class in inspect.getmembers(_module, inspect.isclass):
        if not any([issubclass(_class, _t) for _t in _type]):
            continue

        if excl_types is not None and _class in excl_types:
            continue

        # Create item which references the visual class
        yield f'{_module.__name__}.{_classname}', _class


def calculate_background_mog2(frames):

    mog = cv2.createBackgroundSubtractorMOG2()
    for frame in frames:
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        mog.apply(img)

    # Return background
    return mog.getBackgroundImage()