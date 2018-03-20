#! /usr/bin/python
'''
Created on Feb 2018
@author: davide.marcato@lnl.infn.it
'''

from . import fsmLoggerToFile, fsmLogger, lnlPVs, fsmIOs, fsmTimers, fsmThread
from .reporter import reporter

from threading import Thread
import signal


__timerManager = fsmTimers()
__verbosity = 2
__logger = fsmLogger(__verbosity)
__ioManager = fsmIOs()
__repo = None
__repoinput = None
__ioMap = None
__fsmsList = {}


def setVerbosity(n):
    __verbosity = n
    __logger.changeLevel(n)

def logToFile(path, prefix):
    __logger = fsmLoggerToFile(__verbosity, path, prefix)
    
def setIoMap(iomap):
    __ioMap = iomap
    __ioManager = lnlPVs(__ioMap)

def load(fsmClass, name, *args, **kwargs):
    kwargs["tmgr"] = __timerManager
    kwargs["ios"] = __ioManager
    kwargs["logger"] = __logger
    fsm = fsmClass(name, *args, **kwargs)
    newThread = fsmThread(fsm)
    __fsmsList[fsm] = newThread

def killAll(signum, frame):
    print("Signal: %d -> Going to kill all fsms" % signum)
    for thread in __fsmsList.itervalues():
        if thread.isAlive():
            thread.kill()
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
    repo = reporter("REPORT", __fsmsList, tmgr=__timerManager, ios=__ioManager, logger=__logger)
    repoThread = fsmThread(repo)
    __fsmsList[repo] = repoThread

    for thread in __fsmsList.itervalues():
        thread.start()
    print("%d fsms started!" % (len(__fsmsList)-1) )  #do not count reported (not issued by user)

    #wait for events
    signal.signal(signal.SIGINT, killAll)
    signal.signal(signal.SIGUSR1, printUnconnectedIOs)
    signal.pause()