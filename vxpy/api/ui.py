from vxpy.core.gui import AddonWidget
from vxpy.definitions import *
from vxpy.core import ipc
import vxpy.core.gui as vxgui

def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(PROCESS_GUI, vxgui.PlottingWindow.add_buffer_attribute, attr_name, *args, **kwargs)
