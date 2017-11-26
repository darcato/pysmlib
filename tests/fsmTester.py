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
        self.counter = self.input("testcounter")
        statesWithIOs = {
            "uno" : [self.counter],
            "due" : [self.counter],
            "tre" : [self.counter],
            "quattro" : [self.counter],
            "cinque" : [self.counter],
            "sei" : [self.counter],
            "sette" : [self.counter]
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('uno')
        print self._mirrors

    def uno_eval(self):
        if self.counter.val() == 0:
            self.gotoState("due")    

    def due_eval(self):
        if self.counter.val() == 1:
            self.gotoState("tre")    
            
    def tre_eval(self):
        if self.counter.val() == 2:
            self.gotoState("quattro")    
        
    def quattro_eval(self):
        if self.counter.val() == 3:
            self.gotoState("cinque")    
 
    def cinque_eval(self):
        if self.counter.val() == 4:
            self.gotoState("sei")    
 
    def sei_eval(self):
        if self.counter.val() == 5:
            self.gotoState("sette")    
 
    def sette_eval(self):
        if self.counter.val() == 6:
            self.gotoState("uno")    
 
    def common_eval(self):
        if self.tmrExp("timer"):
            self.logI("Timer expired")
            self.gotoState("uno")    
 
            
            
if __name__ == '__main__':        
    fsm = fsmTest('fsmTest')
    fsm.eval_forever()
    
        
            
            
