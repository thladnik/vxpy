import logging
import multiprocessing as mp
import multiprocessing.connection
import signal
import sys
from time import perf_counter

import Definition
import Helper
import Camera
import Logging

if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class BaseProcess:

    class Signals:
        UpdateProperty  = 10
        RPC             = 20
        Query           = 30
        Shutdown        = 99
        ConfirmShutdown = 100

    name      : str

    _running   : bool
    _shutdown  : bool

    _ctrlQueue : mp.Queue
    _logQueue  : mp.Queue
    _inPipe    : mp.connection.PipeConnection

    _pipes     : dict = dict()
    _processes : dict = dict()

    def __init__(self, **kwargs):
        """
        Kwargs should contain at least
          _ctrlQueue
          _logQueue
          _inPipe
        for basic communication and logging in sub processes (Controller does not require _inPipe)

        Known further kwargs are:
          _cameraBO (multiple processes)
          _app (GUI)
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Setup logging
        Logging.setupLogger(self._logQueue, self.name)

        # Bind signals
        signal.signal(signal.SIGINT, self._handleSIGINT)

    def run(self):
        self._running = True
        self._shutdown = False

        # Run event loop
        self.t = perf_counter()
        while self._isRunning():
            self._handlePipe()
            self.main()
            self.t = perf_counter()

        # Inform controller that process has terminated
        self.send(Definition.Process.Controller, BaseProcess.Signals.ConfirmShutdown)

    def main(self):
        """
        Event loop to be re-implemented in subclass
        :return:
        """
        pass

    def _startShutdown(self):
        # Handle all pipe messages before shutdown
        while self._inPipe.poll():
            self._handlePipe()

        self._shutdown = True

    def _isRunning(self):
        return self._running and not(self._shutdown)

    def send(self, processName, signal, *args, **kwargs):
        """
        Convenience function to send messages to other Processes.
        All messages have the format [Sender, Receiver, Data]
        """
        if self.name == Definition.Process.Controller:
            self._pipes[processName][0].send([signal, args, kwargs])
        else:
            self._ctrlQueue.put([self.name, processName, [signal, args, kwargs]])

    def rpc(self, processName, function, *args, **kwargs):
        self.send(processName, BaseProcess.Signals.RPC, function, *args, **kwargs)

    def registerProperty(self, propName):
        """Register a property with the controller. This will cause any changes to the property in the controller
        to be automatically propagated to this process.

        :param propName:
        :return:
        """
        self.rpc(Controller.name, Controller.connectProperty, propName, self.name)

    def _updateProperty(self, propName, propData):

        try:
            Logging.logger.log(logging.DEBUG, 'Set property <{}> to {}'.
                               format(propName, propData))
            setattr(self, propName, propData)
            self.send(Definition.Process.Controller, BaseProcess.Signals.UpdateProperty, propName, propData)
        except:
            Logging.logger.log(logging.WARNING, 'FAILED to set property <{}> to {}'.
                               format(propName, propData))

    def _executeRPC(self, fun, *args, **kwargs):
        try:
            Logging.logger.log(logging.DEBUG, 'RPC call to function <{}> with Args {} and Kwargs {}'.
                               format(fun.__name__, args, kwargs))
            fun(self, *args, **kwargs)
        except Exception as exc:
            Logging.logger.log(logging.WARNING, 'RPC call to function <{}> failed with Args {} and Kwargs {} '
                                                '// Exception: {}'.
                                                format(fun.__name__, args, kwargs, exc))

    def _handlePipe(self, *args):  # needs *args for compatibility with Glumpy's schedule_interval

        # Poll pipe
        if not(self._inPipe.poll()):
            return

        msg = self._inPipe.recv()
        Logging.logger.log(logging.DEBUG, 'Received message: {}'.
                           format(msg))
        signal, args, kwargs = (msg[0], list(msg[1]), msg[2])

        if signal == BaseProcess.Signals.Shutdown:
            self._startShutdown()

        # RPC calls
        elif signal == BaseProcess.Signals.RPC:
            self._executeRPC(*args, **kwargs)

        # Set property
        elif signal == BaseProcess.Signals.UpdateProperty:
            propName = args[0]
            propData = args[1]

            try:
                Logging.logger.log(logging.DEBUG,
                                   'Set property <{}> to {}'
                                   .format(propName, str(propData)))
                setattr(self, propName, propData)
            except Exception as exc:
                Logging.logger.log(logging.WARNING,
                                   'Failed to set property <{}> to {} // Exception: {}'
                                   .format(propName, str(propData), exc))


    def addPropertyCallback(self, propName, propDtype, callback):
        """Add a callback function for the specified property.

        ---- IMPORTANT NOTICE:
        New properties HAVE to be set on the class and NOT on the instance first
        in order for this to work!
        ----

        :param propName:
        :param propDtype:
        :param callback:
        :return:
        """
        if not(hasattr(self.__class__, propName)):
            # Set new shared property if it doesn't exist
            setattr(self.__class__, propName, Helper.SharedProperty(propName, propDtype))
            Logging.logger.log(logging.DEBUG, 'Created <{}>'.format(getattr(self, propName)))
            # Automatically register property with controller.
            # This will cause the controller to automatically propagate any changes to the property.
            self.registerProperty(propName)

        # Add the callback function to be executed when property value is set.
        Logging.logger.log(logging.DEBUG, 'Add callback <{}> for <{}>'
                           .format(callback.__name__, getattr(self, propName)))
        getattr(self, propName).addSetterCallback(callback)

    def _handleSIGINT(self, sig, frame):
        print('> SIGINT event handled in  %s' % self.__class__)
        sys.exit(0)


if Definition.Env == Definition.EnvTypes.Dev:
    from IPython import embed

class Controller(BaseProcess):
    name = Definition.Process.Controller

    _propertyConnections = dict()
    _cameraBO: Camera.CameraBufferObject = None

    def __init__(self, _configfile, _useGUI):
        BaseProcess.__init__(self, _ctrlQueue=mp.Queue(), _logQueue=mp.Queue())
        self._useGUI = _useGUI

        ## Set configurations
        self._configfile = _configfile
        self.configuration = Helper.Config(self._configfile)
        self._config_Camera = self.configuration.configuration(Definition.CameraConfig)
        self._config_Display = self.configuration.configuration(Definition.DisplayConfig)
        self._config_Gui = self.configuration.configuration(Definition.GuiConfig)

        ## Set up components
        self._setupCamera()

        # (optional)
        # Initialize GUI
        if self._useGUI:
            import GUI
            self._initializeProcess(Definition.Process.GUI, GUI.Main,
                                    _cameraBO=self._cameraBO)
        # Initialize processes
        import process.Display
        self._initializeProcess(Definition.Process.Display, process.Display.Display,
                                _config_Display=self._config_Display)
        import process.Camera
        self._initializeProcess(Definition.Process.Camera, process.Camera.Camera,
                                _cameraBO=self._cameraBO)
        import process.Logger
        self._initializeProcess(Definition.Process.Logger, process.Logger.Logger)

        # Run the event loop
        self.run()

    def _initializeProcess(self, processName, target, **optKwargs):
        """Spawn a new process with a dedicated pipe connection.

        :param processHandle: MappApp_Defintion.<Process> class
        :param target: Process class
        :param optKwargs: optional keyword arguments
        :return: None
        """
        self._pipes[processName] = mp.Pipe()
        self._processes[processName] = mp.Process(target=target,
                                        name=processName,
                                        kwargs=dict(_ctrlQueue=self._ctrlQueue,
                                                    _logQueue=self._logQueue,
                                                    _inPipe=self._pipes[processName][1],
                                                    **optKwargs))
        self._processes[processName].start()

    def _setupCamera(self):
        if self._config_Camera[Definition.CameraConfig.bool_use]:
            # Create camera buffer object
            self._cameraBO = Camera.CameraBufferObject(_config_Camera=self._config_Camera)
            self._cameraBO.addBuffer(Camera.FrameBuffer)
            self._cameraBO.addBuffer(Camera.EdgeDetector)

    def connectProperty(self, propName, processName):
        Logging.logger.log(logging.DEBUG, 'Process <%s> registered property <%s>' % (processName, propName))
        if not(propName in self._propertyConnections):
            self._propertyConnections[propName] = list()
        self._propertyConnections[propName].append(processName)
        self._propagatePropertyUpdate(processName, propName)

    def _propagatePropertyUpdate(self, processName, propName):
        """Update property on sub process
        """

        if hasattr(self, propName):
            Logging.logger.log(logging.DEBUG, 'Send property <{}> to process <{}>'.
                               format(propName, processName))
            self.send(processName, BaseProcess.Signals.UpdateProperty, propName, getattr(self, propName))
        else:
            Logging.logger.log(logging.WARNING, 'Property <{}> not set on process <{}>'.
                               format(propName, processName))

    def run(self):

        ################
        # Startup
        self._running = True
        self._shutdown = False

        ################
        # Run main loop
        Logging.logger.log(logging.DEBUG, 'Run <{}>'
                           .format(self.name))
        while self._isRunning():

            # Get new Data from control queue
            sender, receiver, (signal, args, kwargs) = self._ctrlQueue.get()
            Logging.logger.log(logging.DEBUG, 'Message from <{}> to <{}>: Signal {}, Args {}, Kwargs {}'
                               .format(sender, receiver, signal, args, kwargs))

            ########
            ## CALLS TO CONTROLLER
            if receiver == self.name:

                ########
                # Shutdown
                if signal == BaseProcess.Signals.Shutdown:
                    self._startShutdown()

                ########
                # RPC
                if signal == BaseProcess.Signals.RPC:
                    self._executeRPC(*args, **kwargs)

                ########
                # Update property
                elif signal == BaseProcess.Signals.UpdateProperty:
                    propName = args[0]
                    propData = args[1]

                    try:
                        Logging.logger.log(logging.DEBUG,
                                           'Set property <{}> to {}'
                                           .format(propName, str(propData)))
                        setattr(self, propName, propData)
                    except Exception as exc:
                        Logging.logger.log(logging.WARNING,
                                           'Failed to set property <{}> to {} // Exception: {}'
                                           .format(propName, str(propData), exc))
                    else:
                        Logging.logger.log(logging.DEBUG, 'Inform registered processes of change in property <{}>'
                                           .format(propName))
                        # Inform all registered processes of change to property
                        if propName in self._propertyConnections:
                            for processName in self._propertyConnections[propName]:
                                self._propagatePropertyUpdate(processName, propName)

            ########
            # CALLS TO OTHER PROCESSES (FORWARDING)
            else:
                try:
                    Logging.logger.log(logging.DEBUG, 'Forward message from <{}> to <{}> with signal {}'.
                                       format(sender, receiver, signal))
                    self.send(receiver, signal, *args, **kwargs)
                except:
                    Logging.logger.log(logging.WARNING, 'Failed to forward message from <{}> to <{}> with signal {}'.
                                       format(sender, receiver, signal))

        ################
        # Update configurations that should persist here
        self.configuration.updateConfiguration(Definition.DisplayConfig, **self._config_Display)
        # Save to file
        Logging.logger.log(logging.INFO, 'Save configuration to file {}'
                           .format(self._configfile))
        self.configuration.saveToFile()

        ################
        # Shutdown procedure
        Logging.logger.log(logging.DEBUG, 'Waiting for processes to terminate')
        while True:
            if not(self._ctrlQueue.empty()):
                sender, receiver, msg = self._ctrlQueue.get()
                if msg[0] == BaseProcess.Signals.ConfirmShutdown:
                    Logging.logger.log(logging.DEBUG, 'Received shutdown confirmation from {}'.format(sender))
                    del self._processes[sender]
                    del self._pipes[sender]

                # Check if all processes have shut down
                if not(bool(self._processes)) and not(bool(self._pipes)):
                    break

        Logging.logger.log(logging.DEBUG, 'Confirmed complete shutdown')
        self._running = False

    def _startShutdown(self):
        Logging.logger.log(logging.DEBUG, 'Shutting down processes')
        self._shutdown = True
        for processName in self._processes:
            self.send(processName, BaseProcess.Signals.Shutdown)


if __name__ == '__main__':

    _useGUI = True
    _configfile = 'default.ini'
    ctrl = Controller(_configfile=_configfile, _useGUI=_useGUI)
