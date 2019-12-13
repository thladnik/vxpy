import configparser
from PyQt5 import QtCore

import MappApp_Defaults as madflt
import MappApp_Definition as madef


class Config:

    filepath = 'config.ini'

    def __init__(self):
        self.data = configparser.ConfigParser()
        self.data.read(self.filepath)

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

    def displaySettings(self, **kwargs):
        # If section does not exist: create it and set to defaults
        if not(self.data.has_section(madef.DisplayConfiguration._name)):
            self.data.add_section(madef.DisplayConfiguration._name)
            for option in madflt.DisplayConfiguration:
                self.data.set(madef.DisplayConfiguration._name,
                              getattr(madef.DisplayConfiguration, option), str(madflt.DisplayConfiguration[option]))
        # Return display settings
        return self._parsedSection(madef.DisplayConfiguration._name)

    def updateDisplaySettings(self, **settings):
        if not(self.data.has_section(madef.DisplayConfiguration._name)):
            self.displaySettings()

        self.data[madef.DisplayConfiguration._name].update(**{option : str(settings[option]) for option in settings})

    def saveToFile(self):
        with open(self.filepath, 'w') as fobj:
            self.data.write(fobj)
            fobj.close()

class Sessiondata:

    filepath = 'sessiondata.ini'

    def __init__(self):
        self.data = configparser.ConfigParser()
        self.data.read(self.filepath)

    def rpcSettings(self):
        if not(self.data.has_section('rpc')):
            self.data.add_section(madef.DisplayConfiguration._name)

    def saveToFile(self):
        with open(self.filepath, 'w') as fobj:
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