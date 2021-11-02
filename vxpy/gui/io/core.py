"""
MappApp ./gui/io/__init__.py
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
from PyQt6 import QtWidgets

from vxpy import Def
from vxpy.core import ipc
from vxpy.core.gui import AddonWidget
from vxpy.utils.uiutils import IntSliderWidget


class IoTuner(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QGridLayout())


class TuneLedArenaFlash(AddonWidget):

    def __init__(self, *args, **kwargs):
        AddonWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())

        self.delay = IntSliderWidget('Flash delay [ms]', 0, 1000, 50, label_width=100, step_size=1)
        self.delay.connect_to_result(self.set_flash_delay)
        self.delay.emit_current_value()
        self.layout().addWidget(self.delay)
        self.duration = IntSliderWidget('Flash duration [ms]', 1, 5000, 1000, label_width=100, step_size=10)
        self.duration.connect_to_result(self.set_flash_duration)
        self.duration.emit_current_value()
        self.layout().addWidget(self.duration)
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layout().addItem(spacer)

    def set_flash_delay(self, delay):
        ipc.rpc(Def.Process.Io, TriggerLedArenaFlash.set_delay_ms, delay)

    def set_flash_duration(self, duration):
        ipc.rpc(Def.Process.Io, TriggerLedArenaFlash.set_duration_ms, duration)