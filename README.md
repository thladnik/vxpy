# Installation

## Windows 10 (Anaconda recommended)

1. Download and install the latest release of [Anaconda](https://www.anaconda.com/distribution/) (recommended for beginners) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Set up a new environment called `glumpy`
  2.1 Open an Anaconda command prompt (Start >> type `anaconda prompt` >> Open)
  2.2 Run `conda create -n glumpy python=3.7`and confirm creation of new environment with `y`
3. Activate the newly created environment by running `conda activate glumpy`
4. Install dependencies for MappApp available via Anaconda by running
  ```
  conda install -c anaconda pyqt -y
  conda install -c anaconda scipy -y
  conda install -c anaconda pyopengl -y
  conda install -c anaconda freetype -y
  conda install -c anaconda cython -y
  ```
 5. Download [Visual Studio Community](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019). Why? Because Windows.
 6. Install Visual Studio. Under "Individual Components" select `MSVC...`
 4. Install Glumpy
 ```
 pip install triangle
 ```
