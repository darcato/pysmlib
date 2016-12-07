#! /usr/bin/python

#fsm to save each change in configuration PVs to a static database 
#and to re-upload them at reconnection

from fsm import fsmBase

class reporter(fsmBase):
    def __init__(self, name, fsms, **args):
        fsmBase.__init__(self, name, **args)

        file = open("config/cavCfgs.txt", "r")


        #a dictionary with keys = inputs
        #items = tuple with fsmObj and fsmThread corresponding to the input
        self.watchdogs = {}
        #connect input for each fsm
        #the input is the pv where to write each second to say the fsm is alive (watchdog of 2 seconds)
        for fsmObj, fsmThread in fsms.iteritems():
        	firstletter = ""
        	if isinstance(fsmObj, caraterize):
        		firstletter = "c"
        	elif isinstance(fsmObj, pulseRf):
        		firstletter = "p"
        	elif isinstance(fsmObj, softTuner):
        		firstletter = "s"
        	elif isinstance(fsmObj, zeroFreq):
        		firstletter = "z"
        	elif isinstance(fsmObj, waves):
        		firstletter = "w"

        	inp = self.input(firstletter+"ConnWatchdog", cry=fsmObj._cryostat, cav=fsmObj._cavity)
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