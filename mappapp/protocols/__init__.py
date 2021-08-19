import importlib
import os

from mappapp import Def
from mappapp.core import protocol

_protocols = dict()

def load(protocol_path):
    file_name, protocol_name = protocol_path.split('.')
    return getattr(open_(file_name), protocol_name)


def open_(file_name):
    if _protocols[file_name]['obj'] is None:
        _protocols[file_name]['obj'] = importlib.import_module(_protocols[file_name]['path'])
    return _protocols[file_name]['obj']


def read(file_obj):
    return [_protocol for key, _protocol in file_obj.__dict__.items()
            if isinstance(_protocol, type)
            and issubclass(_protocol, protocol.AbstractProtocol)
            and not(_protocol == protocol.AbstractProtocol)
            and not(_protocol == protocol.StaticProtocol)]


def all():
    return sorted(list(_protocols.keys()))


for i, path in enumerate(os.listdir(os.path.join('.', Def.package, Def.Path.Protocol))):

    if path.startswith('.') or path.startswith('_'):
        continue

    file_name = path[:-3]

    # E.g. protocols.TestProtocol
    importpath = '.'.join([Def.package, Def.Path.Protocol, file_name])

    _protocols[file_name] = dict(path=importpath, obj=None)
