import time
import serial
import serial.tools.list_ports
import numpy as np
import struct

from vxpy.core.devices import serial as vxserial
import vxpy.core.logger as vxlogger
log = vxlogger.getLogger(__name__)


class SutterMP285(vxserial.SerialDevice):

    def __init__(self, *args, **kwargs):
        vxserial.SerialDevice.__init__(self, *args, **kwargs)

    def open(self)-> bool:

        self.time_out = 30  # timeout in sec
        self.ser = serial.Serial()
        self.set_connection_parameters(port=self.properties['port'], baudrate=9600)
        self._open_connection()

        return True

    def close(self)-> bool:
        self._close_connection()

        return True

    def set_connection_parameters(self, port, baudrate=9600):

        """
        set connection parameters for serial connection
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

    def _open_connection(self):

        """
         open serial connection, set velocity and check if sutterMP285 is responding
         :return: none
        """

        try:
            self.ser.open()
            log.info('sutterMP285 connected')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

        self.set_velocity(200, 10)
        self.update_panel()
        (stepM, currentV, vel_scale_factor) = self.get_status()
        if currentV == 200:
            log.info('sutterMP285 ready')
        else:
            log.warning('sutterMP285 did not respond at startup.')

    def _close_connection(self):

        """
        close serial connection
        :return: none
        """

        try:
            self.ser.close()
            log.info('sutterMP285 disconnected')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

    def set_relative_mode(self):

        """
        set sutterMP285 to relative mode
        :return: none
        =================================================================
        relative mode: each axis value following the move to position command represents the number of microsteps away
        (distance) from the current position
        =================================================================
        COMMAND: 'b'CR (0x62 + 0x0D)
        RETURN: CR (0x0D)
        """

        try:
            self.ser.write(b'b\r')
            log.info('sutterMP285 set to relative mode')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return
        self.ser.read(1)

    def set_absolute_mode(self):

        """
        set sutterMP285 to absolute mode
        :return: none
        =================================================================
        relative mode: each axis value following the move to position command represents an absolute position within the
        full range of travel for that axis
        =================================================================
        COMMAND: 'a'CR (0x61 + 0x0D)
        RETURN: CR (0x0D)
        """

        try:
            self.ser.write(b'a\r')
            log.info('sutterMP285 set to absolute mode')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return
        self.ser.read(1)

    def get_position(self):

        """
        get the current position of sutterMP285
        :return: numpy array with length 3 (X, Y, Z)
        =================================================================
        returns values for X, Y and Z in microsteps as three signed long (32 bit) integers + 0x0D
        =================================================================
        COMMAND: 'c'CR (0x63h + 0x0D)
        RETURN: xxxxyyyyzzzzCR (0x0D)
        """

        try:
            self.ser.write(b'c\r')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

        xyzb = self.ser.read(13)
        xyz_um = np.array(struct.unpack('iii', xyzb[:12])) / self.step_mult

        log.info('sutterMP285 stage position: X=%g um, Y=%g um, Z= %g um' % (xyz_um[0], xyz_um[1], xyz_um[2]))

        return xyz_um

    def move_to_position(self, pos):

        """
        move the sutterMP285 to the given position
        :param pos: array or list with length 3 (X: pos[0], Y: pos[1], Z: pos[2])
        :return: none
        =================================================================
        move to a specified position. Position consists of X, Y and Z (in that order), and each consists of a signed long
        (32 bit) integer value in microsteps
        =================================================================
        COMMAND: 'm'xxxxyyyyzzzzCR (0x6D + 4 bytes for X + 4 bytes for Y + 4 bytes for Z + 0x0D)
        RETURN: CR (0x0D)
        """

        if len(pos) != 3:
            log.warning('length of move_to_position argument has to be three')
            return

        xyzb = struct.pack('iii', int(pos[0] * self.step_mult), int(pos[1] * self.step_mult), int(pos[2] * self.step_mult))
        startt = time.time()

        try:
            self.ser.write(b'm' + xyzb + b'\r')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

        cr = []
        cr = self.ser.read(1)
        endt = time.time()
        if len(cr) == 0:
            log.warning('sutterMP285  did not finish moving before timeout (%d sec).' % self.time_out)
        else:
            log.info('sutterMP285 move completed in (%.2f sec)' % (endt - startt))

    def set_velocity(self, vel: int, v_scal_factor=10):

        """
        sets sutterMP285 travel speed (velocity)
        :param vel: velocity (um/s)
        :param v_scal_factor: scale factor for velocity. Can either be 10 or 50 microsteps per step
        :return: none
        =================================================================
        056h + one unsigned short (16 bit) integer + 0x0D. The lower 15 bits (bit 14 through 0) contain the velocity value.
        The high-order bit (bit 15) indicates the microstep-to-step resolution (0 = 10, 1 = 50 microsteps per step)
        =================================================================
        COMMAND: 'V'xxCR (0x56 + 2 bytes + 0x0D)
        RETURN: CR (0x0D)
        """

        velb = struct.pack('H', int(vel))
        # change last bit of 2nd byte to 1 for ustep resolution = 50
        if v_scal_factor == 50:
            velb2 = np.double(struct.unpack('B', velb[1])) + 128
            velb = velb[0] + struct.pack('B', velb2)

        try:
            self.ser.write(b'V' + velb + b'\r')
            log.info('sutterMP285 velocity set to %d' % vel)
        except serial.serialutil.SerialException as e:
            log.error(e)
            return
        self.ser.read(1)

    def update_panel(self):

        """
        updates the panel of the sutterMP285
        :return: none
        =================================================================
        Note: refreshes the XYZ display only
        =================================================================
        COMMAND: 'n'CR (0x6E + 0x0D)
        RETURN: CR (0x0D)
        """

        try:
            self.ser.write(b'n\r')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return
        self.ser.read(1)

    def set_origin(self):

        """
        set the sutterMP285 origin to the current position
        :return: none
        =================================================================
        sets the absolute origin to the current position.
        Note: it is important to know that the set_origin command resets the absolute origin of the controller. It is possible
        to minimize the relative effect of this command by moving the manipulator to a very short distance from the ABSOLUTE ORIGIN
        (e.g. X, Y & Z all to 0.04 um) before issuing the 'o' command from the remote computer. After which, upon issuing
        the 'o' command, the controller's display sshould indicate X, Y & Z all as 0.00 um. There may also be a change
        in the overall appearance of the display. The original display configuration can be restored by entering the
        update_panel ('n') command to clean up the display or by pressing RESET on the front of the controller.
        =================================================================
        COMMAND: 'o'CR (0x6F + 0x0D)
        RETURN: CR (0x0D)
        """

        try:
            self.ser.write(b'o\r')
            log.info('sutterMP285 set origing to current position')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return
        self.ser.read(1)

    def reset_controller(self):

        """
        resets the sutterMP285 controller
        :return: none
        =================================================================

        =================================================================
        COMMAND: 'r'CR (0x72 + 0x0D)
        RETURN: nothing
        """

        try:
            self.ser.write(b'r\r')
            log.info('reset sutterMP285')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

    def get_status(self):

        """
        gets  the sutterMP285 status
        :return: list of length 3 (step_mult, current_velocity, v_scale_factor)
        =================================================================
        currently, only the following values are read out:
         - step_mult (multiplier yields usteps/nm)
         - current_velocity (velocity um/sec, bits 14 - 0)
         - v_scale_factor (10 or 50). Can also be interpreted as the controllers resolution
        =================================================================
        COMMAND: 's'CR (0x72 + 0x0D)
        RETURN: (32 bytes)CR
        """

        try:
            self.ser.write(b's\r')
        except serial.serialutil.SerialException as e:
            log.error(e)
            return

        rrr = self.ser.read(32)
        self.ser.read(1)

        statusbytes = struct.unpack(32 * 'B', rrr)

        self.step_mult = np.double(statusbytes[25]) * 256 + np.double(statusbytes[24])

        if statusbytes[29] > 127:
            self.v_scale_factor = 50
        else:
            self.v_scale_factor = 10

        self.current_velocity = np.double(127 & statusbytes[29]) * 256 + np.double(statusbytes[28])

        log.info('sutterMP285 status info: step_mul (usteps/um): %g, xspeed" [velocity] (usteps/sec): %g, velocity scale factor (usteps/step): %g' %
                 (self.step_mult, self.current_velocity, self.v_scale_factor))

        return (self.step_mult, self.current_velocity, self.v_scale_factor)
