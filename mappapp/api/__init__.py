"""
MappApp ./api/__main__.py
Controller spawns all sub processes.
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
from mappapp import Config
from mappapp import Def
from mappapp import IPC
from mappapp import modules


def get_time():
    return IPC.Process.global_t


def camera_rpc(function, *args, **kwargs):
    IPC.rpc(Def.Process.Camera, function, *args, **kwargs)


def display_rpc(function, *args, **kwargs):
    IPC.rpc(Def.Process.Display, function, *args, **kwargs)


def gui_rpc(function, *args, **kwargs):
    IPC.rpc(Def.Process.Gui, function, *args, **kwargs)


def io_rpc(function, *args, **kwargs):
    IPC.rpc(Def.Process.Io, function, *args, **kwargs)


def set_digital_output(out_pid, attr_name):
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, attr_name)


def set_analog_output(out_pid, routine_cls, attr_name):
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, routine_cls, attr_name)


def set_display_uniform_attribute(uniform_name, routine_cls, attr_name):
    display_rpc(modules.Display.set_display_uniform_attribute, uniform_name, routine_cls, attr_name)
