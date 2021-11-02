"""
MappApp ./routines/io/__init__.py
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
from typing import Any, Dict
import numpy as np

from vxpy import Config
from vxpy import Def
from vxpy.api.attribute import ArrayAttribute, ArrayType, write_to_file, write_attribute
from vxpy.core import routine, ipc
from vxpy.routines.camera import zf_tracking
from vxpy.api.ui import register_with_plotter


class ReadAll(routine.IoRoutine):

    def setup(self):

        # Read all pins
        self.pin_configs: Dict[str, Dict] = {}
        for did, pins in Config.Io[Def.IoCfg.pins].items():
            for pid, pconf in pins.items():
                pconf.update(dev=did)
                self.pin_configs[pid] = pconf

        # Set up buffer attributes
        self.attributes: Dict[str, ArrayAttribute] = {}
        for pid, pconf in self.pin_configs.items():
            if pconf['type'] in ('do', 'ao'):
                continue
            if pconf['type'] == 'di':
                attr = ArrayAttribute(pid, (1,), ArrayType.uint8)
            else:
                attr = ArrayAttribute(pid, (1,), ArrayType.float64)
            self.attributes[pid] = attr

            # Add pin to be written to file
            write_to_file(self, pid)

    def initialize(self):
        for pid, attr in self.attributes.items():
            axis = self.pin_configs[pid]['type']
            register_with_plotter(attr.name, axis=axis)

    def main(self, **pins):
        for pid, pin in pins.items():
            if pid not in self.attributes:
                continue
            write_attribute(pid, pin.read())


###
# TODO: update the following classes to work with current version

class ReadAnalog(routine.IoRoutine):

    def setup(self):

        self.pins = [tuple(s.split(':')) for s in Config.Io[Def.IoCfg.pins]]
        self.pins = [pin for pin in self.pins if pin[-1] == 'a'] # Select just inputs to read

        for pin_name, pin_num, pin_type in self.pins:
            setattr(self.buffer, pin_name, routine.ArrayAttribute((1,), routine.ArrayDType.float64))

    def main(self, pin_data, device):
        for pin_name, pin_num, pin_type in self.pins:
            getattr(self.buffer, pin_name).write(pin_data[pin_name])


class ReadDigital(routine.IoRoutine):

    def __init__(self, *args, **kwargs):
        routine.IoRoutine.__init__(self, *args, **kwargs)

        self.pins = [tuple(s.split(':')) for s in Config.Io[Def.IoCfg.pins]]
        self.pins = [pin for pin in self.pins if pin[-1] == 'i'] # Select just inputs to read

        for pin_name, pin_num, pin_type in self.pins:
            setattr(self.buffer, pin_name, routine.ArrayAttribute((1,), routine.ArrayDType.float64))

    def main(self, pin_data, device):
        for pin_name, pin_num, pin_type in self.pins:
            getattr(self.buffer, pin_name).write(pin_data[pin_name])


class TestTrigger(routine.IoRoutine):

    def __init__(self, *args, **kwargs):
        routine.IoRoutine.__init__(self, *args, **kwargs)

        self.exposed.append(TestTrigger.do_trigger)

        self.connect_to_trigger('saccade_trigger', zf_tracking.EyePositionDetection, TestTrigger.do_trigger01)

    def main(self, *args, **kwargs):
        pass

    def do_trigger01(self):
        print('I am so triggered!!! -.-"')

    def do_trigger(self,there):
        here = time.time()
        print('Time sent {:.5f} // Time received {:.5f} // Time diff {:.5f}'.format(there,here,here-there))


class TriggerLedArenaFlash(routine.IoRoutine):

    def __init__(self, *args, **kwargs):
        routine.IoRoutine.__init__(self, *args, **kwargs)

        # Make trigger function accessible
        self.exposed.append(TriggerLedArenaFlash.trigger_flash)
        self.exposed.append(TriggerLedArenaFlash.set_delay_ms)
        self.exposed.append(TriggerLedArenaFlash.set_delay_s)
        self.exposed.append(TriggerLedArenaFlash.set_duration_ms)
        self.exposed.append(TriggerLedArenaFlash.set_duration_s)

        # Connect to saccade trigger
        #self.connect_to_trigger('saccade_trigger', EyePositionDetection, TriggerLedArenaFlash.trigger_flash)

        self.pins = [tuple(s.split(':')) for s in Config.Io[Def.IoCfg.pins]]
        self.pins = [pin for pin in self.pins if pin[0].startswith('pwm_chan_out')]

        self.trigger_set = False
        self.flash_start_time = np.inf
        self.flash_end_time = -np.inf
        self.trigger_state = False

        # Set buffer attribute
        self.buffer.trigger_set = routine.ArrayAttribute(shape=(1,), dtype=routine.ArrayDType.uint8, length=20000)
        self.buffer.flash_state = routine.ArrayAttribute(shape=(1,), dtype=routine.ArrayDType.uint8, length=20000)

        self.delay = None
        self.duration = None

    def initialize(self):
        self.register_with_ui_plotter(TriggerLedArenaFlash, 'trigger_set', 1, name='Flash trigger', axis='di')
        self.register_with_ui_plotter(TriggerLedArenaFlash, 'flash_state', 1, name='Flash state', axis='di')

    def set_delay_ms(self, delay):
        self.set_delay_s(delay/1000)

    def set_delay_s(self,delay):
        self.delay = delay

    def set_duration_ms(self, duration):
        self.set_duration_s(duration/1000)

    def set_duration_s(self, duration):
        self.duration = duration

    def main(self, pin_data, device):
        # Check saccade
        _, _, le_sacc_val = ipc.Camera.read(zf_tracking.EyePositionDetection, 'le_saccade_0')
        _, sacc_time, re_sacc_val = ipc.Camera.read(zf_tracking.EyePositionDetection, 're_saccade_0')

        if re_sacc_val[0] > 0 or le_sacc_val[0] > 0:
            self.trigger_flash()

        t = time.time()
        state = self.flash_start_time <= t and self.flash_end_time > t

        for pin_id, pin_num, pin_type in self.pins:
            device.write(**{pin_id: int(state)})

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

    def trigger_flash(self):
        # Can't trigger flash while script is reacting to last event
        if self.trigger_state:
            return

        print('Set flash start/end')
        self.trigger_set = not(self.trigger_set)
        self.trigger_state = not(self.trigger_state)
        self.flash_start_time = time.time() + self.delay
        self.flash_end_time = self.flash_start_time + self.duration
