from vxpy.gui.window_widgets import PlottingWindow
from vxpy.core.gui import AddonWidget
from vxpy import Def
from vxpy.core import ipc

def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(Def.Process.Gui, PlottingWindow.add_buffer_attribute, attr_name, *args, **kwargs)
