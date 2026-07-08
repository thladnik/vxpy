"""vxPy application environment setup utilities.

Provides helpers for creating and patching the vxPy application directory
structure and for downloading pre-configured application resource files from
the vxPy-app GitHub repository.
"""
from typing import Union
import requests
import zipfile

import vxpy
from vxpy.definitions import *


class WorkInDirectory:
    """WorkInDirectory class."""

    def __init__(self, new_path: Union[str, None]):
        """  init  .
        
        Parameters
        ----------
        new_path : Union[str, None]
            Description.
        """
        self.new_path = new_path
        self.previous_path = os.getcwd()

    def __enter__(self):
        """  enter  .
        """
        if self.new_path is not None:
            os.chdir(self.new_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """  exit  .
        
        Parameters
        ----------
        exc_type : Any
            Description.
        exc_val : Any
            Description.
        exc_tb : Any
            Description.
        """
        os.chdir(self.previous_path)


def patch_dir(use_path: str = None):
    """Patch dir.
    
    Parameters
    ----------
    use_path : str
        Description.
    """

    with WorkInDirectory(use_path):
        print(f'Patch folders in vxPy application environment at {os.getcwd()}')
        # Create empty default folders
        if not os.path.exists(PATH_LOG):
            os.mkdir(PATH_LOG)
        if not os.path.exists(PATH_TEMP):
            os.mkdir(PATH_TEMP)
        if not os.path.exists(PATH_RECORDING_OUTPUT):
            os.mkdir(PATH_RECORDING_OUTPUT)


def setup_resources(use_path: str = None):
    """Setup resources.
    
    Parameters
    ----------
    use_path : str
        Description.
    """

    # Patch it first to avoid missing paths
    patch_dir()

    with WorkInDirectory(use_path):
        print(f'Set up new vxPy application environment in {os.getcwd()}')

        # Download ressource files from repository
        print('Get app files')
        src_addrs = [f'https://github.com/thladnik/vxpy-app/archive/refs/tags/v{vxpy.__version__}.zip',
                     'https://github.com/thladnik/vxpy-app/archive/refs/heads/main.zip']
        dst_file = 'vxPy_app.zip'

        # Try source address order
        response = None
        for addr in src_addrs:
            print(f'Try {addr}')
            response = requests.get(addr)

            # Check availability
            if response.status_code == 404:
                print('Address unavailable')
                response.close()
                response = None
                continue

        if response is None:
            print('Failed to load application data')
            return

        # Open file for download
        print(f'Download app files from {addr} to {dst_file}')
        content_length = response.headers.get('content-length')
        with open(dst_file, 'wb') as fobj:

            # If it is unknown
            if content_length is None:
                fobj.write(response.content)
            else:
                for data in response.iter_content(chunk_size=1024):
                    # Write
                    fobj.write(data)

        # Upzip contents
        print('Unboxing')
        import shutil
        import glob
        with zipfile.ZipFile(dst_file, 'r') as f:
            f.extractall()

        for path in glob.glob('vxpy-app-main/*'):
            print(path)
            shutil.move(path, '.')

        # Clean up
        shutil.rmtree('vxPy-app-main/')
        os.remove(dst_file)

        print(f'Setup complete')
