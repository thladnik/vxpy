from vxpy.definitions import DeviceType

required = []
registered = []


def require_device(dev_type: DeviceType, dev_name: str):
    global required
    if (dev_type, dev_name) not in required:
        required.append((dev_type, dev_name))


def require_camera_device(dev_name: str):
    require_device(DeviceType.Camera, dev_name)


def require_io_device(dev_name: str):
    require_device(DeviceType.Camera, dev_name)


def register_device(dev_type: DeviceType, dev_name: str):
    global registered
    if (dev_type, dev_name) not in registered:
        registered.append((dev_type, dev_name))


def register_camera_device(dev_name: str):
    register_device(DeviceType.Camera, dev_name)


def register_io_device(dev_name: str):
    register_device(DeviceType.Camera, dev_name)


def assert_device_requirements():
    global registered, required

    for device in required:
        assert device in registered, f'Required device {device} not configured'
