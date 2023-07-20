"""A client for testing functionality of components in `vxpy.extras.ca_processing
"""
import os.path
import socket
import time

import numpy as np
from tifffile import tifffile

from vxpy.definitions import *

sock: socket.SocketType = None


def reconnect():
    global sock

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ('localhost', 55000)
    print(f'Client: connect to server {server_address[0]}:{server_address[1]}')
    sock.connect(server_address)


def run_client():
    global sock

    # Create a TCP/IP socket
    filepath = os.path.join(PATH_SAMPLE, 'roi_activity_tracker_dummy_dataset.tif')
    print('Client: Load file')
    image_series = tifffile.imread(filepath)

    reconnect()

    idx = 0
    run = True
    while run:
        try:
            if idx >= len(image_series):
                idx = 0
                print('Client: Restart connection')
                sock.close()
                reconnect()

            # im = np.random.randint(2**16, size=(512, 512), dtype=np.uint16)
            im = image_series[idx]

            # Send data
            # message = 'This is the message.  It will be repeated.'
            # print('Send message...')

            data_len = (2 * 512 * 512).to_bytes(8, byteorder='big')

            # print("---------------------------------------------------")
            # print(idx)
            # print("new message: " + str(datetime.datetime.now()))
            # print('Send length')
            sock.sendall(data_len)

            # print('Send data')
            sock.send(im.astype(np.uint16).tobytes())

            time.sleep(0.05)
        except Exception as _exc:
            print('Client: connection possibly terminated by remote host')
            import traceback
            run = False

        idx += 1

    print('Client: closing socket')
    sock.close()
