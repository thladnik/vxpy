"""Server module for socket connections and mDNS advertising
"""
import socket
import threading
import time
import contextlib

import zeroconf

import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


def pick_free_port():

    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 0))
        return s.getsockname()[1]


def get_primary_ipv4():

    # Requires internet connection to check against Google DNS
    try:
        # Get primary IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]

    # If no internet connection available
    except OSError:
        # This may still fail for multiple network adapters
        # TODO: revisit this in future

        hostname = socket.gethostname()
        addrs = socket.gethostbyname_ex(hostname)[2]
        ips = [ip for ip in addrs if not ip.startswith('127.')]
        ip = ips[0] if ips else '127.0.0.1'

    else:
        s.close()

    return ip


class MdnsAdvertiser:

    def __init__(self, service_type: str, instance_name: str, ip: bytes, port: int,
                 txt=None, hostname: str = None):
        self.zc = zeroconf.Zeroconf()
        self.hostname = hostname
        self.hostname = socket.gethostname()
        self.ip = ip
        self.port = port
        server_fqdn = f'{self.hostname}.local.'

        self.info = zeroconf.ServiceInfo(
            type_=service_type,
            name=f'{instance_name}@{self.hostname}.{service_type}',
            addresses=[ip],
            port=port,
            properties=(txt or {}),
            server=server_fqdn,
        )

    def start(self):
        self.zc.register_service(self.info)

    def stop(self):
        try:
            self.zc.unregister_service(self.info)
        finally:
            self.zc.close()


def run_mdns_advertiser(service_type: str, instance_name: str):

    ip = socket.inet_aton(get_primary_ipv4())
    port = pick_free_port()
    adv = MdnsAdvertiser(
        service_type, instance_name, ip, port,
        txt={'version': '1.0'}
    )
    adv.start()
    log.info(f'Advertised {instance_name} on mDNS as {service_type} port {port}')

    return adv, ip, port


def test_handle_conn(sock: socket.socket, addr):
    from vxpy.core import socket_com\

    with sock:
        while True:

            # Just read and print data
            value = socket_com.recv_any(sock)

            if isinstance(value, bytes) and value == b'\x00':
                print('Look at this tasty poison pill')
                break

            print(value)


def test_run_server(service_type: str, instance_name: str):

    # Start mDNS
    adv, ip, port = run_mdns_advertiser(service_type, instance_name)

    # Open TCP socket and listen
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', port))
    srv.listen()

    while True:
        try:
            print(f'> Serving {adv.info.name} on port {srv.getsockname()[1]}...')
            conn, addr = srv.accept()
            print(f'> Accept connection from {addr}')
            threading.Thread(target=test_handle_conn, args=(conn, addr), daemon=True).start()

        except:
            break

    adv.stop()
    srv.close()


if __name__ == '__main__':

    import multiprocessing

    service_types = [
        '_vxpy-ssm-serv._tcp.local.',  # ScanImage Streaming Module
        '_vxpy-src-serv._tcp.local.',  # ScanImage Remote Control
        '_vxpy-sci-serv._tcp.local.'   # SysCon Control Interface
    ]

    procs = []
    for stype in service_types:
        for i_idx in range(3):
            p = multiprocessing.Process(target=test_run_server, args=(stype, f'instance_{i_idx}'))
            p.start()
            procs.append(p)
            time.sleep(0.1)

    for p in procs:
        p.join()
