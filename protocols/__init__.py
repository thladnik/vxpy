import importlib
import os

import Def
from core.protocol import AbstractProtocol, StaticProtocol

_protocols = dict()

def load(protocol_path):
    file_name, protocol_name = protocol_path.split('.')
    return getattr(open_(file_name), protocol_name)


def open_(file_name):
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

    file_name = path[:-3]

    # E.g. protocols.TestProtocol
    importpath = '.'.join([Def.Path.Protocol, file_name])

    _protocols[file_name] = dict(path=importpath, obj=None)
