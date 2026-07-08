"""Inter-process I/O convenience wrappers for vxPy.

Provides thin wrappers around IPC remote procedure calls targeting
the Io process.
"""
from vxpy import modules
from vxpy.core.ipc import io_rpc


def set_digital_output(out_pid, attr_name):
    """Set digital output.
    
    Parameters
    ----------
    out_pid : Any
        Identifier of the digital output pin to control.
    attr_name : Any
        Name of the shared attribute whose values are forwarded to the pin.
    """
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, attr_name)


def set_analog_output(out_pid, attr_name):
    """Set analog output.
    
    Parameters
    ----------
    out_pid : Any
        Identifier of the analog output pin to control.
    attr_name : Any
        Name of the shared attribute whose values are forwarded to the pin.
    """
    io_rpc(modules.Io.set_outpin_to_attr, out_pid, attr_name)
