# MappApp
Multiprocess based software for visual stimulation and recording/online-analysis of behavior


## Installation

### Windows 10 (Anaconda recommended)

1. Download and install the latest release of [Anaconda](https://www.anaconda.com/distribution/) (recommended for beginners) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Either use *Anaconda Navigator* of *Anaconda Command Prompt*:
    1. Set up a new Python 3.8 environment called `mappapp` (in cmd: `conda create -n mappapp python=3.8`)
    2. Install dependencies to run MappApp
        1. Navigator packages:
            * numpy
            * pyqt
            * pyqtgraph
            * py-opencv
            * vispy
        2. In Command prompt:
            1. Activate environment: `conda activate mappapp`
            2. Install packages: `conda install numpy pyqt pyqtgraph py-opencv vispy`

## Running the application
 
Either run from IDE configured with mappapp environment by running `Startup.py`

Or use Anaconda Command Prompt (Start >> Anaconda Prompt)
1. Go to the directory to which you've downloaded/cloned MappApp with `cd path\to\mappapp`
2. Activate the environment with `conda activate mappapp`
3. EITHER run MappApp with `python Startup.py`
    * This will prompt a UI where you can create your own program configuration
4. OR if a pre-configured INI file is available
    * Make sure it is located in the `./configs` folder and instead use `python Startup.py ini=filename.ini` 

