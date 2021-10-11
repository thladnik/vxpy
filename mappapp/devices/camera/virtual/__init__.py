import sys
from mappapp.core import camera


try:
    from mappapp.devices.camera.virtual import virtual_camera
except:
    print('WARNING: api for virtual camera could not be included')
else:
    print('Using virtual cameras')
    camera._use_apis.append(virtual_camera)
