import numpy as np

from vxpy import Logging

a = np.random.randint(5, size=(1000, 2000, 5))

def run(rec_folder):
    Logging.write(Logging.INFO,'Gathering recording data for {}'.format(rec_folder))
    for i in np.arange(0, 5, 0.25):
        Logging.write(Logging.INFO,'Composer: iteration {}'.format(i))
        b = a**i