from time import sleep

import Controller

class Main(Controller.BaseProcess):

    _functionList : list = list()

    def __init__(self, **kwargs):
        Controller.BaseProcess.__init__(**kwargs)

    def addFunction(self, fun):
        self._functionList.append(fun)

    def main(self):
        if len(self._functionList) == 0:
            sleep(0.1)
        for fun in self._functionList:
            fun()