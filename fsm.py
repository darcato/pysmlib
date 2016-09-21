'''
Created on 15 set 2016

@author: damiano
'''

import epics
import threading


#classe che rappresenta un ingresso per le macchine a stati

class fsmIO(object):
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
    
    #put callback
    def putcb(self, name):
        self.lock()
        self._lock()
        self.trigger()
        self._unlock()        
        self.unlock()
    	pass

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
        
    def put(self, value):
    	self._pv.put(value, callback=self.putcb, use_complete=True)
        

#rappresenta una lista di oggetti input
class fsmIOs(object):

    def __init__(self):
        self._ios = {}
        self._lck = threading.Lock()
    
    # connette (crea se non esistono) gli ingressi names all'oggetto obj
    def link(self, names, obj):
        ret = {}
        for name in names:
            if name not in self._ios:
                self._ios[name] = fsmIO(name)
            self._ios[name].attach(obj)
            ret[name] = self._ios[name]
        return ret

    def get(self, name):
        return self._ios[name]            
    
    # ottiene l'accesso esclusivo a questo oggetto            
    def lock(self):
        self._lck.acquire()
    
    def unlock(self):
        self._lck.release()

    def getFsmIO(self, fsm):
    	ret = {}
    	for io in self._ios:
    		if fsm in io._attached:
    			ret[io._name] = io
    	return ret
    




# classe base per la macchina a stati
class fsmBase(object):
    def __init__(self, ios, stateDefs):
        
        # stateDefs e un dizionario in cui la chiave e il nome dello stato e
        # il valore un array di ingressi utilizzati dallo stato
        self._ios = io
        self._states = {}
        self._ios.lock()
        for stateDef in stateDefs:
            self._states[stateDef] = self._ios.link(stateDefs[stateDef], self)
        self._ios.unlock()
        self._curstate = None
        self._curexit = None
        self._nextstate = None
        self._nextentry = None
        self._nextexit = None
        self._cursens = {}
        self._cond = threading.Condition()
    	self._myios = self._ios.getFsmIO(self)


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
                self.commonExit()
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
        return self._ios.get(name)       

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, name):
        if name in self._cursens:
            self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente

    def commonEval(self):
        pass

    def commonExit(self):
    	pass


################################################################################

# ESEMPIO DI UTILIZZO