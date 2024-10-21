
[//]: # (<img align="right" width="140" height="140" src="vxpy/vxpy_icon.png">)
<img align="right" width="140" height="140" src="https://raw.githubusercontent.com/thladnik/vxPy/3e75107a8dc7e70b898c50e8b95209126ed3f856/vxpy/vxpy_icon.svg">


# vxPy

`vxPy` is a multiprocessing-based software for vision experiments in Python. 

It leverages OpenGL-based 3D graphics rendering, using the Python visualization library [VisPy](https://github.com/vispy/vispy), for dynamic generation and realtime updating of visual stimuli. `vxPy` utilizes multicore hardware for fast online aquisition and analysis of behavioral and other sensor data, as well as control of external devices, such as actuators or LEDs, via configurable microcontroller interfaces. 

This is the core package for `vxPy`. The accompanying application to configure and run the UI is hosted at [vxPy_app](https://github.com/thladnik/vxPy_app).

## Requirements

`vxPy` has been tested on Windows 11 and Ubuntu 20.04 and 22.04 LTS. It requires Python 3.8 or higher. For best performance Ubuntu is recommended.

## Installation

### Installing Python

#### Windows
Download and install the Python 3.8+ binaries if not already installed from https://www.python.org/downloads/

#### Ubuntu

Install Python 
```console
user@machine: ~$ sudo apt-get install python3.x 
```

### Installing vxPy

#### Linux

Create a new folder where you'd like to install the vxPy application (here`vxPy_app`).
Using a terminal, create a virtual environment inside the empty folder, install `vxPy` and set up the application folder 
```console
user@machine: ~/vxPy_app$ python3.x -m venv venv
user@machine: ~/vxPy_app$ ./venv/bin/activate
(venv) user@machine: ~/vxPy_app$ pip install vxpy
(venv) user@machine: ~/vxPy_app$ vxpy setup
```

You can then run the default demo configuration with
```console
(venv) user@machine: ~/vxPy_app$ vxpy -c configurations/example.yaml run
```
Upon first start, vxpy will download demo data files, which may take some additional time.

## Compatible devices

### Cameras

#### TheImagingSource (TIS) cameras
Under Windows [TIS](https://www.theimagingsource.de/) cameras are supported out of the box, using the TIS' original `tisgrabber` DLLs and their `ctype` bindings included in vxPy.

In order to use TIS cameras under Linux, you need to install `tiscamera` ([Github repository](https://github.com/TheImagingSource/tiscamera)) by following the instructions there. 

Within the Python environment, you then need to install `pycairo` and `PyGObject` with
```console
(venv) user@machine: ~/vxPy_app$ pip install pycairo PyGObject
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
(venv) user@machine: ~/vxPy_app$ pip install gst PyGObject pypylon
```

#### Adding a camera

Cameras can be added via the configuration manager
```console
(venv) user@machine: ~/vxPy_app$ vxpy -c path/to/config.yaml configure
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

Internally, `vxPy` uses the standard [Firmata](https://github.com/firmata/arduino) protocol for synchronization and communication with external application and devices via Arduino (and Arduino-compatible) devices. 

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

For more advanced use-cases (e.g. when programming routines for realtime analysis in `vxPy`), all configured IO devices and their PINs are also directly available in the Python script. 

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

