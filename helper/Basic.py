"""
MappApp ./Basic.py - Collections of helper functions and classes.
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

import configparser
import json
import os
from PyQt5 import QtCore

import Default
import Def




class ConfigParser(configparser.ConfigParser):

    class ConfigTypeError(TypeError):
        """Raise when config option has the wrong type"""
        pass

    def __init__(self, *_args, **_kwargs):
        configparser.ConfigParser.__init__(self, *_args, **_kwargs)

        self.filenames = None

    def read(self, filenames, encoding=None):
        if isinstance(filenames, list):
            filenames = [os.path.join(Def.Path.Config, f) for f in filenames]
        else:
            filenames = os.path.join(Def.Path.Config, filenames)

        self.filenames = filenames

        configparser.ConfigParser.read(self, filenames, encoding=encoding)

    def saveToFile(self):
        print('Save config to file {}'.format(self.filenames))
        with open(self.filenames, 'w') as fobj:
            self.write(fobj)
            fobj.close()

    def getParsed(self, section, option):
        dtype = option.split('_')[0]
        if dtype == 'int':
            value = self.getint(section, option)
        elif dtype == 'float':
            value = self.getfloat(section, option)
        elif dtype == 'bool':
            value = self.getboolean(section, option)
        elif dtype == 'list':
            value = json.loads(self.get(section, option))
        else:
            value = self.get(section, option)

        return value

    def setParsed(self, section, option, value):
        dtype = option.split('_')[0]
        if dtype == 'list':
            if not(isinstance(value, list)):
                raise ConfigParser.ConfigTypeError
            self.set(section, option, json.dumps(value))

        else:
            self.set(section, option, str(value))

    def getParsedSection(self, section):

        parsed = dict()
        for option in self[section]:
            parsed[option] = self.getParsed(section, option)

        return parsed



class Config:

    def __init__(self, _configfile=None):
        self._configfile = _configfile
        self.data = configparser.ConfigParser()

        if not(self._configfile is None):
            self.data.read(os.path.join(Def.Path.Config, self._configfile))

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
            elif dtype == 'list':
                value = self.data.get(section, option).split(',')
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
        for option, value in settings.items():
            #self.data[config.name].update(**{option : str(settings[option]) for option in settings})
            dtype = option.split('_')[0]
            if dtype == 'list':
                value = ','.join(value)
            self.data[config.name][option] = str(value)

    def saveToFile(self):
        with open(os.path.join(Def.Path.Config, self._configfile), 'w') as fobj:
            self.data.write(fobj)
            fobj.close()


class Conversion:

    @staticmethod
    def boolToQtCheckstate(boolean):
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    @staticmethod
    def QtCheckstateToBool(checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False