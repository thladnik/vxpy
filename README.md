# MappApp
Software for visual stimulation and recording/online-analysis of behavior


## Installation

### Windows 10 (Anaconda recommended)

1. Download and install the latest release of [Anaconda](https://www.anaconda.com/distribution/) (recommended for beginners) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Set up a new environment called `mappapp`
    1. Open an Anaconda command prompt (Start >> type `anaconda prompt` >> Open)
    2. Run `conda create -n mappapp python=3.7`and confirm creation of new environment with `y`
3. Activate the newly created environment by running `conda activate mappapp`
4. Install basic dependencies for MappApp with `pip install pyqt5 pyqtgraph pyglet scipy scikit-learn pyopengl cython h5py opencv-python keyboard imageio pyfirmata`
5. Install `glumpy`
    1. Download [Visual Studio Community Edition](https://visualstudio.microsoft.com/downloads/). Why? Because Windows.
    2. Install Visual Studio. Under "Individual Components" select `Windows 10 SDK (10.0.18362.0)` and `MSVC v140 VS 2015 C++ build tools (v14.00)` and run install/update.
    3. Install freetype with `conda install -c anaconda freetype` (necessary dependency for glumpy)
    4. Run `pip install triangle glumpy`. **IF** the setup for either of these **fails** with the message `LINK : fatal error LNK1158: cannot run 'rc.exe'`, follow these steps:
        1. Locate the folder `C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x86` and copy the files rc.exe and rcdll.dll
        2. Paste both files to `C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\x86_amd64`
        3. Try step (iv) again
6. Download the current master release of MappApp to a folder or clone the branch using `git`.

## Running the application
 
1. Open an Anaconda prompt (Start >> Anaconda prompt)
2. Go to the directory to which you've downloaded MappApp with `cd path\to\mappapp`
2. Activate the environment with `conda activate mappapp`

### Setup application
Before using the application a configuration file has to be created. This can be done simply by executing the `Startup.py` script (`python Startup.py`).

### Start application
Run `python Startup.py --skip_setup` to start with default .INI file
