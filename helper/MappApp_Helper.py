import configparser
import os
from PyQt5 import QtCore

import MappApp_Defaults as madflt
import MappApp_Definition as madef


class Config:

    def __init__(self, _configfile):
        self._configfile = _configfile
        self.data = configparser.ConfigParser()
        self.data.read(os.path.join(madef.Path.Config, self._configfile))

    def _parsedSection(self, section):
        parsed = dict()
        for option in self.data[section]:
            dtype = option.split('_')[0]
            if dtype == 'int':
                value = self.data.getint(section, option)
            elif dtype == 'float':
                value = self.data.getfloat(section, option)
            elif dtype == 'bool':
                value = self.data.getboolean(section, option)
            else:
                value = self.data.get(section, option)
            parsed[option] = value

        return parsed

    def displayConfiguration(self, name=None):
        # If section does not exist: create it and set to defaults
        if not(self.data.has_section(madef.DisplayConfig._name)):
            self.data.add_section(madef.DisplayConfig._name)
            for option in madflt.DisplayConfiguration:
                self.data.set(madef.DisplayConfig._name,
                              getattr(madef.DisplayConfig, option), str(madflt.DisplayConfiguration[option]))

        # Return display settings
        if name is not None:
            return self._parsedSection(madef.DisplayConfig._name)[name]
        return self._parsedSection(madef.DisplayConfig._name)

    def updateDisplayConfiguration(self, **settings):
        if not(self.data.has_section(madef.DisplayConfig._name)):
            self.displayConfiguration()

        self.data[madef.DisplayConfig._name].update(**{option : str(settings[option]) for option in settings})


    def cameraConfiguration(self, name=None):
        # If section does not exist: create it and set to defaults
        if not(self.data.has_section(madef.CameraConfiguration._name)):
            self.data.add_section(madef.CameraConfiguration._name)
            for option in madflt.CameraConfiguration:
                self.data.set(madef.CameraConfiguration._name,
                              getattr(madef.CameraConfiguration, option), str(madflt.CameraConfiguration[option]))
        # Return display settings
        if name is not None:
            return self._parsedSection(madef.CameraConfiguration._name)[name]
        return self._parsedSection(madef.CameraConfiguration._name)

    def updateCameraConfiguration(self, **settings):
        if not(self.data.has_section(madef.CameraConfiguration._name)):
            self.cameraConfiguration()

        self.data[madef.CameraConfiguration._name].update(**{option : str(settings[option]) for option in settings})


    def saveToFile(self):
        print('Save configuration to file %s' % self._configfile)
        with open(os.path.join(madef.Path.Config, self._configfile), 'w') as fobj:
            self.data.write(fobj)
            fobj.close()


def rpc(obj, data):
    fun = data[0]
    if hasattr(obj, fun) and callable(getattr(obj, fun)):
        # Retrieve call arguments
        args = list()
        if len(data) > 1:
            args = data[1]
        kwargs = dict()
        if len(data) > 2:
            kwargs = data[2]

        # Make call
        print('%s calling method %s' % (obj._name, data[0]))
        return getattr(obj, fun)(*args, **kwargs)


class Conversion:

    @staticmethod
    def boolToQtCheckstate(boolean):
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    @staticmethod
    def QtCheckstateToBool(checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False