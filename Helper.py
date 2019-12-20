import configparser
import os
from PyQt5 import QtCore

import Default
import Definition

class Config:

    def __init__(self, _configfile):
        self._configfile = _configfile
        self.data = configparser.ConfigParser()
        self.data.read(os.path.join(Definition.Path.Config, self._configfile))

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

    def configuration(self, config, property = None):
        # If section does not exist: create it and set to defaults
        if not(self.data.has_section(config.name)):
            self.data.add_section(config.name)
            for option in Default.Configuration[config.name]:
                self.data.set(config.name,
                              option,
                              str(Default.Configuration[config.name][option]))

        # Return display settings
        if property is not None:
            return self._parsedSection(config.name)[property]
        return self._parsedSection(config.name)

    def updateConfiguration(self, config, **settings):
        # If section does not exist, create it
        if not(self.data.has_section(config.name)):
            self.configuration(config)

        # Update settings
        self.data[config.name].update(**{option : str(settings[option]) for option in settings})

    def saveToFile(self):
        with open(os.path.join(Definition.Path.Config, self._configfile), 'w') as fobj:
            self.data.write(fobj)
            fobj.close()

class Conversion:

    @staticmethod
    def boolToQtCheckstate(boolean):
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    @staticmethod
    def QtCheckstateToBool(checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False