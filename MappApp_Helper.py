import configparser
from PyQt5 import QtCore

import MappApp_Defaults as madflt
import MappApp_Definition as madef


class Config:

    filepath = 'config.ini'

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.filepath)

    def _parsedSection(self, section):
        parsed = dict()
        for option in self.config[section]:
            dtype = option.split('_')[0]
            if dtype == 'int':
                value = self.config.getint(section, option)
            elif dtype == 'float':
                value = self.config.getfloat(section, option)
            elif dtype == 'bool':
                value = self.config.getboolean(section, option)
            else:
                value = self.config.get(section, option)
            parsed[option] = value

        return parsed

    def displaySettings(self, **kwargs):
        # If section does not exist: create it and set to defaults
        if not(self.config.has_section(madef.DisplaySettings._name)):
            self.config.add_section(madef.DisplaySettings._name)
            for option in madflt.DisplaySettings:
                self.config.set(madef.DisplaySettings._name,
                                getattr(madef.DisplaySettings, option), str(madflt.DisplaySettings[option]))
        # Return display settings
        return self._parsedSection(madef.DisplaySettings._name)

    def updateDisplaySettings(self, **settings):
        if not(self.config.has_section(madef.DisplaySettings._name)):
            self.displaySettings()

        self.config[madef.DisplaySettings._name].update(**{option : str(settings[option]) for option in settings})

    def saveToFile(self):
        with open(self.filepath, 'w') as fobj:
            self.config.write(fobj)
            fobj.close()

class Conversion:

    @staticmethod
    def boolToQtCheckstate(boolean):
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    @staticmethod
    def QtCheckstateToBool(checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False