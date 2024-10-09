import ctypes
import datetime
import json
import select
import socket
import time
from enum import Enum
from typing import Tuple

import numpy as np

import vxpy.core.attribute as vxattribute
import vxpy.core.logger as vxlogger
import vxpy.core.routine as vxroutine

log = vxlogger.getLogger(__name__)


class MScanFrameReceiverTcpServer(vxroutine.WorkerRoutine):

    port: int = 55002
    frame_name: str = 'tcp_server_frame'
    frame_width: int = 256
    frame_height: int = 256
    frame_dtype: str = 'uint16'

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.server = None

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
        vxattribute.write_to_file(self, self.frame_name)
        vxattribute.ArrayAttribute(f'{self.frame_name}_counter', (1,), vxattribute.ArrayType.uint64)

        return True

    def initialize(self):
        try:
            log.info(f'Listening for clients on port {self.port}')
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('', self.port))  # Don't restrict host
            self.server.settimeout(0.1)
            self.server.listen(1)
            self.listening = False
        except Exception as _exc:
            log.error(f'Unable to listen for clients on {self.port} // Exception: {_exc}')
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


class ScanImageFrameReceiverTcpServer(vxroutine.WorkerRoutine):
    port: int = 55004
    frame_name: str = 'tcp_server_frame'
    frame_width: int = 512
    frame_height: int = 512
    frame_dtype: str = 'uint16'

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.server = None

        self.connected = False
        self.acquisition_running = False
        self.client_conn = None
        self.client_addr = None
        self.next_buffer_length: int = 0
        self.acquisition_metadata = {}
        self.frame_header = {}
        self.last_time = time.perf_counter()

    def require(self) -> bool:

        # Create frame attribute
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        vxattribute.ArrayAttribute(self.frame_name, (self.frame_width, self.frame_height), dtype=dtype)
        vxattribute.ArrayAttribute(f'{self.frame_name}_index', (1,), vxattribute.ArrayType.int64)
        vxattribute.ArrayAttribute(f'{self.frame_name}_timestamp', (1,), vxattribute.ArrayType.float64)
        vxattribute.write_to_file(self, self.frame_name)
        vxattribute.write_to_file(self, f'{self.frame_name}_index',)
        vxattribute.write_to_file(self, f'{self.frame_name}_timestamp')

        return True

    def initialize(self):
        try:
            log.info(f'Listening for clients on port {self.port}')
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('', self.port))  # Don't restrict host
            self.server.settimeout(0.1)
            self.server.listen(1)
            self.connected = False
        except Exception as _exc:
            log.error(f'Unable to listen for clients on {self.port} // Exception: {_exc}')

    def main(self):

        # If not connected, listen for client
        if not self.connected:

            try:
                conn, addr = self.server.accept()

            except socket.timeout:
                return

            # Set client connection
            self.client_conn = conn
            self.client_addr = addr
            self.connected = True

            # New connection established
            frame_info = f'{self.frame_width}x{self.frame_height} [{self.frame_dtype}]'
            log.info(f'Started new connection to {self.client_addr[0]}:{self.client_addr[1]} to receive {frame_info}')

        # Process data sent by client
        try:
            self._process_data()

        # In case of an error, assume something with connection went wrong and wait for reconnect
        except Exception as _exc:

            log.warning(f'Caught exception {_exc}. Closed connection to client.')

            # Try to close connection properly, just in case
            try:
                self.client_conn.close()
            except Exception:
                pass

            # Reset client connection
            self.client_conn = None
            self.client_addr = None
            self.connected = False

            log.info(f'Listening for clients on port {self.port} again')

    def _process_data(self):

        # Check for data
        signal, buffer = self._recv()

        # If no data received
        if not signal:
            return

        # Check signals
        if signal == 'acq_start':

            self.acquisition_metadata = json.loads(buffer.decode('ascii'))
            self.acquisition_running = True

            log.info(f'Acquisition mode started. Metadata: {self.acquisition_metadata}')

        elif signal == 'recv_frame_header':

            # print('> Decode frame header')

            self.frame_header = json.loads(buffer.decode('ascii'))

            # print(f'> Received frame header: {self.frame_header}')
            # print(f'>> Fetch frame data')

            # Read frame data
            next_signal, frame_buffer = self._recv()

            # Check if correct data was received
            if not next_signal or next_signal != 'recv_frame_data':
                log.error('Incorrect signal')
                return

            # On ScanImage abort frames may be sent after acq_end
            if not self.acquisition_running:
                return

            frame_width = self.frame_header['frame_width']
            frame_height = self.frame_header['frame_height']

            bytes_decoded = np.frombuffer(frame_buffer, ctypes.c_uint16)
            frame_in = np.reshape(bytes_decoded, (frame_width, frame_height), order='C')

            # Pad frame in case incoming frames shape is smaller
            if frame_width != self.frame_width or frame_height != self.frame_height:
                frame_out = np.zeros((self.frame_width, self.frame_height))
                frame_out[:frame_width, :frame_height] = frame_in
            else:
                frame_out = frame_in

            # Write frame data
            vxattribute.write_attribute(self.frame_name, frame_out)
            vxattribute.write_attribute(f'{self.frame_name}_index', self.frame_header['frame_number'])
            vxattribute.write_attribute(f'{self.frame_name}_timestamp', self.frame_header['last_frame_time_stamp'])

        # Wait for metadata to start frame stream
        elif signal == 'acq_end':

            log.info(f'Acquisition mode ended')
            self.acquisition_running = False

        elif signal == 'disconnected':
            log.warning(f'Lost connection to client {self.client_addr}')
            self.connected = False

    def _recv(self):

        readable, _, _ = select.select([self.client_conn], [], [], 0.1)

        if not readable:
            return False, b''

        com_buffer = self._read_n_bytes(16)

        # Read com buffer
        signal_code, data_length = np.frombuffer(com_buffer, ctypes.c_int64)

        if signal_code == -1:
            signal = 'disconnected'
        elif signal_code == 10:
            signal = 'acq_start'
        elif signal_code == 20:
            signal = 'recv_frame_header'
        elif signal_code == 30:
            signal = 'recv_frame_data'
        elif signal_code == 40:
            signal = 'acq_end'
        else:
            log.error(f'Signal code {signal_code} not recognized')
            return False, b''

        # print(f'COM CODE [{signal_code}, {data_length}]')

        data_buffer = self._read_n_bytes(data_length)

        return signal, data_buffer

    def _read_n_bytes(self, n) -> bytes:

        # print(f'Read {n} bytes')

        buff = bytearray(n)
        pos = 0
        while pos < n:
            cr = self.client_conn.recv_into(memoryview(buff)[pos:])
            if cr == 0:
                raise EOFError
            pos += cr

        return buff


if __name__ == '__main__':
    pass