from pyfirmata import Arduino, ArduinoMega, ArduinoDue, ArduinoNano, util

class arduino(object):
    def __init__(self,device_name,device_type = 'normal'):
        if device_name == 'normal':
            self._device = Arduino(device_name)
        elif device_name == 'Mega':
            self._device = ArduinoMega(device_name)
        elif device_name == 'Due':
            self._device = ArduinoDue(device_name)
        elif device_name == 'Nano':
            self._device = ArduinoNano(device_name)
        else:
            print("Unrecognized Arduino board type")
            return -1
        self.info = (device_name,device_type)
        self._iterator = util.Iterator(self._device)
        self._iterator.start()
        self.reg_pin = {}
    def register_pin(self,pin_name,pin_def):
        pin_def = pin_def.replace(" ","")
        if pin_def[0] == 'a' and pin_def[-1] == 'p':
            print("Invalid request: analog pin for pwm output")
            return -1
        else:
            pin_def_no_column = pin_def.replace(":","")
            self.reg_pin[pin_name] = (self._device.get_pin(pin_def),pin_def_no_column )
            if self.reg_pin[pin_name][1][-1] == 'i':
                self.reg_pin[pin_name].enable_reporting()
    def read(self,pin_name):
        if pin_name in self.reg_pin.keys():
            if self.reg_pin[pin_name][1][-1] == 'i':
                return self.reg_pin[pin_name][0].read()
            else:
                print("Invalid request: reading from write-only pin")
                return -1
        else:
            print("Request for unregistered pin")
    def write(self,pin_name,val):
        if pin_name in self.reg_pin.keys():
            if self.reg_pin[pin_name][1][-1] in ['o','p']:
                return self.reg_pin[pin_name][0].write(val)
            else:
                print("Invalid request: writing to from read-only pin")
                return -1
        else:
            print("Request for unregistered pin")
    def analog(self):
        return self.get_reg_pin('a')
    def digital(self):
        return self.get_reg_pin('d')
    def writable(self):
        return self.get_reg_pin('o')+self.get_reg_pin('p')
    def readable(self):
        return self.get_reg_pin('i')
    def get_reg_pin(self,crit):
        if any(x in crit for x in 'ad'):
            filt_da =  [[p, self.reg_pin[p][0],self.reg_pin[p][1][1]] for p in self.reg_pin if self.reg_pin[p][1][0] == crit]
        else:
            filt_da = {}
        if any(x in crit for x in 'iop'):
            filt_iop = [[p, self.reg_pin[p][0],self.reg_pin[p][1][1]] for p in self.reg_pin if self.reg_pin[p][1][-1] == crit]
        else:
            filt_iop = {}
        return list(set(filt_da.items()) & set(filt_iop.items()))

    def terminate(self):
        self._iterator.join()
        self._device.exit()