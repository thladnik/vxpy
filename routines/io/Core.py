"""
MappApp ./routines/Core.py - Custom processing routine implementations.
Copyright (C) 2020 Tim Hladnik

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
import time
import numpy as np

import Config
import Def

from routines import AbstractRoutine, ArrayAttribute, ArrayDType, ObjectAttribute

class Read(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        self.pins = [tuple(s.split(':')) for s in Config.Io[Def.IoCfg.pins]]
        self.pins = [pin for pin in self.pins if pin[-1] == 'i'] # Select just inputs to read

        for pin_name, pin_num, pin_type in self.pins:
            setattr(self.buffer, pin_name, ObjectAttribute())

    def execute(self, pin_data, device):
        for pin_name, pin_num, pin_type in self.pins:
            getattr(self.buffer, pin_name).write(pin_data[pin_name])

    def to_file01(self):

        for pin_name, pin_num, pin_type in self.pins:
            _, times, values = getattr(self.buffer, pin_name).read(0)

            if values[0] is None:
                continue

            yield pin_name, times[0], values[0]


class TriggerLedArenaFlash(AbstractRoutine):

    def __init__(self, *args, **kwargs):
        AbstractRoutine.__init__(self, *args, **kwargs)

        # Make trigger function accessible
        self.exposed.append(TriggerLedArenaFlash.trigger_flash)

        self.pins = [tuple(s.split(':')) for s in Config.Io[Def.IoCfg.pins]]
        self.pins = [pin for pin in self.pins if pin[0].startswith('pwm_chan_out')]

        self.trigger_set = False
        self.flash_start_time = np.inf
        self.flash_end_time = -np.inf
        self.trigger_state = False

        # Set buffer attribute
        self.buffer.trigger_set = ArrayAttribute(shape=(1,), dtype=ArrayDType.uint8, length=20000)
        self.buffer.flash_state = ArrayAttribute(shape=(1,), dtype=ArrayDType.uint8, length=20000)

    def execute(self, pin_data, device):
        t = time.time()
        state = self.flash_start_time <= t and self.flash_end_time > t
        #print(self.flash_start_time, t, self.flash_end_time)
        #if state:
        #    print('FLASH!')

        for pin_id, pin_num, pin_type in self.pins:
            device.write(pin_id, state)

        # Flash is over
        if self.trigger_state and t >= self.flash_end_time:
            self.trigger_state = False
            self.flash_start_time = np.inf
            self.flash_end_time = -np.inf

        self.buffer.trigger_set.write(self.trigger_set)
        self.buffer.flash_state.write(state)

        # Reset trigger set flag
        if self.trigger_set:
            self.trigger_set = not(self.trigger_set)

    def to_file01(self):
        _, _, triggers = self.buffer.trigger_set.read(0)
        _, times, flash_states = self.buffer.flash_state.read(0)

        yield 'flash_trigger', times[0], triggers[0]
        yield 'flash_state', times[0], flash_states[0]

    def trigger_flash(self, delay, duration):
        # Can't trigger flash while script is reacting to last event
        if self.trigger_state:
            return

        print('Set flash start/end')
        self.trigger_set = not(self.trigger_set)
        self.trigger_state = not(self.trigger_state)
        self.flash_start_time = time.time() + delay
        self.flash_end_time = self.flash_start_time + duration
