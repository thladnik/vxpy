from setuptools import setup

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

setup(
    name='vxpy',
    version='0.0.1',
    packages=['vxpy', 'vxpy.api', 'vxpy.gui', 'vxpy.gui.io', 'vxpy.gui.camera', 'vxpy.gui.display',
              'vxpy.lib', 'vxpy.lib.pyapi', 'vxpy.core', 'vxpy.configure', 'vxpy.configure.camera',
              'vxpy.configure.display', 'vxpy.utils', 'vxpy.devices', 'vxpy.devices.camera',
              'vxpy.devices.camera.tis', 'vxpy.devices.camera.virtual', 'vxpy.modules', 'vxpy.routines',
              'vxpy.routines.io', 'vxpy.routines.camera', 'vxpy.routines.display', 'vxpy.setup'],
    url='',
    license='GPL 3',
    author='Tim Hladnik',
    author_email='tim.hladnik@gmail.com',
    description='vxPy - Something for vision experiments',
    install_requires=requirements
)
