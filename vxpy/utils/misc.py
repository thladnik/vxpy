"""
MappApp ./utils/misc.py
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
import importlib
import json
import os
from PySide6 import QtCore

from vxpy.definitions import *
from vxpy import definitions
from vxpy.definitions import *


class ConfigParser(configparser.ConfigParser):

    class ConfigTypeError(TypeError):
        """Raise when config option has the wrong type"""
        pass

    def __init__(self, *_args, **_kwargs):
        configparser.ConfigParser.__init__(self, *_args, **_kwargs)

        self.filenames = None

    def _verify_filename(self, fn):
        # Search on local path
        path = os.path.join(PATH_CONFIG, fn)
        if os.path.exists(path):
            return path

        raise Exception(f'Config file {fn} could not be found')

    def read(self, filenames, encoding=None):
        if isinstance(filenames, list):
            filenames = [self._verify_filename(fn) for fn in filenames]
        else:
            filenames = self._verify_filename(filenames)

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
        elif dtype == 'json':
            value = json.loads(self.get(section, option))
        else:
            value = self.get(section, option)

        return value

    def setParsed(self, section, option, value):
        dtype = option.split('_')[0]
        if dtype == 'json':
            self.set(section, option, json.dumps(value))

        else:
            self.set(section, option, str(value))

    def getParsedSection(self, section):

        parsed = dict()
        for option in self[section]:
            parsed[option] = self.getParsed(section, option)

        return parsed


class Conversion:

    @staticmethod
    def boolToQtCheckstate(boolean):
        return QtCore.Qt.Checked if boolean else QtCore.Qt.Unchecked

    @staticmethod
    def QtCheckstateToBool(checkstate):
        return True if (checkstate == QtCore.Qt.Checked) else False