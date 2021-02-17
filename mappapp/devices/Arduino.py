import logging
import numpy as np
import time

from mappapp import Logging,Def,Config


class Device:

    def connect(self):

        _dmodel = Config.Io[Def.IoCfg.device_model]

        # Set up and connect device on configured comport
        if _dmodel == 'Virtual':
            self._board = Virtual_board()
        else:
            import pyfirmata
            self._board = getattr(pyfirmata, _dmodel)(Config.Io[Def.IoCfg.device_port])

        Logging.write(Logging.INFO,f'Using device {Config.Io[Def.IoCfg.device_type]}>>{_dmodel}')

        return True

    def setup(self):

        self.pins = dict()
        self.in_pins = list()
        self.out_pins = list()

        for pin in Config.Io[Def.IoCfg.pins]:
            pin_id, pin_num, pin_type = pin.split(':')

            type_name = ''
            if 'i' in pin_type:
                type_name = 'input'
            elif 'o' in pin_type:
                type_name = 'output'
            elif pin_type == 'p':
                type_name = 'pwm'

            msg = f'Configuration of \'{pin_id}\' for \'{type_name}\' on pin {pin_num}'
            try:
                self.pins[pin_id] = self._board.get_pin(f'd:{int(pin_num)}:{pin_type}')

                if pin_type in ['ai', 'di']:
                    self.in_pins.append(pin_id)
                elif pin_type in ['ao', 'do', 'p']:
                    self.out_pins.append(pin_id)
                else:
                    Logging.write(Logging.WARNING,f'Unknown pin type {pin_type} for {pin_id}')
                    continue

                Logging.write(Logging.INFO,msg)

            except Exception as exc:
                Logging.write(logging.WARNING,f'{msg} failed')

        return True

    def write(self, **data):
        for pin_id, pin_data in data.items():
            self.pins[pin_id].write(pin_data)

    def read_all(self):
        return {name: self.pins[name].read() for name in self.in_pins}


class Virtual_board:

    class Pin:

        def __init__(self, pin_descr):
            from scipy.signal import sawtooth
            self.sawtooth = sawtooth
            self.descr = pin_descr
            self.pname, self.pin, self.ptype = self.descr.split(':')
            self.pin = int(self.pin)

        def read(self):
            return -0.5 + 0.1 * np.random.rand() + self.sawtooth(time.time()+self.pin/20 * 2 * np.pi * 1.0 )

        def write(self, data):
            pass

    def get_pin(self, pin_descr):
        return Virtual_board.Pin(pin_descr)