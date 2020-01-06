from StaticProtocol import StimulationProtocol

from stimuli.Checkerboard import Checkerboard
from stimuli.Grating import Grating

class Example01(StimulationProtocol):

    _name = 'Example01'

    def __init__(self, _glWindow):
        super().__init__(_glWindow)

        for num in range(4):

            for v in range(5):

                self.addStimulus(Grating,
                                 dict(orientation='vertical', shape='rectangular', num=10+num*4, velocity=v+1),
                                 duration=5)