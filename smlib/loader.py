#! /usr/bin/python
'''
A loader to simplify the creation of a daemon of various fsm running
on different threads and sharing resources.

@date: February 2018
@authors: Davide Marcato 
@email: davide.marcato@lnl.infn.it
'''

from . import fsmFileLogger, fsmLogger, mappedIOs, fsmIOs, fsmTimers, fsmWatchdog
from threading import Thread
import signal

# Global variables
__timerManager = fsmTimers()
__verbosity = 2
__logger = fsmLogger(__verbosity)
__ioManager = fsmIOs()
__repo = None
__repoinput = None
__ioMap = None
__fsmsList = []
__levelStrings = { "error":0, "warning":1, "info":2, "debug":3 }


def setVerbosity(level):
    if isinstance(level, int):
        n = max(0, min(level, 3)) # log level must be in range [0,3]
    elif isinstance(level, str) and level.lower().strip() in __levelStrings.keys():
        n = __levelStrings[level.lower().strip()]    
    else:
        raise KeyError("Verbosity level \"%s\" not recognized!" % str(level))

    global __verbosity, __logger
    __verbosity = n
    __logger.changeLevel(n)

def logToFile(path, prefix):
    global __logger
    __logger = fsmFileLogger(__verbosity, path, prefix)
    
def setIoMap(iomap):
    global __ioMap, __ioManager
    __ioMap = iomap
    __ioManager = mappedIOs(__ioMap)

def load(fsmClass, name, *args, **kwargs):
    global __fsmsList, __timerManager, __ioManager, __logger
    kwargs["tmgr"] = __timerManager
    kwargs["ios"] = __ioManager
    kwargs["logger"] = __logger
    #TODO:check if it is not a derivate of fsmBase
    fsm = fsmClass(name, *args, **kwargs) #instance class
    __fsmsList.append(fsm)

def killAll(signum, frame):
    global __fsmsList, __timerManager
    #print("Signal: %d -> Going to kill all fsms" % signum)
    for fsm in __fsmsList:
        if fsm.isAlive():
            fsm.kill()
    print("Killed all the fsms")
    if __timerManager.isAlive():  #if no fsm is loaded it won't be alive
        __timerManager.kill()
    print("Killed the timer manager")
    
def printUnconnectedIOs(signum, frame):
    global __ioManager
    ios = __ioManager.getAll()
    s = 0
    print("DISCONNECTED INPUTS:")
    for i in ios:
        if not i.connected():
            print i.ioname()
            s+=1
    print("Total disconnected inputs: %d out of %d!" % (s, len(ios)))
    signal.pause()

def start():
    global __fsmsList, __timerManager, __ioManager, __logger
    #start another fsm to report if all the others are alive to epics db
    repo = fsmWatchdog("REPORT", __fsmsList, tmgr=__timerManager, ios=__ioManager, logger=__logger)
    __fsmsList.append(repo)

    for thread in __fsmsList:
        thread.start()
    print("%d fsms started!" % (len(__fsmsList)-1) )  #do not count reported (not issued by user)

    #wait for events
    signal.signal(signal.SIGINT, killAll)
    signal.signal(signal.SIGUSR1, printUnconnectedIOs)
    signal.pause()