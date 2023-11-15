from abc import ABC, abstractmethod

class BaseControl(ABC):

    def __init__(self):
        self.is_active = False

    def start(self):
        self.is_active = True

    def end(self):
        self.is_active = False

    @abstractmethod
    def initialize(self, **kwargs):
        """Method to be implemented in control. Called during start of phase"""

    @abstractmethod
    def main(self, dt: float):
        """Method to be implemented in control. Called on each event loop iteration"""

    def destroy(self):
        """Method to be implemented in control. Called after control phase has finished"""
