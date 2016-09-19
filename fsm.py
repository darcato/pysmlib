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
        self.trigger()
        self._unlock()        
        self.unlock()
    
    #callback aggiornamento
    def chgcb(self, **args):
        self.lock()
        self._lock()
        self.data = args
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
    def __init__(self, inputs, outputs, states):
        # 'states' è un dizionario in cui la chiave è il nome dello stato e 
        # il valore un array di ingressi utilizzati dallo stato
        self._inputs = inputs
        self._outputs = outputs
        _states = {}
        self._inputs.lock()
        for state in states:
            _states[state] = self._inputs.link(states[state], self)
        self._states = _states
        self._curstate = None
        self._inputs.unlock()
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
                self._curstatename = self._nextstatename
            
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
            self.eval() # eval viene eseguito con l'accesso esclusivo su questa macchina
            self._cond.wait() # la macchina va in sleep in attesa di un evento (da un ingresso)

            
    def input(self, name):
        return self._inputs.get(name)       

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, name):
        if name in self._cursens:
            self._cond.notify() #sveglia la macchina solo se quell'ingresso è nella sensitivity list dello stato corrente


    def commonEval(self):
		pass


################################################################################

# ESEMPIO DI UTILIZZO
            
class testFsm(fsmBase):
    def __init__(self, inputs, outputs):
        fsmBase.__init__(self, inputs, outputs, 
                         {
                          "init" : [],          # lo stato init non è interessanto a nessun ingresso
                          "uno"  : ['A'],       # lo stato 'uno' è interessato agli eventi dell'ingresso A
                          "due"  : ['A', 'B']   # lo stato 'due' è interessato agli eventi dell'ingresso B
                          }
                         )
        
        self.gotoState('init')
        


    #eval dello stato 'init'        
    def init_eval(self):
        print "init eval"
        self.gotoState('uno')
    
    # facoltativa: questa veiene eseguita una sola volta quando la macchina entra nello stato 1
    def uno_entry(self):
        print "entering in 'uno'"
        self.timer('t1').set(5.5)
        
    # obbligatoria: viene eseguita un numero imprecisato di volte finchè rimane nello stato 1       
    def uno_eval(self):
        print "evaluating 'uno'"
        i = self.input('A')
        i.val()
        
        self.input('A').value()
        self.input('A').severity()

        if i.data.get('value', None) == 1:
            self.gotoState('due')
         elif self.timer('t1').expired():
         	self.gotoState('error')   
    
    # facoltativa: viene eseguita una sola volta all'uscita dello stato 'uno'        
    def uno_exit(self):
        print "exiting from 'uno'"
            
    # so on...            
    def due_eval(self):
        print "evaluating 'due'"
        if self.input('A').conn and self.input('A').data['value'] == 0:
            self.gotoState('uno')
        
        
        
inputs = fsmInputs()
outputs = fsmOutputs()

f = testFsm(inputs, outputs)

f.eval_forever()        
