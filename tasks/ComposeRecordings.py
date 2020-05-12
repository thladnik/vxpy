import numpy as np
import time

import logging

import Logging

a = np.random.randint(5, size=(1000, 2000, 5))

def run(rec_folder):
    Logging.write(logging.INFO, 'Gathering recording data for {}'.format(rec_folder))
    for i in np.arange(0, 1, 0.1):
        Logging.write(logging.INFO, 'Composer: iteration {}'.format(i))
        b = a**i