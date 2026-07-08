from vxpy.definitions import DeviceType

required = []
registered = []


def require_device(dev_type: DeviceType, dev_name: str):
    """Register a device as required for the experiment.

    Parameters
    ----------
    dev_type : DeviceType
        Type of the device (e.g., Camera, IO).
    dev_name : str
        Name identifier of the device.
    """
    global required
    if (dev_type, dev_name) not in required:
        required.append((dev_type, dev_name))


def require_camera_device(dev_name: str):
    """Require camera device.
    
    Parameters
    ----------
    dev_name : str
        Camera device identifier that must be configured.
    """
    require_device(DeviceType.Camera, dev_name)


def require_io_device(dev_name: str):
    """Require io device.
    
    Parameters
    ----------
    dev_name : str
        I/O device identifier that must be configured.
    """
    require_device(DeviceType.Camera, dev_name)


def register_device(dev_type: DeviceType, dev_name: str):
    """Register device.
    
    Parameters
    ----------
    dev_type : DeviceType
        Device category being registered.
    dev_name : str
        Device identifier provided by configuration.
    """
    global registered
    if (dev_type, dev_name) not in registered:
        registered.append((dev_type, dev_name))


def register_camera_device(dev_name: str):
    """Register camera device.
    
    Parameters
    ----------
    dev_name : str
        Camera device identifier available at runtime.
    """
    register_device(DeviceType.Camera, dev_name)


def register_io_device(dev_name: str):
    """Register io device.
    
    Parameters
    ----------
    dev_name : str
        I/O device identifier available at runtime.
    """
    register_device(DeviceType.Camera, dev_name)


def assert_device_requirements():
    """Assert device requirements.
    """
    global registered, required

    for device in required:
        assert device in registered, f'Required device {device} not configured'
