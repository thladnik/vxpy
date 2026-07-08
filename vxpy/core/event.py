"""Event trigger module for vxPy.

Provides trigger classes that monitor shared attributes and fire callbacks
when user-defined conditions are met.
"""
from __future__ import annotations
from typing import Any, Callable, Iterable, List, Union

import numpy as np

import vxpy.core.attribute as vxattribute
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class Trigger:
    """Trigger class."""

    all: List[Trigger] = []
    attribute: Union[vxattribute.Attribute, None] = None

    @staticmethod
    def _return_empty() -> (bool, np.ndarray):
        """ return empty.
        
        Returns
        -------
        (bool, np.ndarray)
            ``(False, empty_mask)`` indicating that no trigger events were detected.
        """
        return False, np.array([])

    def condition(self, data) -> (bool, np.ndarray):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Newly read attribute payload to evaluate.

        Returns
        -------
        (bool, np.ndarray)
            Success flag and boolean mask selecting rows that should fire callbacks.
        """
        return self._return_empty()

    def __init__(self, attr: Union[str, vxattribute.Attribute], callback: Union[Callable, List[Callable]] = None):
        """  init  .
        
        Parameters
        ----------
        attr : Union[str, vxattribute.Attribute]
            Attribute object or attribute name monitored by this trigger.
        callback : Union[Callable, List[Callable]]
            Callback(s) invoked as ``callback(index, time, value)`` on trigger events.
        """
        if isinstance(attr, str):
            self.attribute_name = attr
            self.attribute = None
        elif isinstance(attr, vxattribute.Attribute):
            self.attribute_name = attr.name
            self.attribute = attr
        else:
            log.error('Trigger attribute has to be either valid attribute name or attribute object.')
            return

        log.info(f'Add {self.__class__.__name__} on attribute "{self.attribute_name}"')

        self.callbacks: List[Callable] = []
        if callback is not None:
            self.add_callback(callback)

        # Find last index
        self._last_read_idx: int = 0
        self._active = False

    def __repr__(self):
        """  repr  .
        """
        return f"{self.__class__.__name__}('{self.attribute.name}', {self.callbacks})"

    def set_active(self):
        """Set active.
        """
        if self not in self.all:
            self.all.append(self)

        if self.attribute is None:
            self.attribute = vxattribute.get_attribute(self.attribute_name)

        # Set index and active
        self._last_read_idx = self.attribute.index
        self._active = True

    def set_inactive(self):
        """Set inactive.
        """
        self._active = False

    def add_callback(self, callback: Union[Callable, Iterable[Callable]]):
        """Add callback.
        
        Parameters
        ----------
        callback : Union[Callable, Iterable[Callable]]
            Single callback or iterable of callbacks to append.
        """

        if not isinstance(callback, Iterable):
            callback = [callback]

        for c in callback:
            if not isinstance(c, Callable):
                log.warning(f'Failed to set callback {c} on {self.__class__.__name__}. '
                            f'Trigger callback must be callable')

            self.callbacks.append(c)

    def process(self):
        """Process.
        """
        if not self._active:
            return

        # Read all new datasets in attribute (including the last read dataset)
        indices, times, data = self.attribute.read(from_idx=self._last_read_idx)

        # If empty, return
        if len(indices) == 0:
            return

        # Set new last index
        self._last_read_idx = indices[-1]

        # Evaluate condition
        success, instances = self.condition(data)

        # Return is no success
        if not success:
            return

        # Call connected callbacks
        for c in self.callbacks:
            for i in np.where(instances)[0]:
                c(indices[i], times[i], data[i])


class OnTrigger(Trigger):
    """OnTrigger class."""

    def condition(self, data):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Sequence or array of attribute samples to cast to boolean states.
        """

        # Convert if necessary
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        # Remove first dataset (otherwise this one would be evaluated again) and remove extra dimensions
        data = np.squeeze(data[1:])

        # Compute condition
        results = data.astype(bool)
        results = np.append([False], results)

        # Return results
        if np.any(results):
            return True, results
        else:
            return self._return_empty()


class NotNullTrigger(Trigger):
    """NotNullTrigger class."""

    def condition(self, data) -> (bool, np.ndarray):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Sequence or array of attribute samples to test for non-zero values.

        Returns
        -------
        (bool, np.ndarray)
            Success flag and mask marking samples that are not zero.
        """

        # Convert if necessary
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        results = data != 0

        if np.any(results):
            return True, results
        else:
            return self._return_empty()


class RisingEdgeTrigger(Trigger):
    """RisingEdgeTrigger class."""

    def condition(self, data):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Sequence or array of samples used to detect positive transitions.
        """

        # Convert if necessary
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        # Remove extra dimensions
        data = np.squeeze(data)

        if data.ndim == 0 or data.shape[0] < 2:
            return self._return_empty()

        # Compute condition: type of data CANNOT be bool, because np.diff on boolean arrays
        #  always evaluates to True if there's any difference - regardless of sign
        results = np.diff(data.astype(int)) > 0
        # Prepend False to fix length
        results = np.append([False], results)

        # Return results
        if np.any(results):
            return True, results
        else:
            return self._return_empty()


class FallingEdgeTrigger(Trigger):
    """FallingEdgeTrigger class."""

    def condition(self, data):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Sequence or array of samples used to detect negative transitions.
        """

        # Convert if necessary
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        # Remove extra dimensions
        data = np.squeeze(data)

        if data.ndim == 0 or data.shape[0] < 2:
            return self._return_empty()

        # Compute condition: type of data CANNOT be bool, because np.diff on boolean arrays
        #  always evaluates to True if there's any difference - regardless of sign
        results = np.diff(data.astype(int)) < 0
        # Prepend False to fix length
        results = np.append([False], results)

        # Return results
        if np.any(results):
            return True, results
        else:
            return self._return_empty()


class NewDataTrigger(Trigger):
    """NewDataTrigger class."""

    def condition(self, data) -> (bool, np.ndarray):
        """Condition.
        
        Parameters
        ----------
        data : Any
            Sequence of newly read samples including the previously seen sample at index 0.

        Returns
        -------
        (bool, np.ndarray)
            Success flag and mask where all entries except the first are marked ``True``.
        """

        success = False
        instances = np.zeros(len(data), dtype=bool)
        if len(data) > 1:
            success = True
            instances[1:] = True

        return success, instances
