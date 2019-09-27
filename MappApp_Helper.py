import configparser
from collections import namedtuple

import MappApp_Definition as madef

class Config:

    filename = 'config.ini'

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.filename)

    def _parsedSection(self, section, return_dict=False):
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
                value = self.config.getboolean(section, option)
            parsed[option] = value

        if return_dict:
            return parsed
        return namedtuple(section, parsed.keys())(*parsed.values())

    def displaySettings(self):
        if self.config.has_section(madef.DisplaySettings.name):
            return self._parsedSection(madef.DisplaySettings.name)
        return None

    def setDisplaySettings(self, **settings):
        if not(self.config.has_section(madef.DisplaySettings.name)):
            self.config.add_section(madef.DisplaySettings.name)

        self.config[madef.DisplaySettings.name].update(settings)
