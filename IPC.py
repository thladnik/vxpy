import ctypes
from multiprocessing import managers

import Definition

Manager : managers.SyncManager

def createConfigDict():
    return Manager.dict()

def createSharedState():
    return Manager.Value(ctypes.c_int8, Definition.State.stopped)

class State:
    Camera     : int = None
    Controller : int = None
    Display    : int = None
    Gui        : int  = None
    IO         : int = None
    Logger     : int = None
    Worker     : int = None

