import serial

def getSerialConnection():
    serialConn = serial.Serial('COM4',
                               9600,
                               parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE,
                               bytesize=serial.EIGHTBITS,
                               timeout=1.0,
                               writeTimeout=None
                               )

    return serialConn
