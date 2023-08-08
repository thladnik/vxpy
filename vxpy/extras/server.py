import ctypes
import datetime
import socket

import numpy as np

import vxpy.core.attribute as vxattribute
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine

log = vxlogger.getLogger(__name__)


class FrameReceiverTcpServer(vxroutine.WorkerRoutine):

    host: str = '127.0.0.1'
    port: int = 55000
    frame_name: str = 'tcp_server_frame'
    frame_width: int = 512
    frame_height: int = 512
    frame_dtype: str = 'uint8'

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.listening = False
        self.connected = False
        self.client_conn = None
        self.client_addr = None
        self.counter = 0

    def require(self) -> bool:

        # Create frame attribute
        shape = (self.frame_width, self.frame_height)
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        vxattribute.ArrayAttribute(self.frame_name, shape, dtype=dtype)
        vxattribute.ArrayAttribute(f'{self.frame_name}_counter', (1,), vxattribute.ArrayType.uint64)

        return True

    def initialize(self):
        try:
            log.info(f'Listening for clients on {self.host}:{self.port}')
            self.server.bind((self.host, self.port))
            self.server.settimeout(0.01)
            self.server.listen(1)
            self.listening = False
        except Exception as _exc:
            log.error(f'Unable to listen for clients on {self.host}:{self.port} // Exception: {_exc}')
            self.listening = False

    def main(self):

        # If not connected, check for new connection
        if not self.connected:
            self.connected = self._accept_connection()

            # If no new connection, return
            if not self.connected:
                return

            # New connection established

            frame_info = f'{self.frame_width}x{self.frame_height} [{self.frame_dtype}]'
            log.info(f'Started new connection to {self.client_addr[0]}:{self.client_addr[1]} to receive {frame_info}')

            # Reset counter on new connection
            self.counter = 0

        # Receive data stream. It won't accept data packet greater than 1024 bytes
        data_len = self.client_conn.recv(8)
        data_len = int.from_bytes(data_len, byteorder='big')
        # print(f'Got length: {data_len}')

        data = self._readnbyte(data_len)
        if not data:
            # If data is not received, reset state
            self.connected = False
            log.warning(f'Lost connection to {self.client_addr[0]}:{self.client_addr[1]}')
            return
        # print("---------------------------------------------------")
        # print(self.counter)
        # print("new message: " + str(datetime.datetime.now()))

        # decode bytes and convert to 2D-array
        bytes_decode = np.frombuffer(data, ctypes.c_uint16)
        frame = np.reshape(bytes_decode, (-1, int(np.sqrt(len(bytes_decode)))), order='F')

        vxattribute.write_attribute(self.frame_name, frame)
        vxattribute.write_attribute(f'{self.frame_name}_counter', self.counter)

        # print("received " + str(len(data)) + " bytes")
        # print("size of array: " + str(read_frame.shape))
        # print("max element: " + str(np.max(read_frame)) + " | min element: " + str(np.min(read_frame)))

        # Increment counter
        self.counter += 1

    def _readnbyte(self, n):
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