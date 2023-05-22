"""
vxPy ./setup/__init__.py
Copyright (C) 2022 Tim Hladnik

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
from typing import Union
import h5py
import requests
import sys
import zipfile

import vxpy
from vxpy.definitions import *


class WorkInDirectory:
    """Context manager to change working directory to a different path temporarily"""
    def __init__(self, new_path: Union[str, None]):
        self.new_path = new_path
        self.previous_path = os.getcwd()

    def __enter__(self):
        if self.new_path is not None:
            os.chdir(self.new_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.previous_path)


def patch_dir(use_path: str = None):
    """Create potentially missing application folders in the specified base path"""

    with WorkInDirectory(use_path):
        print(f'Patch folders in vxPy application environment at {os.getcwd()}')
        # Create empty default folders
        if not os.path.exists(PATH_LOG):
            os.mkdir(PATH_LOG)
        if not os.path.exists(PATH_SAMPLE):
            os.mkdir(PATH_SAMPLE)
        if not os.path.exists(PATH_TEMP):
            os.mkdir(PATH_TEMP)
        if not os.path.exists(PATH_RECORDING_OUTPUT):
            os.mkdir(PATH_RECORDING_OUTPUT)


def setup_resources(use_path: str = None):
    """Set up the application resources on the specified base path.

    Method will first check if there is an corresponding application version
     to the currently installed vxPy core version and fallback to the vxPy_app master head version.
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
        for addr in src_addrs:
            print(f'Try {addr}')
            response = requests.get(addr)

            # Check availability
            if response.status_code == 404:
                print('Address unavailable')
                response.close()
                continue

            # Open file for download
            print(f'Download app files from {addr} to {dst_file}')
            content_length = response.headers.get('content-length')
            with open(dst_file, 'wb') as fobj:

                # If it is unknown
                if content_length is None:
                    fobj.write(response.content)
                else:
                    for data in response.iter_content(chunk_size=1024):
                        fobj.write(data)

            break

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


def download_samples(use_path: str = None):
    """Download binary sample files from vxPy core's release tag (if available)"""

    with WorkInDirectory(use_path):

        # Check availability
        source_url = f'https://github.com/thladnik/vxpy/releases/download/v{vxpy.__version__}/samples_compr.h5'
        local_path = os.path.join(PATH_SAMPLE, 'samples_compr.hdf5')

        # Connect
        response = requests.get(source_url, stream=True)

        # Check availability
        if response.status_code == 404:
            print('No sample file matching this release version found')
            response.close()
            return

        # Download, if it is available
        with open(local_path, 'wb') as fobj:
            print(f'Download sample file for release {source_url} to {local_path}')

            # If it is unknown
            content_length = response.headers.get('content-length')
            if content_length is None:
                fobj.write(response.content)
            else:
                cur_length = 0
                content_length = int(content_length)
                print(f'Downloading samples files for release at {source_url}')

                for data in response.iter_content(chunk_size=4096):
                    cur_length += len(data)
                    fobj.write(data)
                    print_download_progress(cur_length, content_length)
                    sys.stdout.flush()

        # Unpack compressed sample files
        unpack_samples()


def unpack_samples():
    """Decompress binary sample files (avoid laggs or poor performance at runtime)"""

    in_path = os.path.join(PATH_SAMPLE, 'samples_compr.hdf5')
    out_path = os.path.join(PATH_SAMPLE, 'samples.hdf5')

    with h5py.File(in_path, 'r') as fin:
        with h5py.File(out_path, 'w') as fout:
            for key in fin.keys():
                fout.create_dataset(key, data=fin[key][:])


def print_download_progress(cur_length, total_length, unit=None):
    """Print simple CLI progress bar"""

    if unit == 'B':
        num = 10**0
    elif unit == 'KB':
        num = 10 ** 3
    elif unit == 'MB':
        num = 10 ** 6
    else:
        p = total_length // 100
        if p > 10 ** 6:
            num = 10 ** 6
            unit = 'MB'
        else:
            num = 10 ** 3
            unit = 'KB'

    progress = int(100 * cur_length / total_length)
    sys.stdout.write(f'\r[{"#" * progress}{" " * (100-progress)}]'
                     + '({:.2f} / {:.2f} '.format(cur_length / num, total_length / num)
                     + f'{unit})')
