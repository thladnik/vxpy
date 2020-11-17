import logging
import numpy as np
import time

import Config
import Def
import Logging

class Device:

    def connect(self):

        _dmodel = Config.Io[Def.IoCfg.device_model]

        ### Set up and connect device on configured comport
        if _dmodel == 'Virtual':
            self._board = Virtual()
        else:
            import pyfirmata
            self._board = getattr(pyfirmata, _dmodel)(Config.Io[Def.IoCfg.device_port])

        Logging.write(logging.INFO, 'Using device {}>>{}'
                      .format(Config.Io[Def.IoCfg.device_type],
                              _dmodel))

        return True

    def setup(self):

        self._pins = dict()
        self._digin_pins = list()

        for digitPin in Config.Io[Def.IoCfg.pins]:
            pin_id, num, ptype = digitPin.split(':')

            typeStr = ''
            if ptype == 'i':
                typeStr = 'input'
            elif ptype == 'o':
                typeStr = 'output'
            elif ptype == 'p':
                typeStr = 'pwm'

            msg = 'Configuration of \'{}\' for \'{}\' on pin {}'.format(pin_id, typeStr, num)
            try:
                self._pins[pin_id] = self._board.get_pin(f'd:{int(num)}:{ptype}')
                if ptype == 'i':
                    self._digin_pins.append(pin_id)
                Logging.write(logging.INFO, msg)

            except Exception as exc:
                Logging.write(logging.WARNING, '{} failed'.format(msg))

        return True

    def write(self, pin_id, value):
        self._pins[pin_id].write(value)

    def read_all(self):
        return {name : self._pins[name].read() for name in self._digin_pins}


class Virtual:

    class Pin:

        def __init__(self, pin_descr):
            from scipy.signal import sawtooth
            self.sawtooth = sawtooth
            self.descr = pin_descr
            self.pname, self.pin, self.ptype = self.descr.split(':')
            self.pin = int(self.pin)

        def read(self):
            return -0.5 + 0.1 * np.random.rand() + self.sawtooth(time.time()+self.pin/20 * 2 * np.pi * 1.0 )

    _pins = list()

    def get_pin(self, pin_descr):
        return Virtual.Pin(pin_descr)