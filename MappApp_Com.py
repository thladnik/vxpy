from multiprocessing import connection

class Main:

    socket = 6010

    class Code:
        Ready = 200
        Close = 299

    class Listener:
        def __init__(self):
            self.listener = connection.Listener(('127.0.0.1', Main.socket))
            self.conn = self.listener.accept()

    class Client:
        def __init__(self):
            self.conn = connection.Client(('127.0.0.1', Main.socket))



class Display:
    socket = 6020

    class Code:
        NewSettings = 100
        SetNewStimulus = 101
        Close = 199


    class Listener:
        def __init__(self):
            self.listener = connection.Listener(('127.0.0.1', Display.socket))
            self.conn = self.listener.accept()

    class Client:
        def __init__(self):
            self.conn = connection.Client(('127.0.0.1', Display.socket))

        def send(self, *args, **kwargs):
            self.conn.send(*args, **kwargs)


class Presenter:
    socket = 6030

    class Code:
        Close = 199

    class Listener:
        def __init__(self):
            self.listener = connection.Listener(('127.0.0.1', Presenter.socket))
            self.conn = self.listener.accept()

    class Client:
        def __init__(self):
            self.conn = connection.Client(('127.0.0.1', Presenter.socket))

        def send(self, *args, **kwargs):
            self.conn.send(*args, **kwargs)

