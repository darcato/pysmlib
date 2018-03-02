#! /usr/bin/python
'''
Created on Feb 2018
@author: davide.marcato@lnl.infn.it
'''

from fsm import *
from reporter import reporter

from threading import Thread
import signal


__timerManager = fsmTimers()
__verbosity = 2
__logger = fsmLogger(__verbosity)
__ioManager = fsmIOs()
__repo = None
__repoinput = None
__path = None
__ioMap = None
__fsmsList = {}


def setVerbosity(n):
    __verbosity = n
    __commonLogger.changeLevel(n)

def logToFile(path, prefix):
    self._logPath = path
    __logger = fsmLoggerToFile(__verbosity, path, prefix)
    
def setIoMap(iomap):
    self._ioMap = iomap
    __ioManager = lnlPVs(self._ioMap)

def load(fsmClass, name, *args, **nom_args):
    fsm = fsmClass(name, args, nom_args, tmgr=__timerManager, ios=__ioManager, logger=__logger)
    newThread = fsmThread(fsm)
    __fsmsList[fsm] = newThread

def killAll(signum, frame):
    #print("Signal: %d -> Going to kill all fsms" % signum)
    for fsm, thread in __fsmsList.iteritems():
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
    repoThread.start()

    count = 0
    for fsm, thread in __fsmsList.iteritems():
        count += 1
        thread.start()
    print("%d fsms started!" % count-1)  #do not count reported (not issued by user)

    #wait for events
    signal.signal(signal.SIGINT, self.killAll)
    signal.signal(signal.SIGUSR1, self.printUnconnectedIOs)
    signal.pause()