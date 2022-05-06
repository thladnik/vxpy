from vxpy.definitions import *
from vxpy.core import ipc
from vxpy.addons import core_widgets

def register_with_plotter(attr_name: str, *args, **kwargs):
    ipc.rpc(PROCESS_GUI, core_widgets.PlottingWindow.add_buffer_attribute, attr_name, *args, **kwargs)
