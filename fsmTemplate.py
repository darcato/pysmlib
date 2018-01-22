'''
Created on Jan 20, 2018

@author: damiano.bortolato@lnl.infn.it

FSM that implements common operation for other machines.

'''

from fsm import fsmBase

class fsmTemplate(fsmBase):
    def __init__(self, name, **va):
        fsmBase.__init__(self, name, **va)
        self.setCommonPVs(**va)

    def setCommonPVs(self, **va):
        self._errc = va.get('errCodeOut', None)
        self._errm = va.get('errMsgOut', None)
        self._stat = va.get('fsmStateOut', None)
        self._errst = va.get('errStateName', 'error')

    def gotoWait(self, tm, complist, nextstate=None):
            self._waittime = tm
            self._complist = complist
            self._retstate = self._curstatename if nextstate is None else nextstate
            self.gotoState('_wcomp')

    def _wcomp_eval(self):
        if all(map(lambda x: x.putComplete(), self._complist)):
            self.tmrSet('_tmrwait',self._waittime)
            self.gotoState('_wtimer')
            
    def _wtimer_eval(self):
        if self.tmrExp('_tmrwait'):
            self.gotoState(self._retstate)

    def setErrorStaus(self, errCod, errMsg):
        if self._errc:
            self._errc.put(errCod)
        if self._errm:
            self._errm.put(errMsg)
    
    def gotoState(self, state):
        if self._stat:
            self._stat.put(state)
        return fsmBase.gotoState(self, state)
                
    def gotoError(self, errCod, errMsg='default error message'):
        self.logI("Error: %s" % errMsg)
        self.setErrorStaus(errCod, errMsg)
        self.gotoState(self._errst)

