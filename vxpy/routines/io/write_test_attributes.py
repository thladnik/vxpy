"""
MappApp ./routines/io/write_test_attributes.py
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

from vxpy.api import get_time
from vxpy.api.io import set_digital_output
from vxpy.api.routine import IoRoutine
from vxpy.api.attribute import ArrayAttribute, ArrayType
from vxpy.api.ui import register_with_plotter


class WriteRandoms(IoRoutine):

    def __init__(self):
        super(WriteRandoms, self).__init__()

    def setup(self):
        self.sawtooth_attr = ArrayAttribute('test_sawtooth', (1, ), ArrayType.float32)
        self.poisson_1p20_attr = ArrayAttribute('test_poisson_1p200', (1, ), ArrayType.bool)

    def initialize(self):
        register_with_plotter('test_sawtooth', axis=WriteRandoms.__name__)
        register_with_plotter('test_poisson_1p200', axis=WriteRandoms.__name__)
        set_digital_output('ch_do01', 'test_poisson_1p200')

        self.poisson_high_end = 0.

    def main(self, *args, **kwargs):
        t = get_time()

        # Update sawtooth
        a = 1.
        p = 2.
        sawtooth = - 2 * a / np.pi * np.arctan(1. / np.tan(np.pi * t / p))
        self.sawtooth_attr.write(sawtooth)

        # Update poisson_1p200
        if self.poisson_high_end >= get_time():
            new_state = True
        else:
            self.poisson_high_end = 0.
            new_state = np.random.randint(200) == 0
            if new_state:
                # Show high state for 5ms
                self.poisson_high_end = get_time() + 0.005

        self.poisson_1p20_attr.write(new_state)


class RandomOnOff(IoRoutine):

    def __init__(self, *args):
        IoRoutine.__init__(self, *args)

    def setup(self):
        self.test_onoff = ArrayAttribute('test_onoff', (1,), ArrayType.bool)

    def initialize(self):
        set_digital_output('onoff_out', 'test_onoff')

    def main(self, *args, **kwargs):
        t = get_time()
        sig = int(t / 2) % 2
        self.test_onoff.write(sig)


class SinesAddedWhiteNoise(IoRoutine):

    def __init__(self, *args):
        IoRoutine.__init__(self, *args)

    def setup(self):
        self.whitenoise = ArrayAttribute('test_sines_whitenoise', (1,), ArrayType.float64)

    def initialize(self):
        register_with_plotter('test_sines_whitenoise', axis='Sines+Noise')
        self.whitenoise.add_to_file()

    def main(self, *args, **kwargs):
        t = get_time()
        self.whitenoise.write(3. * np.random.normal() + np.sin(t * 2. * np.pi * 20) + np.sin(t * 2. *  np.pi * 180))
