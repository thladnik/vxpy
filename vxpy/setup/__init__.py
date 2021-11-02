import os
import shutil

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
