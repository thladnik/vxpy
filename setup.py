from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

setup(
    name='vxpy',
    version='0.0.1',
    packages=find_packages(include=['vxpy', 'vxpy.*']),
    include_package_data=True,
    url='',
    license='GPL 3',
    author='Tim Hladnik',
    author_email='tim.hladnik@gmail.com',
    description='vxPy - Something for vision experiments',
    install_requires=requirements
)
