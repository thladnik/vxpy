import numpy as np
from scipy import signal

from vxpy.api.attribute import ArrayAttribute, ArrayType, get_attribute
from vxpy.api.routine import WorkerRoutine
from vxpy.core import logging


class CalculatePSD(WorkerRoutine):

    nperseg = 2 ** 10

    def __init__(self, *args, **kwargs):
        WorkerRoutine.__init__(self, *args, **kwargs)

        self.exposed.append(CalculatePSD.set_input_signal)
        self.exposed.append(CalculatePSD.set_integration_window_width)

    def set_input_signal(self, attr_name, force_overwrite=False):
        if self.input_signal is not None and not force_overwrite:
            warn_context = f'Signal is already set to {self.input_signal.name}.'
        else:
            self.input_signal = get_attribute(attr_name)

            if self.input_signal is None:
                warn_context = 'Undefined attribute.'
            else:
                logging.write(logging.INFO,
                              f'Set input signal in {self.__class__.__name__} to {attr_name}.')
                return

        logging.write(logging.WARNING, f'Failed to set input signal in {self.__class__.__name__} to {attr_name}. {warn_context}')

    def set_integration_window_width(self, width):
        if width < self.nperseg:
            logging.write(logging.WARNING,
                          f'Failed to set integration window width in {self.__class__.__name__}. '
                          f'New value {width} < nperseg ({self.nperseg}). '
                          f'Keeping current ({self.integration_window_width})')
            return

        self.integration_window_width = width

    def setup(self):
        self.input_signal: ArrayAttribute = None
        self.integration_window_width = None
        psd_return_size = self.nperseg // 2 + 1
        self.frequencies = ArrayAttribute('psd_frequency', (psd_return_size, ), ArrayType.float64)
        self.power = ArrayAttribute('psd_power', (psd_return_size, ), ArrayType.float64)

    def initialize(self):
        pass

    def main(self, *args, **kwargs):
        if self.input_signal is None or self.integration_window_width is None:
            return

        i, t, y = self.input_signal.read(self.integration_window_width)
        if t[0] is None or not isinstance(y, np.ndarray):
            return

        y = y.flatten()

        f, p = signal.csd(y, y, fs=1./np.mean(np.diff(t)), nperseg=self.nperseg)

        self.frequencies.write(f)
        self.power.write(p)
