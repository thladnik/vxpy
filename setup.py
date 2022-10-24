from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

# Add wres~=1.0.3 for windows platform?

# Add h5gview repository
requirements.append('h5gview @ git+https://git@github.com/thladnik/h5gview.git')

setup(
    name='vxpy',
    version='0.0.1',
    packages=find_packages(include=['vxpy', 'vxpy.*']),
    include_package_data=True,
    url='',
    license='GPL 3',
    author='Tim Hladnik',
    author_email='tim.hladnik@gmail.com',
    description='vxPy - Vision experiments in Python',
    install_requires=requirements
)
