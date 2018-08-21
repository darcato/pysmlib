#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
An example of a finite state machine developed with pysmlib

@date: March 2018
@authors: Davide Marcato, Damiamo Bortolato
@email: davide.marcato@lnl.infn.it - damiano.bortolato@lnl.infn.it
'''

from smlib import fsmBase

class myfsm(fsmBase):
    def __init__(self, name, *args, **kwargs):
        super(myfsm, self).__init__(name, **kwargs)
        
        self.counter = self.connect("testcounter")
        self.wdog = self.connect("testwdog")
        self.setWatchdogInput(self.wdog, mode="on-off", interval=3)
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
    fsm = myfsm('fsmTest')
    fsm.eval_forever()
