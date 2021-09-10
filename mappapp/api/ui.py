from mappapp.gui import Plotter
from mappapp import Def
from mappapp import IPC


def register_with_plotter(attr_name: str, *args, **kwargs):
    IPC.rpc(Def.Process.Gui, Plotter.add_buffer_attribute, attr_name, *args, **kwargs)
