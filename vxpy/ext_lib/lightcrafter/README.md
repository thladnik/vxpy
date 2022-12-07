## lightcrafter

### Installation (preliminary)

Tested under Ubuntu 18.04 (running in Windows 10's Linux Subsystem) with Python 3. For details on `hidapi`, see [here](/https://pypi.org/project/hidapi/0.7.99.post19/#install).

```
git clone https://github.com/eulerlab/lightcrafter.git
cd lightcrafter
sudo apt update
sudo apt upgrade
sudo apt install libusb-1.0-0.dev
sudo apt install libudev-dev
pip3 install numpy
git clone https://github.com/trezor/cython-hidapi.git
cd cython-hidapi
git submodule init
git submodule update
python3 setup.py build
sudo python3 setup.py install
```

Test by running:
```
python3
>>> import hid
```
... and then:
```
cd code
python3 __toVideoMode.py
```


