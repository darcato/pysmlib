#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
Implementing watchdogs for others fsm.

@date: Oct 2016
@author: Davide Marcato
@email: davide.marcato@lnl.infn.it
'''

from . import fsmBase
from random import uniform

class reporter(fsmBase):
    def __init__(self, name, fsms, **args):
        super(reporter, self).__init__(name, **args)

        #a list of timers with timer name and input linked
        self.timers = {}
        #connect input for each fsm
        #the input is the pv where to write each time to say the fsm is alive
        for fsm in fsms:
            wd = fsm.getWatchdogInput()
            if wd!=None:
                inp, mode, interval = wd
                self.timers[inp.ioname()] = fsm


        statesWithIOs = {
            "run" : []
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('run')
        

    def run_entry(self):
        for tmrName, fsm in self.timers.iteritems():
            #start with a random delay not to write all pvs at the same instant
            inp, mode, interval = fsm.getWatchdogInput()
            randDelay = uniform(0, interval)
            self.tmrSet(tmrName, randDelay)
        self.logD("set %d watchdogs" % len(self.timers))
    
    def run_eval(self):
        for tmrName, fsm in self.timers.iteritems():
            if self.tmrExp(tmrName):
                inp, mode, interval = fsm.getWatchdogInput()
                self.tmrSet(tmrName, interval)
                if inp.connected():
                    if mode=="on":
                        inp.put(int(fsm.isAlive()))
                    elif mode=="off":
                        inp.put(int(not fsm.isAlive()))
                    elif mode=="on-off":
                        if fsm.isAlive():
                            inp.put(int(not inp.val()))
                    else:
                        self.logE("Unknown watchdog mode")