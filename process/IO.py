"""
MappApp ./process/IO.py - General purpose digital/analog input/output process.
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

import logging
from time import sleep

import Controller
import Definition
from devices import Arduino
import Logging

class Main(Controller.BaseProcess):
    name = Definition.Process.IO

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(**kwargs)

        try:
            Arduino.getSerialConnection()
        except:
            Logging.logger.log(logging.INFO, 'No connected serial device found.')


    def main(self):
        sleep(0.1)