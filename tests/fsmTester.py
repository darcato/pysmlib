# -*- coding: utf-8 -*-
'''
Created on 15 set 2016
@author: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''


from fsm import fsmBase

################################################################################

# ESEMPIO DI UTILIZZO

    
    
                
class fsmTest(fsmBase):
    def __init__(self, name, **args):
        fsmBase.__init__(self, name)
        self.loopPower = self.input("lopwEn")
        statesWithIOs = {
            "uno" : [],
            "due" : []
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('uno')
    
    def uno_entry(self):
        self.logI("uno entry")
        self.loopPower.put(0)
        self.tmrSet('t1',5)
        

    def due_entry(self):
        self.logI("due entry")
        self.tmrSet('t2',7)
            
    def uno_eval(self):
        self.logD('waiting for t1')
        if self.tmrExp('t1'):
            self.gotoState('due')
        
    def due_eval(self):
        self.logD('waiting for t2')
        if self.tmrExp('t2'):
            self.gotoState('uno')
 
            
            
if __name__ == '__main__':        
    fsm = fsmTest('fsmTest')
    fsm.eval_forever()
    
        
            
            
