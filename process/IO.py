import logging
from time import sleep

import Controller
from devices import Arduino
import Logging

class Main(Controller.BaseProcess):

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(**kwargs)

        try:
            Arduino.getSerialConnection()
        except:
            Logging.logger.log(logging.INFO, 'No connected serial device found.')


    def main(self):
        sleep(0.1)