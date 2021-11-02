import sys
from vxpy.core import camera


try:
    from vxpy.devices.camera.virtual import virtual_camera
except:
    print('WARNING: api for virtual camera could not be included')
else:
    camera._use_apis.append(virtual_camera)
