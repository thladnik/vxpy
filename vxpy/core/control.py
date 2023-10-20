from abc import ABC, abstractmethod

class BaseControl(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def initialize(self, **kwargs):
        """Method to be implemented in control. Called during start of phase"""

    @abstractmethod
    def control(self, dt):
        """Method to be implemented in control. Called on each event loop iteration"""

    def destroy(self):
        """Method to be implemented in control. Called after control phase has finished"""
