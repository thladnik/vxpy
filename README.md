# vxPy

Multiprocess based software for vision experiments in Python

## Requirements

vxPy has been tested on Windows 10 and Ubuntu 20.04 LTS. It requires Python 3.8+

## Installation

### Installing Python

#### Windows
Download and install the Python 3.8+ binaries if not already installed from https://www.python.org/downloads/

#### Ubuntu

Install from canonical 
```
> sudo apt-get install python3.x 
```

### Install vxPy with PyCharm (recommended)

TODO

### Install vxPy with terminal

#### Ubuntu

Create a new folder where you'd like to install the vxPy application (here ~/vxPy_app/)
Using a terminal, create a virtual environment inside the empty folder 
```
~/vxPy_app> python3.x -m venv venv 
```

Activate the environment
```
~/vxPy_app> ./venv/bin/activate
```

Install vxPy with all its dependencies
```
<venv> ~/vxPy_app> pip install git+https://github.com/thladnik/vxpy.git
```

Run vxPy setup to create application structure
```
<venv> ~/vxPy_app> python -m vxpy setup
```
Alternatively, you can forego downloading sample files 
```
<venv> ~/vxPy_app> python -m vxpy setup nosamples
```
**WARNING**: the demonstration in default.ini requires the sample files to run properly

You can run the default configuration with
```
 <venv> ~/vxPy_app>python main.py
```