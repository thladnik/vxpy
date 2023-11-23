from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseControl(ABC):

    def __init__(self):
        self.is_active = False

    def start(self):
        self.is_active = True

    def update(self, parameters: Dict[str, Any]):
        for name, value in parameters.items():
            setattr(self, name, value)

    def _end(self):
        pass

    def end(self):
        self._end()
        self.is_active = False

    @abstractmethod
    def initialize(self, **kwargs):
        """Method to be implemented in control. Called during start of phase"""

    @abstractmethod
    def main(self, dt: float):
        """Method to be implemented in control. Called on each event loop iteration"""

    def destroy(self):
        """Method to be implemented in control. Called after control phase has finished"""
