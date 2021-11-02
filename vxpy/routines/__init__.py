import importlib
import os

from vxpy import Def


def load(path=None):
    if path is not None:
        return get_routine(path)

    base_path = os.path.join(Def.PATH_PACKAGE, Def.Path.Routines)
    processes = os.listdir(base_path)
    for p in processes:
        if os.path.isfile(os.path.join(base_path, p)):
            continue

        # module =

def get_routine(path):
    return ''