#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
Implementing watchdogs for others fsm.

@date: Oct 2016
@author: Davide Marcato
@email: davide.marcato@lnl.infn.it
'''

from random import uniform
from . import fsmBase


class fsmWatchdog(fsmBase):
    '''A FSM that implements watchdogs for others fsm.'''

    def __init__(self, name: str, fsms: list, **args) -> None:
        super(fsmWatchdog, self).__init__(name, **args)

        # a list of timers with timer name and input linked
        self.timers = {}
        # connect input for each fsm
        # the input is the pv where to write each time to say the fsm is alive
        for fsm in fsms:
            wd = fsm.getWatchdogInput()
            if wd is not None:
                inp = wd[0]
                self.timers[inp.ioname()] = fsm

        statesWithIOs = {
            "run": []
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('run')

    def run_entry(self):
        for tmrName, fsm in self.timers.items():
            # start with a random delay not to write all pvs at the same instant
            interval = fsm.getWatchdogInput()[2]
            randDelay = uniform(0, interval)
            self.tmrSet(tmrName, randDelay)
        self.logD("set %d watchdogs" % len(self.timers))

    def run_eval(self):
        for tmrName, fsm in self.timers.items():
            if self.tmrExpired(tmrName):
                inp, mode, interval = fsm.getWatchdogInput()
                self.tmrSet(tmrName, interval)
                if inp.connected():
                    if mode == "on":
                        inp.put(int(fsm.is_alive()))
                    elif mode == "off":
                        inp.put(int(not fsm.is_alive()))
                    elif mode == "on-off":
                        if fsm.is_alive():
                            inp.put(int(not inp.val()))
                    else:
                        self.logE("Unknown watchdog mode")
