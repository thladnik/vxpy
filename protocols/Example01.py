from MappApp_Protocol import StimulationProtocol

from stimuli.Checkerboard import Checkerboard
from stimuli.Grating import Grating

class Example01(StimulationProtocol):

    def __init__(self):
        super().__init__()

        self.addStimulus(Checkerboard, dict(), duration=10)
        self.addStimulus(Grating, dict(), duration=None)
        self.addStimulus(Checkerboard, dict(), duration=None)
