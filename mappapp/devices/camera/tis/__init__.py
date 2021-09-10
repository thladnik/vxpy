import sys
from mappapp.core import camera


if sys.platform == 'linux':
    try:
        from mappapp.devices.camera.tis import gst_linux
    except:
        print('WARNING: linux api for TIS could not be included')
    else:
        print('Using gst_linux cameras')
        camera._use_apis.append(gst_linux)

elif sys.platform == 'win32':
    pass