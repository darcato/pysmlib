#! /usr/bin/python
'''
A loader to simplify the creation of a daemon of various fsm running
on different threads and sharing resources.

@date: February 2018
@authors: Davide Marcato 
@email: davide.marcato@lnl.infn.it
'''

from . import fsmLoggerToFile, fsmLogger, mappedIOs, fsmIOs, fsmTimers, fsmWatchdog
from threading import Thread
import signal


__timerManager = fsmTimers()
__verbosity = 2
__logger = fsmLogger(__verbosity)
__ioManager = fsmIOs()
__repo = None
__repoinput = None
__ioMap = None
__fsmsList = []


def setVerbosity(n):
    __verbosity = n
    __logger.changeLevel(n)

def logToFile(path, prefix):
    __logger = fsmLoggerToFile(__verbosity, path, prefix)
    
def setIoMap(iomap):
    __ioMap = iomap
    __ioManager = mappedIOs(__ioMap)

def load(fsmClass, name, *args, **kwargs):
    kwargs["tmgr"] = __timerManager
    kwargs["ios"] = __ioManager
    kwargs["logger"] = __logger
    #check if it is not a derivate of fsmBase
    fsm = fsmClass(name, *args, **kwargs)
    __fsmsList.append(fsm)

def killAll(signum, frame):
    print("Signal: %d -> Going to kill all fsms" % signum)
    for fsm in __fsmsList:
        if fsm.isAlive():
            fsm.kill()
    print("Killed all the fsms")
    if __timerManager.isAlive():  #if no fsm is loaded it won't be alive
        __timerManager.kill()
    print("Killed the timer manager")
    
def printUnconnectedIOs(signum, frame):
    ios = __ioManager.getAll()
    s = 0
    print("DISCONNECTED INPUTS:")
    for i in ios:
        if not i.connected():
            print i.ioname()
            s+=1
    print("Total unconnected inputs: %d out of %d" % (s, len(ios)))

def start():
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