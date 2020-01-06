from StaticProtocol import StimulationProtocol

from stimuli.Checkerboard import Checkerboard
from stimuli.Grating import Grating
from stimuli.Test01 import TestA

class Example01(StimulationProtocol):

    _name = 'Example01'

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.addStimulus(TestA, dict(param_a=5))