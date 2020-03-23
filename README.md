# MappApp
Software for visual stimulation and recording/online-analysis of behavior

## Installation

### Windows 10 (Anaconda recommended)

1. Download and install the latest release of [Anaconda](https://www.anaconda.com/distribution/) (recommended for beginners) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Set up a new environment called `glumpy`
    1. Open an Anaconda command prompt (Start >> type `anaconda prompt` >> Open)
    2. Run `conda create -n glumpy python=3.7`and confirm creation of new environment with `y`
3. Activate the newly created environment by running `conda activate glumpy`
4. Install basic dependencies for MappApp with `pip install pyqt5 pyqtgraph pyglet scipy scikit-learn pyopengl cython h5py opencv-python keyboard imageio`
5. Install `glumpy`
    1. Download [Visual Studio Community Edition](https://visualstudio.microsoft.com/downloads/). Why? Because Windows.
    2. Install Visual Studio. Under "Individual Components" select `MSVC v140 VS 2015 C++ build tools (v14.00)`
    3. Install freetype with `conda install -c anaconda freetype` (necessary dependency for glumpy)
    4. Run `pip install triangle glumpy`
6. Download the current master release of MappApp to a folder or clone the branch using `git`.

## Running the application
 
1. Open an Anaconda prompt (Start >> Anaconda prompt)
2. Go to the directory to which you've downloaded MappApp with `cd path\to\mappapp`
2. Activate the environment with `conda activate glumpy`

### Setup application
Before using the application a configuration file has to be created. This can be done simply by executing the `Startup.py` script (`python Startup.py`).

### Start application
Run `python Controller.py`
