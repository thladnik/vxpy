import logging
import multiprocessing as mp

import MappApp_Definition as madef
from helper import MappApp_Helper as mahelp
from MappApp_ImageProcessing import CameraBO

class Controller:

    _name = madef.Process.Controller.name

    process = dict()
    process_cls = dict()
    pipe = dict()
    outPipe = dict()
    _running = None
    _shutdown = None

    _propertyConnections = dict()
    _cameraBO = None

    def __init__(self, _configfile, _useGUI):
        self._configfile = _configfile
        self._ctrlQueue = mp.Queue()
        self._logQueue = mp.Queue()
        self._useGUI = _useGUI

        ## Set configurations
        self.configuration = mahelp.Config(self._configfile)
        self._cameraConfiguration = self.configuration.cameraConfiguration()
        self._displayConfiguration = self.configuration.displayConfiguration()

        ## Set up components
        self._setupCamera()

        # (optional)
        # Initialize GUI
        if self._useGUI:
            from MappApp_GUI import runGUI
            self._initializeProcess(madef.Process.GUI, runGUI, _cameraBO=self._cameraBO)

        # Initialize processes
        from process.Display import Display
        self._initializeProcess(madef.Process.Display, Display, _displayConfiguration=self._displayConfiguration)
        # self._initializeProcess(madef.Process.FrameGrabber, FrameGrabber, _cameraBO=self._cameraBO)
        from process.Logger import Logger
        self._initializeProcess(madef.Process.Logger, Logger)

        # Set up logging
        h = logging.handlers.QueueHandler(self._logQueue)  # Just the one handler needed
        root = logging.getLogger(self._name)
        root.addHandler(h)
        # send all messages, for demo; no other level or filter logic applied.
        root.setLevel(logging.DEBUG)
        self.logger = logging.getLogger(self._name)


        # Run the event loop
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
        self.process[name] = mp.Process(target=target,
                                        name=name,
                                        kwargs=dict(_ctrlQueue=self._ctrlQueue,
                                                    _logQueue=self._logQueue,
                                                    _inPipe=self.outPipe[name],
                                                    **optKwargs))
        self.process[name].start()

    def _setupCamera(self):

        # Create camera buffer object
        self._cameraBO = CameraBO(cameraConfig=self._cameraConfiguration)
        self._cameraBO.addBuffer('frame')
        self._cameraBO.addBuffer('edge_detector')

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def _start_shutdown(self):
        self.logger.log(logging.DEBUG, 'Controller shutting down processes')
        self._shutdown = True
        for name in self.process:
            self.pipe[name].send([madef.Process.Signal.rpc, madef.Process.Signal.shutdown])

    def _registerPropertyWithProcess(self, propName, process, callback=None):
        self.logger.log(logging.DEBUG, 'Process <%s> registered property <%s> with <%s>' % (process, propName, self._name))
        if not(propName in self._propertyConnections):
            self._propertyConnections[propName] = list()
        self._propertyConnections[propName].append([process, callback])

    def _setProperty(self, propName, data):
        if hasattr(self, propName):

            # Set property
            setattr(self, propName, data)
            self.logger.log(logging.DEBUG, 'Process <%s> set property <%s>: %s' % (self._name, propName, str(data)))

            # Inform all registered processes of change to property
            if propName in self._propertyConnections:
                for processName, callback in self._propertyConnections[propName]:
                    self._setPropertyOnProcess(processName, propName, callback)

            return
        self.logger.log(logging.DEBUG, 'Process <%s> FAIL to set property <%s>: %s' % (self._name, propName, str(data)))

    def _setPropertyOnProcess(self, processName, propName, callback=None):

        if hasattr(self, propName):

            # If data included a callback signature, make RPC call to sender
            if callback is not None:
                self.logger.log(logging.DEBUG, 'Process <%s> send property <%s> to process <%s> >> used callback signature <%s>'
                      % (self._name, propName, processName, callback))
                self.pipe[processName].send([madef.Process.Signal.rpc, callback, [], getattr(self, propName)])

            # Else just let sender set the property passively
            else:
                self.logger.log(logging.DEBUG, '<%s> send property <%s> to process <%s>'
                      % (self._name, processName, propName))
                self.pipe[processName].send([madef.Process.Signal.setProperty, propName, getattr(self, propName)])
        else:
            self.logger.log(logging.WARNING, 'property <%s> not set on process <%s>' % (propName, self._name))

    def run(self):
        self._running = True
        self._shutdown = False

        self.logger.log(logging.DEBUG, 'Run controller')
        while self._isRunning():

            # Evaluate queued messages
            if not(self._ctrlQueue.empty()):
                obj = self._ctrlQueue.get()

                sender, receiver, data = obj

                self.logger.log(logging.DEBUG, 'Message from <%s> to <%s>: %s' % (sender, receiver, str(data)))

                ## CALLS TO CONTROLLER
                # TODO: logging
                if receiver == madef.Process.Controller.name:

                    # RPC
                    if data[0] == madef.Process.Signal.rpc:
                        mahelp.rpc(self, data[1:])

                    # PROPERTY UPDATES
                    elif data[0] == madef.Process.Signal.setProperty:
                        self._setProperty(*data[1:])

                    # QUERIES
                    elif data[0] == madef.Process.Signal.query:
                        self._setPropertyOnProcess(sender, *data[1:])

                # CALLS TO OTHER PROCESSES (FORWARDING)
                else:
                    self.logger.log(logging.DEBUG, 'Controller forwarded data from <%s> to <%s>: %s' % (sender, receiver, str(data)))
                    if receiver in self.pipe:
                        self.pipe[receiver].send(data)

        # Update configurations that should persist here
        self.configuration.updateDisplayConfiguration(**self._displayConfiguration)
        # Save
        self.configuration.saveToFile()

        # Shutdown procedure
        self.logger.log(logging.DEBUG, 'Waiting for processes to terminate...')
        wait = True
        while wait:
            if not(self._ctrlQueue.empty()):
                obj = self._ctrlQueue.get()
                name = obj[0]
                if obj[2] == madef.Process.State.stopped:
                    self.logger.log(logging.DEBUG, 'Process <%s> confirmed termination' % name)
                    del self.process[name]
                    del self.pipe[name]
                if not(bool(self.process)) and not(bool(self.pipe)):
                    wait = False
        self.logger.log(logging.DEBUG, 'Process <%s> confirmed complete shutdown' % self._name)
        self._running = False

def runController(_configfile, _useGUI):
    Controller(_configfile=_configfile, _useGUI=_useGUI)


if __name__ == '__main__':

    _useGUI = True
    _configfile = 'default.ini'
    runController(_configfile, _useGUI)
