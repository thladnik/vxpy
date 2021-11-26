import shutil
import sys
import requests
import zipfile

import vxpy
from vxpy.Def import *
from vxpy.setup import res


def setup_resources():
    # Create empty default folders
    if not os.path.exists(PATH_LOG):
        os.mkdir(PATH_LOG)
    if not os.path.exists(PATH_SAMPLE):
        os.mkdir(PATH_SAMPLE)
    if not os.path.exists(PATH_TEMP):
        os.mkdir(PATH_TEMP)
    if not os.path.exists(PATH_RECORDING_OUTPUT):
        os.mkdir(PATH_RECORDING_OUTPUT)

    # Copy all default resources
    # src_dir = res.__path__[0]
    # dst_dir = os.path.join(os.getcwd(), '.')
    # shutil.copytree(src_dir, dst_dir,
    #                 symlinks=False,
    #                 ignore=None,
    #                 copy_function=shutil.copy2,
    #                 ignore_dangling_symlinks=False,
    #                 dirs_exist_ok=True)

    print('Get app files')
    src_addrs = [f'https://github.com/thladnik/vxPy_app/archive/refs/tags/v{vxpy.__version__}.zip', 'https://github.com/thladnik/vxPy_app/archive/refs/heads/main.zip']
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
                # cur_length = 0
                # content_length = int(content_length)
                for data in response.iter_content(chunk_size=1024):
                    # cur_length += len(data)
                    fobj.write(data)
                    # print_download_progress(cur_length, content_length)
                    # sys.stdout.flush()

        break

    # Upzip contents
    print('Unboxing')
    import shutil
    import glob
    with zipfile.ZipFile(dst_file, 'r') as f:
        f.extractall()

    for path in glob.glob('vxPy_app-main/*'):
        print(path)
        shutil.move(path, '.')

    # Clean up
    shutil.rmtree('vxPy_app-main/')
    os.remove(dst_file)


def download_samples():
    source_url = f'https://github.com/thladnik/vxPy/releases/download/v{vxpy.__version__}/samples_compr.h5'
    local_path = os.path.join(PATH_SAMPLE, 'samples_compr.h5')

    # Connect
    response = requests.get(source_url, stream=True)

    # Check availability
    if response.status_code == 404:
        print('No sample file matching this release version found')
        response.close()
        return

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


def print_download_progress(cur_length, total_length, unit=None):

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
