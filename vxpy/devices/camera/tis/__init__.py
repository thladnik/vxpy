import sys
from vxpy.core import camera


if sys.platform == 'linux':
    try:
        from vxpy.devices.camera.tis import gst_linux
    except:
        print('WARNING: linux api for TIS could not be included')
    else:
        print('Using gst_linux cameras')
        if gst_linux not in camera._use_apis:
            camera._use_apis.append(gst_linux)

elif sys.platform == 'win32':
    pass