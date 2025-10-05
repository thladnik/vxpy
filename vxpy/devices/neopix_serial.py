"""Device to control LED strips or matrices that use the NeoPixel (WS2812) protocol.
"""
import time
import serial
from vxpy.core.devices import serial as vxserial

import vxpy.core.logger as vxlogger
log = vxlogger.getLogger(__name__)


class NeopixSerial(vxserial.SerialDevice):

    def __init__(self, *args, **kwargs):

        vxserial.SerialDevice.__init__(self, *args, **kwargs)

    def __del__(self):
        self.ser.close()

    def open(self):

        """
        open serial connection and turn off all LEDs
        :return: none
        """

        self.time_out = 1
        self.ser = serial.Serial()
        self.set_connection_parameters(port=self.properties['port'], baudrate=9600)

        try:
            self.ser.open()
            log.info("NeoPix connected")
        except serial.serialutil.SerialException as e:
            log.error(e)
            return False

        self.clear_pixels()

        return True

    def set_connection_parameters(self, port, baudrate=9600):

        """
        set connection parameters for serial communication
        :param port: serial port to set
        :param baudrate: must be 9600
        :return: none
        """

        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = self.time_out

        return

    def close_connection(self):

        """
        close serial connetion
        :return:  none
        """

        try:
            self.ser.close()
            log.info("Neopix disconnected")
        except serial.serialutil.SerialException as e:
            log.error(e)

        return

    def clear_pixels(self):

        """
        turns all LEDs off via the command: f"{999},{0},{0},{0}\n"
        :return: none
        """

        self._write(f"{999},{0},{0},{0}\n".encode())

        return

    def set_led(self, led_num, rgb: list):

        """
        turns individual LED on/of and sets its color and brightness
        :param led_num: LED to turn on/off
        :param rgb: list of length 3 which contains values for RGB. If all values are 0 then LED is turned off.
        Values can range from 0 to 255 ratio within RGB values define the color. Total Value of RGB defines brightness
        (e.g.: [250, 250, 250] is white with 100% brightness, [50, 50, 50] is white with 20% brightness)
        :return: none
        """

        self._write(f"{led_num},{rgb[0]},{rgb[1]},{rgb[2]}\n".encode())

        return

    def _write(self, msg):

        """
        writes serial command to Arduino
        :param msg: message to write. Needs to be in the following format: f"{<led number>},{<red channel>},{<green channel>},{<blue channel>}\n"
        all numbers (led_num, red/green/blue channel needs to be of type integer)
        :return: length of written msg
        """

        # format of all messages must be
        # f"{<led number>},{<red channel>},{<green channel>},{<blue channel>}\n"
        # led number: 0 - 49
        # red/green/blue channel: 0 - 255

        msg_len = self.ser.write(msg)
        time.sleep(0.01)

        return msg_len
