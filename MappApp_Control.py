import configparser
from multiprocessing import Process, freeze_support

import MappApp_Communication as macom
import MappApp_Definition as madef
import MappApp_Helper as mahlp
import MappApp_Output as maout

freeze_support()

class Controller:

    def __init__(self):

        ## Load configuration
        self.config = mahlp.Config()

        ### Set up IPC
        ipc = macom.IPC()
        ## Main listener
        ipc.registerConnection(madef.Processes.CONTROL, madef.Processes.DISPLAY)
        # ipc.registerConnection('main', 'io')
        ## IO Listener
        #ipc.registerConnection(madef.Processes.IO, madef.Processes.DISPLAY)
        # Save to file
        ipc.saveToFile()

        ## Setup presenter screen
        print('Starting display...')
        self.display = Process(name=madef.Processes.DISPLAY, target=maout.runDisplay,
                               kwargs=dict(fps=30, settings=self.config.displaySettings()))
        self.display.start()

        ## Setup stimulus inspector
        #print('Starting stimulus inspector...')
        #self.stimspector = Process(name=madef.Processes.STIMINSPECT, target=maout.runStimulusInspector)
        #self.stimspector.start()

        ## Setup input/output
        #print('Starting IO...')
        #self.io = Process(name=madef.Processes.IO, target=maout.runIO)
        #self.io.start()

        # Set up listener (Listener waits for clients, so all client processes
        # need to be started at this point or they won't be able to connect)
        self.listener = ipc.getMetaListener(madef.Processes.CONTROL)
        self.listener.acceptClients()


    def updateDisplaySettings(self, **settings):
        self.config.updateDisplaySettings(**settings)
        self.listener.sendToClient(madef.Processes.DISPLAY,
                                   [macom.Display.Code.NewDisplaySettings, self.config.displaySettings()])

    def terminate(self):
        print('Terminating MappApp')
        # Signal processes to terminate
        self.listener.sendToClient(madef.Processes.DISPLAY, [macom.Display.Code.Close])
        #self.listener.sendToClient(madef.Processes.IO, [macom.IO.Code.Close])

        # Save configuration
        self.config.saveToFile()

    def start(self):
        """
        If MappApp is run without GUI, call this method.
        :return:
        """
        while True:
            pass

if __name__ == '__main__':
    controller = Controller()
    controller.start()