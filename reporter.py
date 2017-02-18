#! /usr/bin/python

#reporter thread to write to PV the status of each fsm

from fsm import fsmBase, cavityPVs
from caraterize import caraterize
from pulseRf import pulseRf
from softTuner import softTuner
from zeroFreq import zeroFreq
from waves import waves
from store import store
from random import uniform

class reporter(fsmBase):
    def __init__(self, name, fsms, **args):
        fsmBase.__init__(self, name, **args)

        #a dictionary with keys = inputs
        #items = tuple with fsmObj and fsmThread corresponding to the input
        self.watchdogs = {}
        #connect input for each fsm
        #the input is the pv where to write each second to say the fsm is alive (watchdog of 2 seconds)
        for fsmObj, fsmThread in fsms.iteritems():
        	inp = None
        	if isinstance(fsmObj, caraterize):
        		inp = self.input("cConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
        	elif isinstance(fsmObj, pulseRf):
        		inp = self.input("pConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
        	elif isinstance(fsmObj, softTuner):
        		inp = self.input("sConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
        	elif isinstance(fsmObj, zeroFreq):
        		inp = self.input("zConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
        	elif isinstance(fsmObj, waves):
        		inp = self.input("wConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
        	elif isinstance(fsmObj, store):
        		inp = self.input("storeConnWd")
        	if inp!=None:
        		self.watchdogs[inp] = (fsmObj, fsmThread)

		statesWithIOs = {
            "run" : []
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('run')
        
        #a list of timers with timer name and input linked
        self.timers = []

    def run_entry(self):
    	for inp, objThr in self.watchdogs.iteritems():
    		#start with a random delay not to write all pvs at the same instant
    		randDelay = uniform(0, 1)
    		tmrName = inp.ioname()
    		self.timers.append((tmrName, inp))
    		self.tmrSet(tmrName, randDelay)
    	self.logD("set %d watchdogs" % len(self.timers))
    
    def run_eval(self):
    	for tmrName, inp in self.timers:
    		if self.tmrExp(tmrName):
    			#now write it each second
    			self.tmrSet(tmrName, 1)
    			if inp.connected():
    				fsm, thread = self.watchdogs[inp]
    				inp.put(int(thread.isAlive()))