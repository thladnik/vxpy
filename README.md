<h1 align="center">
<img src="https://raw.githubusercontent.com/thladnik/vxpy/d535fb2760869eaf18000ba0d6425815b8cd8f03/vxpy/vxpy_icon.svg" width="200">
</h1><br>

**VxPy** is a multiprocessing-based software for vision experiments in Python. 

It leverages OpenGL-based 3D graphics rendering, using the Python visualization library [VisPy](https://github.com/vispy/vispy), for dynamic generation and realtime updating of visual stimuli. VxPy utilizes multicore hardware for fast online aquisition and analysis of behavioral and other sensor data, as well as control of external devices, such as actuators or LEDs, via configurable microcontroller interfaces. 

This is the core package for VxPy. The accompanying application to configure and run it is available at [VxPy-app](https://github.com/thladnik/vxPy_app).

## Requirements

VxPy has been tested on Windows 11 and Ubuntu 20.04, 22.04 and 24.04 LTS. It requires Python 3.8 or higher. For best performance **Ubuntu is recommended**.

## Quick start guide

* Running VxPy
* Creating a visual stimulus
* Creating an online analysis routine

## Roadmap

### Version 0.2: consolidation of core functions and integration of frequently used application-side code into core 
For version 0.2 the core function API of VxPy v0.1.x (legacy API) will be consolidated and fixed in place for future compatibility with existing experiments. 
At the same time, plugins, controls, visuals and devices that were added to [VxPy-app](https://github.com/thladnik/vxPy_app) initially and are in use by multiple protocols regularly will be integrated into the VxPy core module. 
Patches to fix remaining bugs will continue to be released under the v0.2.x release tags for the foreseeable future, but no new features will be added.

### Version 0.3: API changes and introduction of DAG-like architecture
For version 0.3 some core design features of VxPy will be reworked. 
This will necessarily come with some changes to the core function API. 
However, most existing implementations of custom plugins and devices should be able to migrate to 0.3 with minimal changes.

There are two main reasons for these design changes
1) **Improving performance** of VxPy to enable more complex and computation-intensive experimental designs (such as the existing DeepLabCut tracking or the multiplane 2-photon fluorescence imaging analysis at resonant imaging frame rates)
2) Making future **code refactors easier** through a better separation of different VxPy core functions

Some of the planned changes include
* **Implementation of an explicit directed acyclical graph (DAG) like architecture** (formerly implemented through the `_load_order` of plugins and custom signal triggers). 
   This will enable separate routines - even logically connected ones - to run on individual processes and also help with the separation of sources, computations and sinks.
* Allowing **multiple instances of analysis routines** on separate DAG branches. 
   Currently in VxPy, an analysis routine can be access from remote processes through the class's `instance` method to read out shared values or configuration states.
   However, this also means that any routine may at most have one instance running at any time. 
   In cases where multiple instances are required, subclasses have to be used, which in turn can lead to inheritance issues for shared values. 
   This change would allow for instances of a routine to run completely separately on their respective subtrees.  
* **Addition of dynamic shared attributes** that can be added at runtime by making use of the `shared_memory` module added with Python 3.8. 
   Previously, shared attributes that are available across all processes, had to be declared at program start. 
   With multiprocessing features that were added with Python 3.8 (after VxPy's inception) many of the former limitations on memory allocation were lifted. 
   This change will make it easier to create analysis routines which have very large and/or variable numbers of output variables (such as for example the results of image segmentations) and decrease overall memory requirements.
* **Implementation of backend agnostic user interface API**. 
   Currently, communication between the UI and other parts of VxPy is mostly (with some exceptions in the core UI) achieved through state-dependent changes. 
   This makes debugging of problems easier for custom routines, but may also be less intuitive and clunky when planning and implementing the program flow.
   A generic UI-program interface would help with this be providing a dedicated way of communication between the analysis routine and its user interface.

## Installation

### Installing Python

#### Windows
Download and install the Python 3.8+ binaries if not already installed from https://www.python.org/downloads/

#### Ubuntu

Run command in a terminal to install desired Python version (e.g. 3.10)
```console
user@machine: ~$ sudo apt-get install python3.x 
```

### Installing VxPy

Create a new folder where you'd like to install the vxPy application (here `vxpy-app`).
Using a terminal, create a virtual environment inside the empty folder, install VxPy and set up the application folder 
```console
user@machine: ~/vxpy-app$ python3.x -m venv venv
user@machine: ~/vxpy-app$ ./venv/bin/activate
(venv) user@machine: ~/vxpy-app$ pip install vxpy
(venv) user@machine: ~/vxpy-app$ vxpy setup
```

You can then run the default demo configuration with
```console
(venv) user@machine: ~/vxpy-app vxpy -c configurations/example.yaml run
```
Upon first start, VxPy will download demo data files, which may take some additional time.

### Notes on dependencies

* Because of changes with regard to multiple inheritances in PySide6 (https://bugreports.qt.io/browse/PYSIDE-1564), PySide is currently locked to 6.4.3 until this issue is patched in VxPy. This also requires NumPy to be locked to the latest 1.x release (1.26.4).

## Compatible devices

### Cameras

#### TheImagingSource (TIS) cameras
Under Windows [TIS](https://www.theimagingsource.de/) cameras are supported out of the box, using the TIS' original `tisgrabber` DLLs and their `ctype` bindings included in vxPy.

In order to use TIS cameras under Linux, you need to install `tiscamera` ([Github repository](https://github.com/TheImagingSource/tiscamera)) by following the instructions there. 

Within the Python environment, you then need to install `pycairo` and `PyGObject` with
```console
(venv) user@machine: ~/vxpy-app$ pip install pycairo PyGObject
```

**WARNING**: starting with version 1.0.0, `tiscamera` no longer supports older camera models (see table [supported devices](https://www.theimagingsource.com/en-us/documentation/tiscamera/supported-devices.html)). 
If you're using one of those, instead install the latest pre-1.0.0 stable release (0.14.0) by checking it out with
```console
user@machine: ~/tiscamera$ git checkout tags/v-tiscamera-0.14.0
```
directly after cloning the repository and before installing the dependencies or building the binaries.

#### Basler cameras

[Basler](https://www.baslerweb.com/) cameras are supported for Windows and Linux. Just download the `pylon` installer for your plattform from the [Basler website](https://www.baslerweb.com/de/downloads/downloads-software/#type=pylonsoftware;language=all;version=all).

Then install the respective Python `pypylon` package into your environment with
```console
(venv) user@machine: ~/vxpy-app$ pip install gst PyGObject pypylon
```

#### Adding a camera

Cameras can be added via the configuration manager
```console
(venv) user@machine: ~/vxpy-app$ vxpy -c path/to/config.yaml configure
```

or directly by adding them to the configuration file
```YAML
CAMERA_DEVICES:
  camera01_behavior:
    api: vxpy.devices.camera.basler_pylon.BaslerCamera
    serial: 12345
    model: a2A1920-160umBAS
    width: 1936
    height: 1216
    frame_rate: 80
    basler_props:
      BinningHorizontalMode: Average
      BinningHorizontal: 1
      BinningVerticalMode: Average
      BinningVertical: 1
      GainAuto: false
      Gain: 20
      ExposureAuto: false
      ExposureTime: 10000
```

### DAQs 

Internally, VxPy uses the standard [Firmata](https://github.com/firmata/arduino) protocol for synchronization and communication with external application and devices via Arduino (and Arduino-compatible) devices. 

To the user, aquisition or writing of analog and digital signals is easily accessible through the configurable IO interface by adding devices and PINs to the configuration YAML file:
```YAML
IO_DEVICES:
  Dev1_microscope:
    api: vxpy.devices.arduino_daq.ArduinoDaq
    model: Arduino
    port: /dev/ttyACM1
    pins:
      y_mirror_in:
        type: analog
        direction: input
        map: a:1:i # PIN 1 analog input
      frame_sync:
        type: digital
        direction: input
        map: d:2:i # PIN 2 digital input
      frame_trigger_out:
        type: digital
        direction: output
        map: d:3:o  # PIN 3 digital output
```

For more advanced use-cases (e.g. when programming routines for realtime analysis in VxPy), all configured IO devices and their PINs are also directly available in the Python script. 

Configured devices can either be directly accessed through their SerialDevice instance
```Python
import vxpy.core.devices.serial as vxserial

device = vxserial.get_serial_device_by_id('Dev1_microscope')
device.board.get_pin('d:3:o').write(1)
```

and individual, configured PINs can be written to automatically from attributes that are created in a `vxPy` analysis routine
```Python

import vxpy.core.io as vxio

vxio.set_digital_output('frame_trigger_out', 'frame_trigger_attribute') 
```

