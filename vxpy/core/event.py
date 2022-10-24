from typing import Any, Callable, List, Union

import numpy as np

from vxpy.core.attribute import Attribute, get_attribute


class InvalidTriggerAttributeError(Exception):
    pass


class InvalidTriggerConditionError(Exception):
    pass


class InvalidTriggerDataError(Exception):
    pass


class Trigger(object):
    attribute: Attribute = None

    @staticmethod
    def condition(data) -> (bool, Any):
        return False, None

    def __init__(self, attr: Union[str, Attribute],
                 condition: Callable = None,
                 callback: Callable = None):
        if isinstance(attr, str):
            self.attribute = get_attribute(attr)
        elif isinstance(attr, Attribute):
            self.attribute = attr
        else:
            raise InvalidTriggerAttributeError()

        if condition is not None:
            if not callable(condition):
                raise InvalidTriggerConditionError()
            else:
                self.condition = condition

        self.observers: List[Callable] = []
        if callback is not None:
            self.observers.append(callback)

    def add_callback(self, callback):
        self.observers.append(callback)

    def process(self):
        indices, times, data = self.attribute.read_all_new(include_last_read=True)

        result, instances = self.condition(data)
        if result:
            for obs in self.observers:
                obs()


class RisingEdgeTrigger(Trigger):

    @staticmethod
    def condition(data):
        if not isinstance(data, np.ndarray):
            data = np.ndarray

        data = np.squeeze(data)

        if data.ndim > 1:
            raise InvalidTriggerDataError('RisingEdgeTrigger expects 1D data')

        results = np.diff(data) > 0
        if np.any(results):
            return True, results
        else:
            return False


class FallingEdgeTrigger(Trigger):

    @staticmethod
    def condition(data):
        if not isinstance(data, np.ndarray):
            data = np.ndarray

        data = np.squeeze(data)

        if data.ndim > 1:
            raise InvalidTriggerDataError('FallingEdgeTrigger expects 1D data')

        d = np.diff(data)
        return np.any(d < 0)
