import ctypes
import datetime
import socket

import numpy as np

import vxpy.core.routine as vxroutine
import vxpy.core.logger as vxlogger

log = vxlogger.getLogger(__name__)


class FrameReceiverTcpServer(vxroutine.WorkerRoutine):

    host = '127.0.0.1'
    port = 55000

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.listeing = False
        self.connected = False
        self.client_conn = None
        self.client_addr = None
        self.counter = 0

    def readnbyte(self, n):
        buff = bytearray(n)
        pos = 0
        while pos < n:
            cr = self.client_conn.recv_into(memoryview(buff)[pos:])
            if cr == 0:
                raise EOFError
            pos += cr
        return buff

    def _accept_connection(self):
        try:
            conn, addr = self.server.accept()
            success = True
        except socket.timeout:
            success = False
        else:
            self.client_conn = conn
            self.client_addr = addr

        return success

    def initialize(self):
        try:
            log.info(f'Listening for clients on {self.host}:{self.port}')
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.settimeout(0.01)
            self.server.listen(1)
            self.listeing = False
        except Exception as _exc:
            log.error(f'Unable to listen for clients on {self.host}:{self.port} // Exception: {_exc}')
            self.listeing = False

    def main(self):

        if not self.connected:
            self.connected = self._accept_connection()
            if not self.connected:
                return

            log.info(f'Started new connection to {self.client_addr[0]}:{self.client_addr[1]}')
            self.counter = 0

        # receive data stream. it won't accept data packet greater than 1024 bytes
        data_len = self.client_conn.recv(8)
        data_len = int.from_bytes(data_len, byteorder='big')
        print(f'Got length: {data_len}')

        data = self.readnbyte(data_len)
        if not data:
            # if data is not received reset state
            self.connected = False
            log.warning(f'Lost connection to {self.client_addr[0]}:{self.client_addr[1]}')
            return
        print("---------------------------------------------------")
        print(self.counter)
        print("new message: " + str(datetime.datetime.now()))

        # decode bytes and convert to 2D-array
        bytes_decode = np.frombuffer(data, ctypes.c_uint16)
        array = np.reshape(bytes_decode, (-1, int(np.sqrt(len(bytes_decode)))))

        print("received " + str(len(data)) + " bytes")
        print("size of array: " + str(array.shape))
        print("max element: " + str(np.max(array)) + " | min element: " + str(np.min(array)))

        self.counter += 1
