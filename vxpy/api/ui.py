from vxpy.gui import Plotter
from vxpy import Def
from vxpy.core import ipc


def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(Def.Process.Gui, Plotter.add_buffer_attribute, attr_name, *args, **kwargs)
