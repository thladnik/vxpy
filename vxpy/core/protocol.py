"""Core protocol module.

Defines the phase-based protocol hierarchy used to structure stimulation
experiments in vxPy.  A :class:`BaseProtocol` collects :class:`Phase`
objects; the concrete subclasses :class:`StaticProtocol`,
:class:`TriggeredProtocol`, and :class:`ContinuousProtocol` implement
different timing and advancement strategies.
"""
from __future__ import annotations
import importlib
from abc import abstractmethod
from inspect import isclass
from typing import Any, Dict, List, Union, Callable, Type

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
    """Get available protocol paths.
    
    Parameters
    ----------
    reload : bool
        If ``True``, rescan protocol modules even when a cached list exists.

    Returns
    -------
    List[str]
        Sorted dotted import paths of discovered protocol classes.
    """
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


def get_protocol(path: str) -> Union[Type['StaticProtocol'], None]:
    """Get protocol.
    
    Parameters
    ----------
    path : str
        Dotted import path to a protocol class.

    Returns
    -------
    Union[Type['StaticProtocol'], None]
        Protocol class object if available, otherwise ``None``.
    """
    if path not in get_available_protocol_paths():
        log.warning(f'Cannot get protocol {path}')
        return None

    # Return protocol class object
    parts = path.split('.')
    mod = importlib.import_module('.'.join(parts[:-1]))
    return getattr(mod, parts[-1])


class Phase:
    """Phase class."""

    def __init__(self, duration=None,
                 control=None, action_params=None,
                 visual=None, visual_params=None):
        """  init  .
        
        Parameters
        ----------
        duration : Union[float, int, None]
            Phase duration in seconds.
        control : Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl], None]
            Control class or instance executed for this phase.
        action_params : dict
            Keyword arguments forwarded to the phase control.
        visual : Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual], None]
            Visual class or instance rendered during the phase.
        visual_params : dict
            Parameter updates applied to the phase visual.
        """
        self.duration: Union[float, int] = duration

        self.control_parameters: Dict = action_params
        self.control = control

        self.visual: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual], None] = visual
        self.visual_parameters: Dict = visual_params

    def set_duration(self, duration: float):
        """Set duration.
        
        Parameters
        ----------
        duration : float
            Phase duration in seconds.
        """
        self.duration = duration

    @property
    def control(self) -> Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]:
        """Control.
        
        Returns
        -------
        Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]
            Control instance (or class before instantiation) assigned to this phase.
        """
        return self._control

    @control.setter
    def control(self, value: Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]):
        """Control.
        
        Parameters
        ----------
        value : Union[vxcontrol.BaseControl, Type[vxcontrol.BaseControl]]
            Control instance or class to attach to this phase.
        """
        self._control = value

    @property
    def visual(self) -> Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]:
        """Visual.
        
        Returns
        -------
        Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]
            Visual instance (or class before instantiation) assigned to this phase.
        """
        return self._visual

    @visual.setter
    def visual(self, value: Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]) -> None:
        """Visual.
        
        Parameters
        ----------
        value : Union[vxvisual.AbstractVisual, Type[vxvisual.AbstractVisual]]
            Visual instance or class to attach to this phase.
        """
        self._visual = value

    @property
    def visual_parameters(self):
        """Visual parameters.
        """
        return {} if self._visual_parameters is None else self._visual_parameters

    @visual_parameters.setter
    def visual_parameters(self, value):
        """Visual parameters.
        
        Parameters
        ----------
        value : dict
            Visual parameter mapping for this phase.
        """
        self._visual_parameters = value

    def set_visual(self, visual_cls: Type[vxvisual.AbstractVisual], params: dict = None):
        """Set visual.
        
        Parameters
        ----------
        visual_cls : Type[vxvisual.AbstractVisual]
            Visual class used for this phase.
        params : dict
            Initial visual parameter values for the phase.
        """
        self._visual = visual_cls
        self._visual_parameters = params

    @property
    def control_parameters(self):
        """Control parameters.
        """
        return {} if self._control_parameters is None else self._control_parameters

    @control_parameters.setter
    def control_parameters(self, value):
        """Control parameters.
        
        Parameters
        ----------
        value : dict
            Control parameter mapping for this phase.
        """
        self._control_parameters = value

    def set_control(self, control_cls: Type[vxcontrol.BaseControl], params: dict = None):
        """Set control.
        
        Parameters
        ----------
        control_cls : Type[vxcontrol.BaseControl]
            Control class used for this phase.
        params : dict
            Initial control parameter values for the phase.
        """
        self._control = control_cls
        self._control_parameters = params


