import importlib
import os

import Def
from Protocol import AbstractProtocol, StaticProtocol

_protocols = dict()

def open(file_name):
    if _protocols[file_name]['obj'] is None:
        _protocols[file_name]['obj'] = importlib.import_module(_protocols[file_name]['path'])
    return _protocols[file_name]['obj']

def read(file_obj):
    return [protocol for key, protocol in file_obj.__dict__.items()
            if isinstance(protocol, type)
            and issubclass(protocol, AbstractProtocol)
            and not(protocol == AbstractProtocol)
            and not(protocol == StaticProtocol)]

def all():
    return sorted(list(_protocols.keys()))

for i, path in enumerate(os.listdir(Def.Path.Protocol)):

    if path.startswith('.') or path.startswith('_'):
        continue

    importpath = '.'.join([Def.Path.Protocol, path[:-3]])

    file_name = path
    _protocols[file_name] = dict(path=importpath, obj=None)
