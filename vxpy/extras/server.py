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


class ScanImageFrameReceiverTcpServer(vxroutine.WorkerRoutine):
    port: int = 55004
    connection_timeout: float = 0.001  # s
    blanking_duration = 4 * 10 ** -3
    frame_name: str = 'scanimage_frame'
    frame_width: int = 512
    frame_height: int = 512
    frame_dtype: str = 'int16'
    acquisition_metadata: dict = {}
    frame_header: dict = {}
    last_time: float = time.perf_counter()
    layer_num: int = 1
    last_frame_number: int = -1

    def __init__(self, *args, **kwargs):
        vxroutine.WorkerRoutine.__init__(self, *args, **kwargs)

        self.server = None
        self.connected = False
        self.acquisition_running = False
        self.client_socket: socket.socket = None
        self.client_addr = None

        self.contiguous_frame_index = -1

    def require(self) -> bool:

        # Create frame attribute
        dtype = vxattribute.ArrayType.get_type_by_str(self.frame_dtype)
        vxattribute.ArrayAttribute(self.frame_name, (self.frame_width, self.frame_height), dtype=dtype)
        vxattribute.ArrayAttribute(f'{self.frame_name}_number', (1,), vxattribute.ArrayType.int64)
        vxattribute.ArrayAttribute(f'{self.frame_name}_index', (1,), vxattribute.ArrayType.int64)
        vxattribute.ArrayAttribute(f'{self.frame_name}_timestamp', (1,), vxattribute.ArrayType.float64)
        vxattribute.write_to_file(self, self.frame_name)
        vxattribute.write_to_file(self, f'{self.frame_name}_number',)
        vxattribute.write_to_file(self, f'{self.frame_name}_index',)
        vxattribute.write_to_file(self, f'{self.frame_name}_timestamp')

        return True

    def initialize(self):
        try:
            log.info(f'Listening for clients on port {self.port}')
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('', self.port))  # Don't restrict host
            self.server.settimeout(self.connection_timeout)
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
            self.client_socket = conn
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
                self.client_socket.close()
            except Exception:
                pass

            # Reset client connection
            self.client_socket = None
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

            # Format:
            # 'acquisition_mode': 'grab' or 'focus' (str)
            # 'rolling_avg_factor': 5 (int)
            # 'stack_num_slices': 2 (int)
            # 'stack_num_frames_per_volume': 10 (int)
            # 'stack_num_frames_per_slice': 1 (int)
            # 'channels_data_type': 'int16' (str)
            self.acquisition_metadata = json.loads(buffer.decode('ascii'))
            self.acquisition_running = True

            print(f'Get metadata: {self.acquisition_metadata}')

            log.info(f'Acquisition mode started. Metadata: {self.acquisition_metadata}')

            if self.acquisition_metadata['acquisition_mode'] == 'focus':
                self.layer_num = 1
            else:
                self.layer_num = self.acquisition_metadata['stack_num_slices']

            self.last_frame_number = -1
            self.contiguous_frame_index = -1

        elif signal == 'recv_frame_header':

            # print('> Decode frame header')

            self.frame_header = json.loads(buffer.decode('ascii'))

            # print(f'Frame header {self.frame_header}')

            # print(f'> Received frame header: {self.frame_header}')
            # print(f'>> Fetch frame data')

            # Read frame data to buffer
            next_signal, frame_buffer = self._recv()

            # print(f'Next: {next_signal}')

            # Check if correct data was received
            if not next_signal or next_signal != 'recv_frame_data':
                log.error('Incorrect signal')
                return

            # On ScanImage abort frames may be sent after acq_end
            if not self.acquisition_running:
                return

            # Skip duplicate frames (this happens when SI skips a frame during stack imaging with flyback delay)
            if self.last_frame_number == self.frame_header['frame_number']:
                return
            self.last_frame_number = self.frame_header['frame_number']

            # Increment counter
            self.contiguous_frame_index += 1

            frame_width = self.frame_header['frame_width']
            frame_height = self.frame_header['frame_height']

            # Convert frame buffer to array
            bytes_decoded = np.frombuffer(frame_buffer, ctypes.c_int16)
            frame_in = np.reshape(bytes_decoded, (frame_width, frame_height), order='C')

            # Calculate number of lines to discard during blanking
            pixel_dwell_time = self.acquisition_metadata['scan_pixel_time_mean']
            pixel_num = self.blanking_duration // pixel_dwell_time
            blank_line_num = int(pixel_num // frame_width)

            # Set blanked lines low
            frame_in[:, :blank_line_num] = -2**15

            # print(f'Frame in {frame_in.sum()}')

            # Pad frame in case incoming frames shape is smaller
            if frame_width != self.frame_width or frame_height != self.frame_height:
                frame_out = np.zeros((self.frame_width, self.frame_height))
                frame_out[:frame_width, :frame_height] = frame_in
            else:
                frame_out = frame_in

            # print(f'Write frame {frame_out.sum()}')

            print(self.frame_header['frame_number'], frame_in.sum())

            # Write frame data
            vxattribute.write_attribute(self.frame_name, frame_out)
            vxattribute.write_attribute(f'{self.frame_name}_number', self.frame_header['frame_number'])
            vxattribute.write_attribute(f'{self.frame_name}_index', self.contiguous_frame_index)
            vxattribute.write_attribute(f'{self.frame_name}_timestamp', self.frame_header['last_frame_time_stamp'])

        # Wait for metadata to start frame stream
        elif signal == 'acq_end':

            log.info(f'Acquisition mode ended')
            self.acquisition_running = False

        elif signal == 'disconnected':
            log.warning(f'Lost connection to client {self.client_addr}')
            self.connected = False

    def _send_bytes(self, _bytes):
        if self.client_socket is None:
            log.error('Failed to send data to client. No client connected')
            return

        self.client_socket.send(_bytes)

    def _recv(self):

        # Check if connection is still open
        readable, _, _ = select.select([self.client_socket], [], [], self.connection_timeout)

        # Return False if not
        if not readable:
            return False, b''

        # Read 16 bytes to buffer
        com_buffer = self._read_n_bytes(16)

        # Convert to signal code and following data length (in bytes)
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

        # Read to data buffer
        data_buffer = self._read_n_bytes(data_length)

        return signal, data_buffer

    def _read_n_bytes(self, n) -> bytes:

        # print(f'Read {n} bytes')

        buff = bytearray(n)
        pos = 0
        while pos < n:
            cr = self.client_socket.recv_into(memoryview(buff)[pos:])
            if cr == 0:
                raise EOFError
            pos += cr

        return buff

    # def layer_num(self):
    #     if len(self.acquisition_metadata) == 0 or self.acquisition_metadata['acquisition_mode'] == 'focus':
    #         return 1
    #     return self.acquisition_metadata['stack_num_slices']


if __name__ == '__main__':
    pass