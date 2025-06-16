"""A dummy ScanImage client for testing functionality of components in `vxpy.extras.ca_processing
"""
import json
import os.path
import socket
import time

import numpy as np
# from tifffile import tifffile
from vxpy.utils import examples

from vxpy.definitions import *

sock: socket.SocketType = None


def reconnect():
    global sock

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        server_address = ('127.0.0.1', 55004)
        print(f'Client: try to connect to server {server_address[0]}:{server_address[1]}')
        sock.connect(server_address)
    except Exception as _exc:
        print(f'Client: Failed to connect // {_exc}')
        return False
    else:
        print(f'Client: Successfully connected to server')
        return True


def run_client():
    global sock

    # Create a TCP/IP socket
    # filepath = os.path.join(PATH_TEMP, 'roi_activity_tracker_dummy_dataset.tif')
    print('Client: Load file')
    # image_series = tifffile.imread(filepath)
    dataset = examples.load_dataset('zf_optic_tectum_driven_activity_2Hz')
    image_series = dataset['frames']

    # time.sleep(3)

    _connected = False
    while not _connected:
        time.sleep(0.5)
        _connected = reconnect()

    idx = 10**10
    run = True
    while run:
        try:

            # Start aquisition
            if idx >= len(image_series):
                idx = 0
                # print('Client: Restart connection')
                # sock.close()
                # reconnect()
                acq_metadata = {
                    'acquisition_mode': 'focus',
                    'rolling_avg_factor': 5,
                    'stack_num_slices': 2,
                    'stack_num_frames_per_volume': 10,
                    'stack_num_frames_per_slice': 1,
                    'channels_data_type': 'int16',
                    'scan_pixel_time_mean': 1
                }

                acq_metadata_bytes = json.dumps(acq_metadata).encode('ascii')

                # Send acquisition signal and metadata
                sock.send(np.array([10, len(acq_metadata_bytes)], dtype=np.int64).tobytes(order='C'))
                sock.send(acq_metadata_bytes)

            # Create frame header
            im = image_series[idx].astype(np.int16)
            frame_header = {
                'frame_number': idx,
                'last_frame_time_stamp': time.time(),
                'frame_width': im.shape[0],
                'frame_height': im.shape[1],
            }
            frame_header_bytes = json.dumps(frame_header).encode('ascii')
            # Send frame header
            sock.send(np.array([20, len(frame_header_bytes)], dtype=np.int64).tobytes(order='C'))
            sock.send(frame_header_bytes)

            # Send frame data
            im_bytes = im.tobytes()
            sock.send(np.array([30, len(im_bytes)], dtype=np.int64).tobytes(order='C'))
            sock.send(im_bytes)

            time.sleep(0.05)
        except Exception as _exc:
            print('Client: connection possibly terminated by remote host')
            import traceback
            run = False

        idx += 1

    print('Client: closing socket')
    sock.close()
