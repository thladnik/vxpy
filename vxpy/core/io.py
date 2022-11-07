"""
MappApp ./api/io.py
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
from vxpy import modules
from vxpy.core.ipc import io_rpc


def set_digital_output(out_pid, attr_name):
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, attr_name)


def set_analog_output(out_pid, attr_name):
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, attr_name)
