from StaticProtocol import StimulationProtocol

from stimuli.Checkerboard import Checkerboard
from stimuli.Grating import Grating

class Calibration(StimulationProtocol):

    _name = 'Calibration'

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        self.addStimulus(Checkerboard,
                         dict(cols=16, rows=16),
                         duration=5)
        self.addStimulus(Grating,
                         dict(orientation='vertical', shape='rectangular', num=20, velocity=2.0),
                         duration=None)
        self.addStimulus(Checkerboard, dict(), duration=None)
