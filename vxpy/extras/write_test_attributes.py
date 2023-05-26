"""
vxPy ./routines/write_test_attributes.py
Copyright (C) 2021 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import numpy as np

import vxpy.api as vxapi
import vxpy.core.ipc as vxipc
from vxpy.core.io import set_digital_output
from vxpy.api.routine import IoRoutine
import vxpy.api.attribute as vxattribute
from vxpy.core.ui import register_with_plotter


class WriteRandoms(IoRoutine):
    """
    Creates two dummy signals. One sawtooth and one following a Poisson process.
    """

    attr_name_sawtooth = 'test_sawtooth'
    attr_name_poisson_1p200 = 'test_poisson_1p200'
    test_poisson_p2Hz = 'test_poisson_p2Hz'  # poisson with mean frequency of .2Hz

    def __init__(self):
        super(WriteRandoms, self).__init__()

        self.poisson_1p200_high_end = 0.

    @classmethod
    def require(cls):
        vxattribute.ArrayAttribute(cls.attr_name_sawtooth, (1, ), vxattribute.ArrayType.float32)
        vxattribute.ArrayAttribute(cls.test_poisson_p2Hz, (1,), vxattribute.ArrayType.bool)

    def initialize(self):
        # Add attributes to plotter
        register_with_plotter(self.attr_name_sawtooth, axis=WriteRandoms.__name__)
        register_with_plotter(self.test_poisson_p2Hz, axis=WriteRandoms.__name__)

        # Set binary signal to be written to output channel named "ch_do01"
        set_digital_output('ch_do01', self.test_poisson_p2Hz)

    def main(self, *args, **kwargs):
        t = vxipc.get_time()

        # Update sawtooth
        sawtooth = - 2. / np.pi * np.arctan(1. / np.tan(np.pi * t / 2.))
        vxattribute.get_attribute(self.attr_name_sawtooth).write(sawtooth)

        # Update poisson_1p200

        interval = vxipc.LocalProcess.interval
        state_p5Hz = np.random.rand() < interval * 0.2

        # if self.poisson_1p200_high_end >= t:
        #     new_state = True
        # else:
        #     self.poisson_1p200_high_end = 0.
        #     new_state = np.random.randint(200) == 0
        #     if new_state:
        #         # Show high state for 5ms
        #         self.poisson_1p200_high_end = t + 0.005

        vxattribute.get_attribute(self.test_poisson_p2Hz).write(state_p5Hz)


class OnOff(IoRoutine):
    """
    Creates a dummy signal that randomly switches between on and off state
    """

    attr_name = 'test_onoff'

    def __init__(self, *args):
        IoRoutine.__init__(self, *args)

    @classmethod
    def setup(cls):
        vxattribute.ArrayAttribute(cls.attr_name, (1,), vxattribute.ArrayType.bool)

    def initialize(self):
        # Set attribute to be written to an output channel named "onoff_out"
        set_digital_output('onoff_out', self.attr_name)

    def main(self, *args, **kwargs):
        t = vxipc.get_time()
        sig = int(t / 2) % 2
        vxattribute.get_attribute(self.attr_name).write(sig)


class SinesAddedWhiteNoise(IoRoutine):
    """
    Creates a dummy signal consisting of a number of sinewaves with noise
    """

    attr_name = 'test_sines_whitenoise'

    def __init__(self, *args):
        IoRoutine.__init__(self, *args)

        self.frequencies = [10, 30, 55, 120, 180, 333]
        self.phases = 2 * np.pi * np.random.rand(len(self.frequencies))

    @classmethod
    def require(cls):
        vxattribute.ArrayAttribute(cls.attr_name, (1,), vxattribute.ArrayType.float64)

    def initialize(self):
        # Add to plotter
        register_with_plotter(self.attr_name, axis='Noisy signals')

        # Add to candidate list for save to disk
        vxattribute.get_attribute(self.attr_name).add_to_file()

    def main(self, *args, **kwargs):
        y = np.random.normal()
        for p, f in zip(self.phases, self.frequencies):
            y += np.sin(vxipc.get_time() * 2 * np.pi * f + p * f) / 5
        vxattribute.get_attribute(self.attr_name).write(y)
