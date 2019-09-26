import configparser
from multiprocessing.connection import Client, Listener
import socket


class Main:
    class State:
        Ready = 200

    class Code:
        Close = 99

class Display:
    class State:
        pass

    class Code:
        NewSettings = 10
        SetNewStimulus = 20
        Close = 99

class Presenter:
    class State:
        pass

    class Code:
        Close = 99


class IPC:

    def __init__(self):
        self.config = configparser.ConfigParser()

    def registerConnection(self, listener, client):
        """
        Registers a new listener>client connection.
        :param listener: str listener to register to
        :param client: str client to register to listener
        :return:
        """

        if not(self.config.has_section(listener)):
            self.config.add_section(listener)

        self.config[listener][client] = str(self._getOpenPort())

    def _getOpenPort(self):
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('', 0))
        addr, port = tcp.getsockname()
        tcp.close()
        return port

    def getClientConnection(self, listener, client):
        try:
            port = int(self.config[listener][client])
        except:
            print('WARNING: listener>client connection "%s>%s" not registered.' % (listener, client))
        else:
            print('Opening connection "%s>%s"' % (listener, client))
            c = Client(('localhost', port))
            c.send(True)  # Let listener accept connection
            return c

    def saveToFile(self):
        with open('socket_connections.cfg', 'w') as fobj:
            self.config.write(fobj)
            fobj.close()

    def loadConnections(self):
        self.config.read('socket_connections.cfg')

        if len(self.config.sections()) == 0:
            print('WARNING: no ports allocated yet')

    def getMetaListener(self, listener):
        if self.config.has_section(listener):
            return MetaListener(listener, self.config[listener])
        else:
            print('WARNING: listener "%s" not registered.')

class MetaListener:

    listeners = dict()
    connections = dict()

    def __init__(self, _name, config):
        self._name = _name
        for client in config:
            self.listeners[client] = Listener(('localhost', int(config[client])))

    def acceptClients(self):
        for client in self.listeners:
            print('Listener "%s" waiting for client "%s"...' % (self._name, client))
            self.listeners[client]._listener._socket.settimeout(5)
            try:
                conn = self.listeners[client].accept()
                self.connections[client] = conn
                print('> connected')
            except:
                print('> no response from client.')

        # Report readyness
        for client in self.connections:
            self.connections[client].send(None)

    def receive(self):
        for client in self.connections:
            if self.connections[client].poll(timeout=.00001):
                return self.connections[client].recv()
        return None