class BaseProtocol:
    """BaseProtocol class."""

    def __init__(self):
        """  init  .
        """
        self._current_phase_id = -1
        self._phases: List[Phase] = []
        self._repeat_intervals: List[List[int]] = []
        self.global_visual_props: Dict[str, Any] = {}

        # Call create method in case there's a custom implementation
        self.create()

    @property
    def current_phase_id(self):
        """Current phase id.
        """
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def current_phase_info(self):
        """Current phase info.
        """
        return vxipc.CONTROL[CTRL_PRCL_PHASE_ID]

    @property
    def current_phase(self):
        """Current phase.
        """
        return self._phases[self.current_phase_id]

    @property
    def phase_count(self):
        """Phase count.
        """
        return len(self._phases)

    @property
    def repeat_intervals(self):
        """Repeat intervals.
        """
        return self._repeat_intervals

    def start_repeat(self):
        """Start repeat.
        """
        self._repeat_intervals.append([len(self._phases)])

    def end_repeat(self):
        """End repeat.
        """
        self._repeat_intervals[-1].append(len(self._phases))

    def add_phase(self, phase: Phase) -> None:
        """Add phase.
        
        Parameters
        ----------
        phase : Phase
            Phase object appended to this protocol.
        """
        self._phases.append(phase)

    def keep_last_frame_for(self, seconds: float):
        """Keep last frame for.
        
        Parameters
        ----------
        seconds : float
            Duration in seconds to keep the last rendered frame visible.
        """
        p = Phase(seconds)
        p.set_visual(vxvisual.KeepLast)
        self.add_phase(p)

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        """Get phase.
        
        Parameters
        ----------
        phase_id : int
            Zero-based phase index.

        Returns
        -------
        Union[Phase, None]
            Phase for ``phase_id`` or ``None`` when unavailable.
        """
        pass

    def create(self):
        """Create.
        """
        pass

    def create_controls(self):
        """Create controls.
        """
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
        """Create visuals.
        
        Parameters
        ----------
        canvas : vispy.app.Canvas
            Canvas used to instantiate protocol visuals.
        _transform : vxtranform.BaseTransform
            Display transform applied to each instantiated visual.
        """
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
    """StaticProtocol class."""

    @property
    def progress(self):
        """Progress.
        """
        return 0.

    @property
    def duration(self) -> float:
        """Duration.
        
        Returns
        -------
        float
            Total duration of all phases in seconds.
        """
        return self.get_duration_until_phase(len(self._phases))

    def get_duration_until_phase(self, phase_id: int) -> float:
        """Get duration until phase.
        
        Parameters
        ----------
        phase_id : int
            Phase index up to which durations are accumulated (exclusive).

        Returns
        -------
        float
            Sum of phase durations before ``phase_id``.
        """
        return sum([phase.duration for phase in self._phases[:phase_id] if phase is not None])

    def fetch_phase_duration(self, phase_id):
        """Fetch phase duration.
        
        Parameters
        ----------
        phase_id : int
            Index of the phase whose duration should be returned.
        """
        return self._phases[phase_id].duration

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        """Get phase.
        
        Parameters
        ----------
        phase_id : int
            Zero-based phase index.

        Returns
        -------
        Union[Phase, None]
            Phase for ``phase_id`` if in range, else ``None``.
        """
        if phase_id < self.phase_count:
            return self._phases[phase_id]
        return


class TriggeredProtocol(BaseProtocol):
    """TriggeredProtocol class."""

    phase_trigger: vxevent.Trigger = None

    def set_phase_trigger(self, trigger: vxevent.Trigger):
        """Set phase trigger.
        
        Parameters
        ----------
        trigger : vxevent.Trigger
            Trigger used to advance through protocol phases.
        """
        self.phase_trigger = trigger

    def get_phase(self, phase_id: int) -> Union[Phase, None]:
        """Get phase.
        
        Parameters
        ----------
        phase_id : int
            Zero-based phase index.

        Returns
        -------
        Union[Phase, None]
            Phase for ``phase_id`` when valid, else ``None``.
        """
        if -1 < phase_id < self.phase_count:
            return self._phases[phase_id]
        return None


class ContinuousProtocol(BaseProtocol):
    """ContinuousProtocol class."""
    pass
