import logging
import multiprocessing as mp

import Definition
import Helper
import Camera
import Process
import Logging

class Controller(Process.BaseProcess):

    name = Definition.Process.Controller

    process     = dict()
    process_cls = dict()
    pipe        = dict()
    outPipe     = dict()

    _propertyConnections = dict()
    _cameraBO: Camera.CameraBufferObject

    def __init__(self, _configfile, _useGUI):
        Process.BaseProcess.__init__(self, _ctrlQueue=mp.Queue(), _logQueue=mp.Queue())
        self._useGUI = _useGUI

        ## Set configurations
        self._configfile = _configfile
        self.configuration = Helper.Config(self._configfile)
        self._config_Camera = self.configuration.configuration(Definition.CameraConfig)
        self._config_Display = self.configuration.configuration(Definition.DisplayConfig)
        self._config_Gui = self.configuration.configuration(Definition.GuiConfig)

        ## Set up components
        self._setupCamera()

        # Initialize processes
        import process.Display
        self._initializeProcess(Definition.Process.Display, process.Display.Display,
                                _config_Display=self._config_Display)
        import process.Camera
        self._initializeProcess(Definition.Process.Camera, process.Camera.Camera,
                                _cameraBO=self._cameraBO)
        import process.Logger
        self._initializeProcess(Definition.Process.Logger, process.Logger.Logger)
        # (optional)
        # Initialize GUI
        if self._useGUI:
            import GUI
            self._initializeProcess(Definition.Process.GUI, GUI.runGUI,
                                    _cameraBO=self._cameraBO)

        # Run the event loop
        self.run()

    def _initializeProcess(self, processName, target, **optKwargs):
        """Spawn a new process with a dedicated pipe connection.

        :param processHandle: MappApp_Defintion.<Process> class
        :param target: Process class
        :param optKwargs: optional keyword arguments
        :return: None
        """
        self.process_cls[processName] = target
        self.pipe[processName], self.outPipe[processName] = mp.Pipe()
        self.process[processName] = mp.Process(target=target,
                                        name=processName,
                                        kwargs=dict(_ctrlQueue=self._ctrlQueue,
                                                    _logQueue=self._logQueue,
                                                    _inPipe=self.outPipe[processName],
                                                    **optKwargs))
        self.process[processName].start()

    def _setupCamera(self):

        # Create camera buffer object
        self._cameraBO = Camera.CameraBufferObject(_config_Camera=self._config_Camera)
        self._cameraBO.addBuffer('frame')
        self._cameraBO.addBuffer('edge_detector')

    def sendSignalToProcess(self, targetName, signal):
        self.pipe[targetName].send([signal])

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shutting down processes')
        self._shutdown = True
        for name in self.process:
            self.sendSignalToProcess(name, Process.BaseProcess.Signals.Shutdown)

    def registerPropertyWithProcess(self, propName, process, callback=None):
        Logging.logger.log(logging.DEBUG, 'Process <%s> registered property <%s>' % (process, propName))
        if not(propName in self._propertyConnections):
            self._propertyConnections[propName] = list()
        self._propertyConnections[propName].append([process, callback])
        self._updateProperty(process, propName, callback=callback)

    def updateProperty(self, propName, propData):
        """Property update to controller

        :param propName:
        :param propData:
        :return:
        """

        # Set property
        try:
            setattr(self, propName, propData)
            Logging.logger.log(logging.DEBUG,
                             'Set property <%s> to %s' % (propName, str(propData)))
        except:
            Logging.logger.log(logging.WARNING,
                             'Failed to set property <%s> to %s' % (propName, str(propData)))
        else:
            # Inform all registered processes of change to property
            if propName in self._propertyConnections:
                for processName, callback in self._propertyConnections[propName]:
                    self._updateProperty(processName, propName, callback)

    def _updateProperty(self, processName: str, propName: str, callback: str = None):
        """Outbound property update to sub process

        :param processName:
        :param propName:
        :param callback:
        :return:
        """

        if hasattr(self, propName):

            # If data included a callback signature, make RPC call to sender
            if callback is not None:
                Logging.logger.log(logging.DEBUG, 'Process <%s> send property <%s> to process <%s> >> used callback signature <%s>'
                                   % (self.name, propName, processName, callback))
                self.pipe[processName].send([Process.BaseProcess.Signals.RPC, callback, getattr(self, propName)])

            # Else just let sender set the property passively
            else:
                Logging.logger.log(logging.DEBUG, '<%s> send property <%s> to process <%s>'
                                   % (self.name, processName, propName))
                self.pipe[processName].send([Process.BaseProcess.Signals.UpdateProperty, propName, getattr(self, propName)])
        else:
            Logging.logger.log(logging.WARNING, 'Property <%s> not set on process <%s>' % (propName, processName))

    def run(self):
        self._running = True
        self._shutdown = False

        Logging.logger.log(logging.DEBUG, 'Run controller')
        while self._isRunning():

            # Evaluate queued messages
            if not(self._ctrlQueue.empty()):
                sender, receiver, msg = self._ctrlQueue.get()

                Logging.logger.log(logging.DEBUG, 'Message from <{}> to <{}>: {}'.format(sender, receiver, str(msg)))

                ## CALLS TO CONTROLLER
                # TODO: logging
                if receiver == self.name:

                    # Shutdown
                    if msg[0] == Process.BaseProcess.Signals.Shutdown:
                        self._startShutdown()

                    # RPC
                    if msg[0] == Process.BaseProcess.Signals.RPC:
                        args = list(msg[1])
                        kwargs = msg[2]
                        fun = args.pop(0)

                        try:
                            #getattr(self, fun)(*args, **kwargs)
                            fun(self, *args, **kwargs)
                        except:
                            Logging.logger.log(logging.WARNING, 'RPC call to method {}() failed with params'.
                                               format(fun, args, kwargs))
                        else:
                            Logging.logger.log(logging.DEBUG, 'RPC call to method {}() with params {}, {}'.
                                               format(fun, args, kwargs))

                    # Update property
                    elif msg[0] == Process.BaseProcess.Signals.UpdateProperty:
                        self.updateProperty(*msg[1:])

                    # Handle query
                    elif msg[0] == Process.BaseProcess.Signals.Query:
                        self._updateProperty(sender, *msg[1], **msg[2])

                # CALLS TO OTHER PROCESSES (FORWARDING)
                else:
                    try:
                        self.pipe[receiver].send(msg)
                    except:
                        Logging.logger.log(logging.WARNING, 'Failed to forward message from <{}> to <{}>: {}'.
                                           format(sender, receiver, str(msg)))
                    else:
                        Logging.logger.log(logging.DEBUG, 'Forwarded message from <{}> to <{}>: {}'.
                                           format(sender, receiver, str(msg)))

        # Update configurations that should persist here
        self.configuration.updateConfiguration(Definition.DisplayConfig, **self._config_Display)
        # Save
        Logging.logger.log(logging.INFO, 'Save configuration to file {}' .format(self._configfile))
        self.configuration.saveToFile()

        # Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Waiting for processes to terminate...')
        wait = True
        while wait:
            if not(self._ctrlQueue.empty()):
                sender, receiver, msg = self._ctrlQueue.get()
                if msg[0] == Process.BaseProcess.Signals.ConfirmShutdown:
                    Logging.logger.log(logging.DEBUG, 'Received shutdown confirmation from {}'.format(sender))
                    del self.process[sender]
                    del self.pipe[sender]

                # Check if all processes have confirmed shutdown
                if not(bool(self.process)) and not(bool(self.pipe)):
                    wait = False

        Logging.logger.log(logging.DEBUG, 'Process <%s> confirmed complete shutdown' % self.name)
        self._running = False

def runController(_configfile, _useGUI):
    Controller(_configfile=_configfile, _useGUI=_useGUI)


if __name__ == '__main__':

    _useGUI = True
    _configfile = 'default.ini'
    runController(_configfile, _useGUI)
