import os
import shutil
import sys
import requests

from vxpy.Def import *
from vxpy.setup import res


def setup_resources():
    # Copy all default resources
    src_dir = res.__path__[0]
    dst_dir = os.path.join(os.getcwd(), '.')
    shutil.copytree(src_dir, dst_dir,
                    symlinks=False,
                    ignore=None,
                    copy_function=shutil.copy2,
                    ignore_dangling_symlinks=False,
                    dirs_exist_ok=True)


def download_samples():
    source_url = 'https://github.com/thladnik/vxPy/releases/download/v0.0.1-alpha/samples_compr.h5'
    local_path = os.path.join(PATH_SAMPLE, 'samples_compr.h5')

    with open(local_path, 'wb') as fobj:
        print(f'Attempt to download sample file {source_url}')

        response = requests.get(source_url, stream=True)
        content_length = response.headers.get('content-length')

        # If it is unknown
        if content_length is None:
            fobj.write(response.content)
        else:
            cur_length = 0
            content_length = int(content_length)
            print(f'Downloading samples files for release at {source_url} ({content_length / 10**6}MB)to {local_path}')

            for data in response.iter_content(chunk_size=4096):
                cur_length += len(data)
                fobj.write(data)
                done = int(100 * cur_length / content_length)
                sys.stdout.write("\r[%s%s]" % ('#' * done, ' ' * (100 - done)))
                sys.stdout.flush()