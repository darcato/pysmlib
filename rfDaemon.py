#! /usr/bin/python
'''
Created on Oct 2016
@author: davide.marcato@lnl.infn.it
'''

from threading import Thread, enumerate
import signal
from time import sleep
import argparse

from waves import waves
from caraterize import caraterize
from pulseRf import pulseRf
from zeroFreq import zeroFreq
from softTuner import softTuner
from reporter import reporter
from store import store
from fsm import fsmTimers, lnlPVs, fsmLoggerToFile

class fsmThread(Thread):
    def __init__(self, fsm):
        Thread.__init__(self)
        self.fsm = fsm
        self._killRequested = False

    def run(self):
        self._killRequested = False
        while not self._killRequested:
            try:
                self.fsm.eval_forever()
            except Exception, e:
                print(repr(e))
                print("WARNING: fsm %s crashed unexpectedly. Restarting..." % self.fsm.fsmname())

    def kill(self):
        self._killRequested = True
        self.fsm.kill()
        self.join()


def main():
    parser = argparse.ArgumentParser(description="rfDaemon - loads the required fsm to perform procedures")
    parser.add_argument("machineSetup", help="the path of the machine setup file", type=str)
    parser.add_argument("ioMap", help="the path of the io map file", type=str)
    parser.add_argument("pvsToStoreFile", help="the path of the file defining pvs to be stored", type=str)

    parser.add_argument("-v", "--verbosity", help="set the debug level", default=2, type=int)
    parser.add_argument("-ld", "--logDirectory", help="the path of the logging directory", default="logs/", type=str)
    parser.add_argument("-lp", "--logPrefix", help="the prefix for log files", default="daemon", type=str)
    parser.add_argument("-dp", "--databasePath", help="the path of the database file", default="db/", type=str)
    parser.add_argument("-dn", "--databaseName", help="the name of the database file", default="datas", type=str)
    args = parser.parse_args()
    
    file = open(args.machineSetup, "r")
    lines = file.readlines()
    file.close()

    targets = {}
    for line in lines:
        if line.startswith("#"):
            continue
        columns=line.split('=')
        cryostat = int(columns[0])
        cavitiesStr = columns[1].split(",")
        cavities = []
        for cavity in cavitiesStr:
            cavities.append(int(cavity))
        targets[cryostat]=cavities

    #create a thread for the timer manager
    timerManager = fsmTimers()
    commonIos = lnlPVs(args.ioMap)
    commonLogger = fsmLoggerToFile(args.verbosity, args.logDirectory, args.logPrefix)
    #timerManager.start()  #will be done automatically from first fsm loaded

    #a dictitonary containing fsm objects as keys and their thread (or None) as values
    fsms = {}
    for cryostat, cavities in targets.iteritems():
        for cavity in cavities:
            name = "Cr%02d.%1d-" % (cryostat, cavity)
            w = waves(name+"WAVE", cryostat, cavity, tmgr=timerManager, ios=commonIos, logger=commonLogger)
            c = caraterize(name+"CARA", cryostat, cavity, tmgr=timerManager, ios=commonIos, logger=commonLogger)
            z = zeroFreq(name+"ZRFR", cryostat, cavity, tmgr=timerManager, ios=commonIos, logger=commonLogger)
            p = pulseRf(name+"PULS", cryostat, cavity, tmgr=timerManager, ios=commonIos, logger=commonLogger)
            s = softTuner(name+"SWTU", cryostat, cavity, tmgr=timerManager, ios=commonIos, logger=commonLogger)
            fsms.update({w:None, c:None, z:None, p:None, s:None})


    for fsm in fsms.iterkeys():
        newThread = fsmThread(fsm)
        newThread.start()
        fsms[fsm]=newThread
    print("All fsms started!")

    stor = store("STORE", args.pvsToStoreFile, dbPath=args.databasePath, dbName=args.databaseName, tmgr=timerManager, ios=commonIos, logger=commonLogger)
    storThread = fsmThread(stor)
    storThread.start()
    fsms[stor]=storThread

    #start another fsm to report if all the others are alive to epics db
    repo = reporter("REPORT", fsms, tmgr=timerManager, ios=commonIos, logger=commonLogger)
    repoThread = fsmThread(repo)
    repoThread.start()

    def killAll(signum, frame):
        print("Signal: %d -> Going to kill all fsms" % signum)
        for fsm, thread in fsms.iteritems():
            if thread.isAlive():
                thread.kill()
        print("Killed all the fsms")
        if repoThread.isAlive():  
            repoThread.kill()
        print("Killed the reporter thread")
        if storThread.isAlive():  
            storThread.kill()
        print("Killed the store thread")
        if timerManager.isAlive():  #if no fsm is loaded it won't be alive
            timerManager.kill()
        print("Killed the timer manager")
        
    
    signal.signal(signal.SIGINT, killAll)
    signal.pause()


if __name__ == '__main__':        
    main()