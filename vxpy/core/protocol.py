"""Core protocol module
"""
from __future__ import annotations
import importlib
from abc import abstractmethod
from inspect import isclass
from typing import List, Union, Callable, Type, Dict, Any

import vispy.app

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
                 action=None, action_params=None,
                 visual=None, visual_params=None):
        self.duration: Union[float, int] = duration

        self.action_parameters: Dict = action_params
        self.action = action

        self.visual: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual], None] = visual
        self.visual_parameters: Dict = visual_params

    def set_duration(self, duration: float):
        self.duration = duration

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    @property
    def visual(self) -> Type[vxvisual.AbstractVisual]:
        return self._visual

    @visual.setter
    def visual(self, value) -> None:
        self._visual = value

    @property
    def action_parameters(self):
        return {} if self._action_parameters is None else self._action_parameters

    @action_parameters.setter
    def action_parameters(self, value):
        self._action_parameters = value

    @property
    def visual_parameters(self):
        return {} if self._visual_parameters is None else self._visual_parameters

    @visual_parameters.setter
    def visual_parameters(self, value):
        self._visual_parameters = value

    def set_visual(self, visual_cls: Callable, parameters: dict = None):
        self._visual = visual_cls
        self._visual_parameters = parameters

    def set_action(self, action_cls: Callable, **kwargs):
        self._action = action_cls
        self._action_parameters = kwargs

    def initialize_action(self):
        if self._action is None:
            return False

        kwargs = {} if self._action_parameters is None else self._action_parameters
        self.action = self._action(**kwargs)

        return True

    def set_initialize_visual(self, visual: vxvisual.AbstractVisual):
        self._visual = visual

    def initialize_visual(self, canvas: vispy.app.Canvas,
                          _protocol: BaseProtocol,
                          _transform: vxtranform.BaseTransform) -> bool:
        if self._visual is None:
            return False

        args = (canvas, )
        kwargs = dict(_protocol=_protocol)
        if isclass(self._visual):
            self._visual = self._visual(*args, **kwargs)
        else:
            self._visual = self._visual.__class__(*args, **kwargs)

        params = self.visual_parameters
        self._visual.update(params)

        return True


class PhaseNotSetError(Exception):
    pass


class BaseProtocol:

    def __init__(self):
        self._current_phase_id = -1
        self._phases: List[Phase] = []
        self._repeat_intervals: List[List[int]] = []
        self.global_visual_props: Dict[str, Any] = {}

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

    def initialize_actions(self):
        for phase in self._phases:
            phase.initialize_action()

    def initialize_visuals(self, canvas: vispy.app.Canvas, _transform: vxtranform.BaseTransform):
        # Fetch all visuals from phases and identify unique ones
        all_visuals = [phase.visual for phase in self._phases]
        unique_visuals = list(set(all_visuals))

        # Initialize unique visuals (one instance per visual class)
        initialize_visuals = {}
        for visual in unique_visuals:
            initialize_visuals[visual] = visual(canvas=canvas, _protocol=self, _transform=_transform)

        # Update all phases to unique visual instance
        for phase in self._phases:
            phase.set_initialize_visual(initialize_visuals[phase.visual])


class StaticProtocol(BaseProtocol):
    """Static experimental protocol which does NOT support closed-loop designs.
    """

    def __init__(self):
        BaseProtocol.__init__(self)

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
        return None


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
