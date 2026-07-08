from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseControl(ABC):
    """BaseControl class."""

    def __init__(self):
        """  init  .
        """
        self.is_active = False

    def start(self):
        """Start.
        """
        self.is_active = True

    def update(self, parameters: Dict[str, Any]):
        """Update control parameters by setting attributes.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Dictionary of parameter names to values to set as attributes on this control.
        """
        for name, value in parameters.items():
            setattr(self, name, value)

    def _end(self):
        """ end.
        """
        pass

    def end(self):
        """End.
        """
        self._end()
        self.is_active = False

    @abstractmethod
    def initialize(self, **kwargs):
        """Initialize the control with optional keyword arguments.

        Parameters
        ----------
        **kwargs : Any
            Optional keyword arguments for control-specific initialization.
        """

    @abstractmethod
    def main(self, dt: float, **pins):
        """Main control loop update method.

        Parameters
        ----------
        dt : float
            Time delta / elapsed time since last call in seconds.
        **pins : Any
            Named input pins/signals for control input.
        """

    def destroy(self):
        """Destroy.
        """
