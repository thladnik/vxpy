"""Client module for socket connections and mDNS service detection
"""

_zeroconf_version = '0.147.0'

try:
    import zeroconf

except ImportError:
    print('Failed to import zeroconf, trying to install it...')

    try:
        import os
        # os.system(f'pip install zeroconf=={_zeroconf_version}')
    except Exception as e:
        print(f'Failed to install zeroconf: {e}')
        raise e


import socket
import time

import zeroconf

_browsers: dict[str, zeroconf.ServiceBrowser] = {}
_services: dict[str, dict[str, tuple]] = {}
_open_sockets: dict[str, socket.socket] = {}


class Listener(zeroconf.ServiceListener):
    def __init__(self):
        pass

    def add_service(self, zc: zeroconf.Zeroconf, service_type: str, name: str):
        global _services

        if service_type not in _services:
            _services[service_type] = {}

        self.update_service(zc, service_type, name)

    def remove_service(self, zc: zeroconf.Zeroconf, service_type: str, name: str) -> None:
        del _services[service_type][name]

    def update_service(self, zc: zeroconf.Zeroconf, service_type: str, name: str) -> None:
        info = zc.get_service_info(service_type, name, timeout=2000)
        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            _services[service_type][name] = (ip, info.port, dict(info.properties or {}))


def register_service_type(service_type: str):
    global _browsers

    zc = zeroconf.Zeroconf()
    listener = Listener()

    browser = zeroconf.ServiceBrowser(zc, service_type, listener=listener)

    _browsers[service_type] = browser


def get_services() -> dict[str, dict[str, tuple]]:
    global _services
    return _services


def get_services_matlab(service_type: str) -> dict[str, tuple]:
    global _services

    _subservices = _services.get(service_type)

    make_matlab_friendly = {}
    for i, (k, v) in enumerate(_subservices.items()):
        make_matlab_friendly[f'service_{i}'] = (k, *v)

    return make_matlab_friendly


def connect_to_first(service_type: str, reconnect=False) -> str:
    global _open_sockets, _services

    _subservices = _services.get(service_type, {})

    if not _subservices:
        raise RuntimeError('No services found via mDNS. Are you on the same subnet?')

    name = list(iter(_subservices.keys()))[0]

    return connect_to(name, reconnect=reconnect)


def connect_to(name: str) -> socket.socket:

    instance_name, rest = name.split('@', 1)
    hostname, service_type = rest.split('.', 1)

    ip, port, txt = _services[service_type][name]

    # conn_key = f'{ip}:{port}'

    return socket.create_connection((ip, port), timeout=3)

    # if conn_key in _open_sockets and not reconnect:
    #     raise RuntimeError(f'Already connected to {conn_key}')
    #
    # print(f'Connecting to {name} at {conn_key} (TXT={txt})')
    #
    # s = socket.create_connection((ip, port), timeout=3)
    #
    # _open_sockets[conn_key] = s
    #
    # return conn_key


def get_socket(conn_key: str):
    global _open_sockets
    return _open_sockets[conn_key]


if __name__ == '__main__':

    import time
    from vxpy.core import socket_com, socket_client

    import numpy as np

    service_types = [
        '_vxpy-ssm-serv._tcp.local.',  # ScanImage Streaming Module
        '_vxpy-src-serv._tcp.local.',  # ScanImage Remote Control
        '_vxpy-sci-serv._tcp.local.'  # SysCon Control Interface
    ]

    for _stype in service_types:
        socket_client.register_service_type(_stype)

    # Simulate delay through user input (browser needs time to find services)
    time.sleep(3)

    conn_key = socket_client.connect_to('instance_1@2P-holo-behavior-PC._vxpy-src-serv._tcp.local.')
    sock = socket_client.get_socket(conn_key)

    a = np.arange(30).reshape((6, -1))

    print(conn_key)
    print(sock)
