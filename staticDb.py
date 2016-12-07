#! /usr/bin/python

#fsm to save each change in configuration PVs to a static database 
#and to re-upload them at reconnection

from fsm import fsmBase

class staticDb(fsmBase):
    def __init__(self, name, **args):
        fsmBase.__init__(self, name, **args)

        file = open("config/cavCfgPvs.txt", "r")
        pvs = file.readlines()
        file.close()

        self.configPvs = {}
        for cryostat in range(4, 29):
            for cavity in range(1, 5):
                for pvname in pvs:
                    pv = self.input(pvname, cry=cryostat, cav=cavity)
                    self.configPvs[pvname] = pv       #should be unique :)
        self.logI("Monitoring %d pvs" % len(self.configPvs))

        statesWithIOs = {
            "run" : []
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('run')

    def run_entry(self):
        pass
    
    def run_eval(self):
        pass