import logging
import pyfirmata

import Config
import Def
import Logging

class Device:

    def connect(self):

        _dmodel = Config.IO[Def.IoCfg.device_model]

        ### Set up and connect device on configured comport
        self._board = getattr(pyfirmata, _dmodel)(Config.IO[Def.IoCfg.device_port])

        Logging.write(logging.INFO, 'Using device {}>>{}'
                      .format(Config.IO[Def.IoCfg.device_type],
                              _dmodel))

        return True

    def setup(self):

        self._digital = dict()

        for digitPin in Config.IO[Def.IoCfg.digital_pins]:
            name, num, type, sr = digitPin.split(':')

            typeStr = ''
            if type == 'i':
                typeStr = 'input'
            elif type == 'o':
                typeStr = 'output'
            elif type == 'p':
                typeStr = 'pwm'

            try:
                self._digital[name] = self._board.get_pin('d:{}:{}'.format(int(num), type))

                Logging.write(logging.INFO, 'Configured \'{}\' for \'{}\' on pin {}'
                              .format(name, typeStr, num))
            except Exception as exc:
                Logging.write(logging.WARNING, 'Configuration of \'{}\' for \'{}\' on pin {} failed'
                              .format(name, typeStr, num))



        return True