from __future__ import annotations
from typing import Any, Callable, Iterable, List, Union

import numpy as np

import vxpy.core.attribute as vxattribute
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class Trigger:
    all: List[Trigger] = []
    attribute: vxattribute.Attribute = None

    @staticmethod
    def condition(data) -> (bool, np.ndarray):
        return False, None

    def __init__(self, attr: Union[str, vxattribute.Attribute],
                 callback: Union[Callable, List[Callable]] = None):

        if isinstance(attr, str):
            self.attribute = vxattribute.get_attribute(attr)
        elif isinstance(attr, vxattribute.Attribute):
            self.attribute = attr
        else:
            log.error('Trigger attribute has to be either valid attribute name or attribute object.')
            return

        self.callbacks: List[Callable] = []
        if callback is not None:
            self.add_callback(callback)

        self.all.append(self)

        # Find last index
        self._last_read_idx: int = self.attribute.index - 1
        self._active = False

    def __repr__(self):
        return f"{self.__name__}('{self.attribute.name}', {self.callbacks})"

    def set_active(self, active):
        self._active = active

    def set_inactive(self, inactive):
        self._active = not inactive

    def add_callback(self, callback: Union[Callable, Iterable[Callable]]):

        if not isinstance(callback, Iterable):
            callback = [callback]

        for c in callback:
            if not isinstance(c, Callable):
                log.warning('Trigger callback must be callable')

            self.callbacks.append(c)

    def process(self):
        if not self._active:
            return

        # Read all new datasets in attribute
        indices, times, data = self.attribute.read(from_idx=self._last_read_idx)
        if len(indices) == 0:
            return

        # Set new last index
        self._last_read_idx = indices[-1] + 1

        # Evaluate condition
        result, instances = self.condition(data)
        if result:
            # print(instances)
            # print(np.where(instances)[0])
            idcs = np.where(instances)[0].astype(int)
            # print([times[i] for i in idcs])
            for c in self.callbacks:
                for i in np.where(instances)[0]:
                    c(indices[i], times[i], data[i])


class RisingEdgeTrigger(Trigger):

    @staticmethod
    def condition(data):
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        data = np.squeeze(data)

        if data.ndim != 1 or data.shape[0] < 2:
            return False, []

        results = np.diff(data) > 0
        results = np.append(results, [False])
        if np.any(results):
            return True, results
        else:
            return False, []


class FallingEdgeTrigger(Trigger):

    @staticmethod
    def condition(data):
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        data = np.squeeze(data)

        if data.ndim != 1 or data.shape[0] < 2:
            return False, []

        results = np.diff(data) < 0
        results = np.append(results, [False])
        if np.any(results):
            return True, results
        else:
            return False, []
