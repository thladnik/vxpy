"""Core protocol module
"""
from __future__ import annotations
import importlib
from abc import abstractmethod
from inspect import isclass
from typing import List, Union, Callable, Type, Dict, Any

import vispy.app

import vxpy.core.control as vxcontrol
import vxpy.core.event as vxevent
import vxpy.core.ipc as vxipc
import vxpy.core.logger as vxlogger
import vxpy.core.transform as vxtranform
import vxpy.core.visual as vxvisual
from vxpy.definitions import *

log = vxlogger.getLogger(__name__)

_available_protocols: List[str] = []


def get_available_protocol_paths(reload=False) -> List[str]:
    global _available_protocols

    if len(_available_protocols) > 0 and not reload:
        return _available_protocols

    _available_protocols = []
    basepath = PATH_PROTOCOL
    filelist = os.listdir(basepath)
    for filename in filelist:

        # Load protocol module
        path = '.'.join([*basepath.split(os.sep), filename.replace('.py', '')])

        if os.path.isdir(path):
            continue

        try:
            mod = importlib.import_module(path)
        except Exception as exc:
            log.warning(f'Unable to load protocol {path}')
            import traceback
            print(traceback.print_exc())
            continue

        # Load protocols in module
        for s in dir(mod):
            # Skip everything that's not a protocol class
            obj = getattr(mod, s)
            if not isinstance(obj, type) or not issubclass(obj, BaseProtocol):
                continue
            # Skip all base classses
            if obj == StaticProtocol:
                continue

            fullpath = f'{path}.{s}'

            _available_protocols.append(fullpath)

    return sorted(_available_protocols)


def get_protocol(path: str) -> Union[Type[StaticProtocol], None]:
    if path not in get_available_protocol_paths():
        log.warning(f'Cannot get protocol {path}')
        return None

    # Return protocol class object
    parts = path.split('.')
    mod = importlib.import_module('.'.join(parts[:-1]))
    return getattr(mod, parts[-1])


class Phase:

    def __init__(self, duration=None,
                 control=None, action_params=None,
                 visual=None, visual_params=None):
        self.duration: Union[float, int] = duration

        self.control_parameters: Dict = action_params
        self.control = control

        self.visual: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual], None] = visual
        self.visual_parameters: Dict = visual_params

    def set_duration(self, duration: float):
        self.duration = duration

    @property
    def control(self) -> Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]:
        return self._control

    @control.setter
    def control(self, value: Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]):
        self._control = value

    @property
    def visual(self) -> Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]:
        return self._visual

    @visual.setter
    def visual(self, value: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]) -> None:
        self._visual = value

    @property
    def visual_parameters(self):
        return {} if self._visual_parameters is None else self._visual_parameters

    @visual_parameters.setter
    def visual_parameters(self, value):
        self._visual_parameters = value

    def set_visual(self, visual_cls: Type[vxvisual.AbstractVisual], params: dict = None):
        self._visual = visual_cls
        self._visual_parameters = params

    @property
    def control_parameters(self):
        return {} if self._control_parameters is None else self._control_parameters

    @control_parameters.setter
    def control_parameters(self, value):
        self._control_parameters = value

    def set_control(self, control_cls: Type[vxcontrol.BaseControl], params: dict = None):
        self._control = control_cls
        self._control_parameters = params


class BaseProtocol:

    def __init__(self):
        self._current_phase_id = -1
        self._phases: List[Phase] = []
        self._repeat_intervals: List[List[int]] = []
        self.global_visual_props: Dict[str, Any] = {}

        # Call create method in case there's a custom implementation
        self.create()

    @property
    def current_phase_id(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def current_phase_info(self):
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def current_phase(self):
        return self._phases[self.current_phase_id]

    @property
    def phase_count(self):
        return len(self._phases)

    @property
    def repeat_intervals(self):
        return self._repeat_intervals

    def start_repeat(self):
        """Mark start of new repeat within the protocol"""
        self._repeat_intervals.append([len(self._phases)])

    def end_repeat(self):
        """Mark end of repeat within the protocol"""
        self._repeat_intervals[-1].append(len(self._phases))

    def add_phase(self, phase: Phase) -> None:
        """Add a new phase to the protocol"""
        self._phases.append(phase)

    def keep_last_frame_for(self, seconds: float):
        """Shortcut for adding a static KeepLast phase.
        This will retain the last rendered frame for given number of seconds on the screen"""
        p = Phase(seconds)
        p.set_visual(vxvisual.KeepLast)
        self.add_phase(p)

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        pass

    def create(self):
        """Method can be reimplemented in protocol
        and will be called upon instantiation
        """
        pass

    def create_controls(self):
        # Fetch all control from phases and identify unique ones
        _all = [phase.control for phase in self._phases if phase.control is not None]
        _unique = list(set(_all))

        # Create each unique visual once
        _created = {}
        for cls in _unique:
            _created[cls] = cls()

        # Update all phases to reference unique control instance
        for phase in self._phases:
            phase.control = _created.get(phase.control, None)

    def create_visuals(self, canvas: vispy.app.Canvas, _transform: vxtranform.BaseTransform):
        # Fetch all visuals from phases and identify unique ones
        _all = [phase.visual for phase in self._phases if phase.visual is not None]
        _unique = list(set(_all))

        # Create each unique visual once
        _created = {}
        for cls in _unique:
            _created[cls] = cls(canvas=canvas, _protocol=self, _transform=_transform)

        # Update all phases to reference unique visual instance
        for phase in self._phases:
            phase.visual = _created.get(phase.visual, None)


class StaticProtocol(BaseProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    @property
    def progress(self):
        return 0.

    @property
    def duration(self) -> float:
        return self.get_duration_until_phase(len(self._phases))

    def get_duration_until_phase(self, phase_id: int) -> float:
        return sum([phase.duration for phase in self._phases[:phase_id] if phase is not None])

    def fetch_phase_duration(self, phase_id):
        return self._phases[phase_id].duration

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        if phase_id < self.phase_count:
            return self._phases[phase_id]
        return


class TriggeredProtocol(BaseProtocol):

    phase_trigger: vxevent.Trigger = None

    def set_phase_trigger(self, trigger: vxevent.Trigger):
        self.phase_trigger = trigger

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        if -1 < phase_id < self.phase_count:
            return self._phases[phase_id]
        return None


class ContinuousProtocol(BaseProtocol):
    pass
