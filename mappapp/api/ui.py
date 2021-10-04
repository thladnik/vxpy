from mappapp.gui import Plotter
from mappapp import Def
from mappapp.core import ipc


def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(Def.Process.Gui, Plotter.add_buffer_attribute, attr_name, *args, **kwargs)
