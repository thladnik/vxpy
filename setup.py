from setuptools import setup, find_packages
import vxpy

with open('requirements.txt', 'r') as f:
    install_deps = f.readlines()

# Add wres~=1.0.3 for windows platform?

# Add optional dependencies
ops_deps = {
    'h5view': ['h5gview @ git+https://git@github.com/thladnik/h5gview.git@main'],
    'toolchain': ['vxpy-tools @ git+https://git@github.com/thladnik/vxPy-tools.git@main'],
    'lightcrafter': ['hidapi~=0.12.0.post2 ']
}

setup(
    name='vxpy',
    version=vxpy.__version__,
    python_requires='>=3.8',
    packages=find_packages(include=['vxpy', 'vxpy.*']),
    include_package_data=True,
    url='https://github.com/thladnik/vxpy',
    license=vxpy.__license__,
    author=vxpy.__author__,
    author_email='tim.hladnik@gmail.com',
    description='vxPy - Vision experiments in Python',
    install_requires=install_deps,
    extras_require={
        'all': install_deps + [d for deps in ops_deps.values() for d in deps],
        **{key: install_deps + deps for key, deps in ops_deps.items()}
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering'
    ],
)
