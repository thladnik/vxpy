from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    install_deps = f.readlines()

# Add wres~=1.0.3 for windows platform?

# Add h5gview repository
# requirements.append('h5gview @ git+https://git@github.com/thladnik/h5gview.git')

toolchain_deps = install_deps + ['vxpy-tools @ git+https://git@github.com/thladnik/vxPy-tools.git@main']

lightcrafter_deps = install_deps + ['hidapi~=0.12.0.post2 ']

setup(
    name='vxpy',
    version='0.0.1',
    python_requires='>=3.10',
    packages=find_packages(include=['vxpy', 'vxpy.*']),
    include_package_data=True,
    url='',
    license='GPL 3',
    author='Tim Hladnik',
    author_email='tim.hladnik@gmail.com',
    description='vxPy - Vision experiments in Python',
    install_requires=install_deps,
    extras_require={'toolchain': toolchain_deps,
                    'lightcrafter': lightcrafter_deps}
)
