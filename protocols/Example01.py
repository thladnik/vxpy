from MappApp_StimulationProtocol import StimulationProtocol

from stimuli.Checkerboard import Checkerboard
from stimuli.Grating import Grating

class Example01(StimulationProtocol):

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.addStimulus(Checkerboard,
                         dict(cols=16, rows=16),
                         duration=5)
        self.addStimulus(Grating,
                         dict(orientation='vertical', shape='rectangular', num=20, velocity=1.0),
                         duration=5)
        self.addStimulus(Grating,
                         dict(orientation='vertical', shape='rectangular', num=20, velocity=3.0),
                         duration=5)
        self.addStimulus(Grating,
                         dict(orientation='vertical', shape='rectangular', num=10, velocity=-1.0),
                         duration=5)
        self.addStimulus(Checkerboard,
                         dict(cols=16, rows=16),
                         duration=None)