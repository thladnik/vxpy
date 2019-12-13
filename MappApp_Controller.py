from configparser import ConfigParser
import multiprocessing as mp
import os

import MappApp_Definition as madef
from MappApp_GUI import runGUI
from MappApp_Helper import rpc
from MappApp_ImageProcessing import CameraBO

class Controller:

    _name = madef.Process.Controller.name

    process = dict()
    process_cls = dict()
    pipe = dict()
    outPipe = dict()
    _running = None
    _shutdown = None

    _cameraBO = None

    def __init__(self, _configfile, _useGUI):
        self._configfile = _configfile
        self._ctrlQueue = mp.Queue()
        self._useGUI = _useGUI

        self.configuration = ConfigParser()
        self.configuration.read(os.path.join(madef.Path.config, self._configfile))

        # Set up components
        self._setupCamera()

        # (optional)
        # Initialize GUI
        if self._useGUI:
            self._initializeProcess(madef.Process.GUI, runGUI, _cameraBO=self._cameraBO)

        # Initialize processes
        from process.Display import Display
        self._initializeProcess(madef.Process.Display, Display)
        from process.FrameGrabber import FrameGrabber
        self._initializeProcess(madef.Process.FrameGrabber, FrameGrabber, _cameraBO=self._cameraBO)

        self.run()


    def _initializeProcess(self, processHandle, target, **optKwargs):
        """Spawn a new process with a dedicated pipe connection.

        :param processHandle: MappApp_Defintion.<Process> class
        :param target: MappApp_Process.<Process> class
        :param optKwargs: optional keyword arguments
        :return: None
        """
        name = processHandle.name
        self.process_cls[name] = target
        self.pipe[name], self.outPipe[name] = mp.Pipe()
        self.process[name] = mp.Process(target=target, kwargs=dict(_ctrlQueue=self._ctrlQueue, _inPipe=self.outPipe[name], **optKwargs))
        self.process[name].start()

    def _setupCamera(self):

        # Create camera buffer object
        self._cameraBO = CameraBO(cameraConfig=self.configuration['camera'])
        self._cameraBO.addBuffer('frame')
        self._cameraBO.addBuffer('edge_detector')

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def _start_shutdown(self):
        print('> Controller shutting down processes')
        self._shutdown = True
        for name in self.process:
            self.pipe[name].send([madef.Process.Signal.rpc, madef.Process.Signal.shutdown])

    def _setProperty(self, propName, data):
        print('Process <%s>: updating property <%s> to value <%s>' % (self._name, propName, str(data)))
        if hasattr(self, propName):
            print('Process <%s>: set property <%s> to value <%s>' % (self._name, propName, str(data)))
            setattr(self, propName, data)
            return
        print('Process <%s>: FAILED to set property <%s> to value <%s>' % (self._name, propName, str(data)))


    def run(self):
        self._running = True
        self._shutdown = False

        print('> Run controller')
        while self._isRunning():

            # Evaluate queued messages
            if not(self._ctrlQueue.empty()):
                obj = self._ctrlQueue.get()

                sender, receiver, data = obj

                print('%s > %s : %s' % (sender, receiver, str(data)))

                ## CALLS TO CONTROLLER
                # TODO: logging
                if receiver == madef.Process.Controller.name:

                    # RPC
                    if data[0] == madef.Process.Signal.rpc:
                        rpc(self, data[1:])

                    # PROPERTY UPDATES
                    elif data[0] == madef.Process.Signal.setProperty:
                        self._setProperty(*data[1:])

                    # QUERIES
                    elif data[0] == madef.Process.Signal.query:
                        if hasattr(self, data[1]):
                            print('Send answer to query')
                            self.pipe[sender].send([madef.Process.Signal.setProperty, data[1], getattr(self, data[1])])

                # CALLS TO OTHER PROCESSES (FORWARDING)
                else:
                    print('Controller forwarded data from "%s" to "%s": %s' % (sender, receiver, str(data)))
                    if receiver in self.pipe:
                        self.pipe[receiver].send(data)

        # Shutdown procedure
        print('> Waiting for processes to terminate...', sep='\n')
        wait = True
        while wait:
            if not(self._ctrlQueue.empty()):
                obj = self._ctrlQueue.get()
                name = obj[0]
                if obj[2] == madef.Process.State.stopped:
                    print('%s confirmed termination' % name)
                    del self.process[name]
                    del self.pipe[name]
                if not(bool(self.process)) and not(bool(self.pipe)):
                    wait = False
        print('>> Confirmed shutdown')
        self._running = False

def runController(_configfile, _useGUI):
    ctrl = Controller(_configfile=_configfile, _useGUI=_useGUI)


if __name__ == '__main__':

    _useGUI = True
    _configfile = 'default.ini'
    runController(_configfile, _useGUI)
