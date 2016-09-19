'''
Created on 15 set 2016

@author: damiano
'''

import epics
import threading


#classe che rappresenta un ingresso per le macchine a stati

class fsmInput(object):
    def __init__(self, name):
        self._name = name
        self.conn = False #pv connessa
        self.val = None
        self.data = {}    # pv data
        self._attached = set() # set che contiene le macchine a stati che utilizzano questo ingresso
        self._pv = epics.PV(name, callback=self.chgcb, connection_callback=self.concb, auto_monitor=True)
        self._lck = threading.Lock() 
    
    def attach(self, obj):
        self._attached.add(obj)
    
    #callback connessione    
    def concb(self, **args):
        self.lock()
        self._lock()
        self.conn = args.get('conn', False)
        self.val = args.get('value', None)
        self.trigger()
        self._unlock()        
        self.unlock()
    
    #callback aggiornamento
    def chgcb(self, **args):
        self.lock()
        self._lock()
        self.data = args
        self.val=args.get('value', None)
        self.trigger()
        self._unlock()        
        self.unlock()
    
    # "sveglia" le macchine a stati connesse a questo ingresso    
    def trigger(self):
        for o in self._attached:
            o.trigger(self._name)

    # ottiene l'accesso esclusivo alle mmacchine a stati connesse a questo 
    # ingresso
    def _lock(self):
        for o in self._attached:
            o.lock()
        
    def _unlock(self):
        for o in self._attached:
            o.unlock()

    #ottiene l'accesso esclusivo a questo ingresso
    def lock(self):
        self._lck.acquire()

    def unlock(self):
        self._lck.release()
        

#rappresenta una lista di oggetti input
class fsmInputs(object):

    def __init__(self):
        self._inputs = {}
        self._lck = threading.Lock()
    
    # connette (crea se non esistono) gli ingressi names all'oggetto obj
    def link(self, names, obj):
        ret = {}
        for name in names:
            if name not in self._inputs:
                self._inputs[name] = fsmInput(name)
            self._inputs[name].attach(obj)
            ret[name] = self._inputs[name]
        return ret

    def get(self, name):
        return self._inputs[name]            
    
    # ottiene l'accesso esclusivo a questo oggetto            
    def lock(self):
        self._lck.acquire()
    
    def unlock(self):
        self._lck.release()

    

class fsmOutputs(object):
    pass    



# classe base per la macchina a stati
class fsmBase(object):
    def __init__(self, inputs, outputs, stateDefs):
        
        # stateDefs e un dizionario in cui la chiave e il nome dello stato e
        # il valore un array di ingressi utilizzati dallo stato
        self._inputs = inputs
        self._outputs = outputs
        _states = {}   #perche' prima lo definisci e poi lo assegni?
        self._inputs.lock()
        for stateDef in stateDefs:
            _states[stateDef] = self._inputs.link(stateDefs[stateDef], self)
        self._states = _states
        self._inputs.unlock()
        self._curstate = None
        self._curexit = None
        self._nextstate = None
        self._nextentry = None
        self._nextexit = None
        self._progress = 0  #to report progress of the procedure [0-100]
        self._cond = threading.Condition()
    
    # ottiene accesso esclusivo a questo oggetto        
    def lock(self):
        self._cond.acquire()

    def unlock(self):
        self._cond.release()

    #cambia stato
    def gotoState(self, state):
        self._nextstatename = state
        #metodo eval del prossimo stato
        self._nextstate = getattr(self, '%s_eval' % state)
        #metodo entry del prossimo stato 
        self._nextentry = getattr(self, '%s_entry' % state, None)
        #metodo exit del prossimo stato
        self._nextexit = getattr(self, '%s_exit' % state, None)

    #valuta la macchina a stati nello stato corrente
    def eval(self):
        again = True
        while again: 
            if self._nextstate != self._curstate:
                if self._nextentry:
                    self._nextentry()
                self._curstate = self._nextstate
                self._curexit = self._nextexit
                self._cursens = self._states[self._nextstatename]
            
            self.commonEval()                
            self._curstate()        
            if self._nextstate != self._curstate:
                again = True
                if self._curexit:
                    self._curexit()
            else:
                again = False        
    
    # valuta all'infinito la macchina a stati
    def eval_forever(self):
        self.lock()
        while(1):
            print "-------------------"
            self.eval() # eval viene eseguito con l'accesso esclusivo su questa macchina
            self._cond.wait() # la macchina va in sleep in attesa di un evento (da un ingresso)

            
    def input(self, name):
        return self._inputs.get(name)       

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, name):
        if name in self._cursens:
            self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente


    def commonEval(self):
        pass


################################################################################

# ESEMPIO DI UTILIZZO
            
class zerFreqFsm(fsmBase):
    def __init__(self, inputs, outputs, statesWithPvs):
        fsmBase.__init__(self, inputs, outputs, statesWithPvs)
        self.freqErr = self.input("freqErr")
        self.enable = self.input("zeroEn")
        self.movn = self.input("m1:motor.MOVN")
        self.position = self.input("m1:motor")
        self.moveRel = self.input("m1:moveRel")
        self.gotoState('init')


    def commonEval(self):
        pass

    #eval dello stato 'init'        
    def init_eval(self):
        print "init eval"
        self.gotoState('idle')
    
    # facoltativa: questa veiene eseguita una sola volta quando la macchina entra nello stato 1
    def idle_entry(self):
        print "boot-up complete, entering idle..."
        
    # obbligatoria: viene eseguita un numero imprecisato di volte finche' rimane nello stato 1       
    def idle_eval(self):
        print "evaluating 'idle'"
        if enable.val == 1:
            if freqErr.val > 10:
            	self.gotoState("outRng_goLow")
            else self.gotoState("inRng_goLows")
    
    def idle_exit(self):
        print "Starting zeroing!"
    
    def outRng_goLow_entry(self):
    	freqerr0 = self.input('freqErr').val
		if self.input("m1:motor.MOVN").val == 0
			if freqerr0 < 10k:
				self.gotoState("outRng_goLow")			
			move of n step down
		lastmovn = movn


    def outRng_goLow_eval(self):
        print "evaluating outRng_goLow"
        self.gotoState("outRng_gohigh")
    
    def outRng_gohigh_eval(self):
        print "evaluating outRng_gohigh"
        self.gotoState("inRng_golow") 

    def inRng_golow_eval(self):
        print "evaluating inRng_golow"
        self.gotoState("inRng_goHigh")
    
    def inRng_goHigh_eval(self):
        print "evaluating inRng_goHigh"
        self.gotoState("minimize")
    
    def minimize_eval(self):
        print "evaluating minimize"
        self.gotoState("end")
    
    def end_eval(self):
        print "evaluating end"
        self.gotoState("error")
    
    def error_eval(self):
        print "evaluating error"
        self.gotoState("idle")            
        
        
inputs = fsmInputs()
outputs = fsmOutputs()

statesWithPvs = {
    "init" : [],
    "idle" : ["zeroEn"],
    "outRng_goLow" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "outRng_gohigh" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "inRng_golow" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "inRng_goHigh" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "minimize" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "end" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
    "error" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"]
}



f = zerFreqFsm(inputs, outputs, statesWithPvs)

f.eval_forever()        
