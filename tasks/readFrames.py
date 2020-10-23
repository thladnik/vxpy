import IPC
import time

def run():
    t = time.perf_counter()
    #_, frames = IPC.Routines.Camera.read('EyePosDetectRoutine/frame', last=50)
    print(time.perf_counter()-t)