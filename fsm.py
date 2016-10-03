# -*- coding: utf-8 -*-
'''
Created on 15 set 2016

@author: damiano
'''


import epics
import threading
import time

class fsmLogger(object):
    levstr = ['E','W','I','D']
    def __init__(self, lev=3):
        self._level = lev
        self.startime = time.time()
        
    def log(self, lev, msg):
    	tm = time.time() - self.startime
        if lev <= self._level:
            self.pushMsg('%8.2fs: %s - %s' %(tm, fsmLogger.levstr[lev], msg))
            
    def pushMsg(self, msg):
        print msg

    def resetTime(self):
    	self.startime = time.time()


#Classe timer, utilizzabile dalle macchine a stati
class fsmTimer(object):
    def __init__(self, fsm, name):
        self.expire = 0
        self._fsm = fsm
        self._pending = False
        self._name = name
            
    def reset(self, timeout):
        self.expire = time.time() + timeout
        self._pending = True
        
    def trigger(self):
        self._pending = False
        self._fsm.lock()
        self._fsm.trigger(timername=self._name)
        self._fsm.unlock()
        
    def expd(self):
        return not self._pending    

    
# Classe per il management dei timers       
class fsmTimers(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        #lock per l'accesso esclusivo
        self._cond = threading.Condition()
        #array con i timers attivi in ordine di scadenza
        # (indice 0 è il prossimo a scadere)
        self._timers = []
        
    # routine principale del thread.
    # Funziona in questo modo: il thread va in sleep per un periodo di tempo pari a quello che manca
    # allo scadere del prossimo timer (il primo di una lista ordinata per scadenza). Allo scadere dello 
    # sleep, il thread inizia a vedere quanti timer sono scaduti partendo dal prossimo (possono scaderene 
    # anche più di uno quando hanno la stessa ora di scadenza o gli intervalli rientrano nel jitter di 
    # esecuzione del thread). Per ogni timer scaduto esegue il trigger e lo rimuove dalla lista dei timer 
    # pendenti  
    def run(self):
        #acquisissce il lock, per avere accesso esclusivo alla lista dei timer
        self._cond.acquire()
        next = None
        while True:
            if len(self._timers): # se ci sono timers in pendenti
                now = time.time() # tempo corrente
                i = 0
                next = None
                for t in self._timers:
                    if t.expire > now: 
                        #abbiamo trovato il primo timer non ancora scaduto,
                        # interrompo la scansione, i rappresenta l'indice del primo timer non scaduto
                        next = self._timers[i].expire - now
                        break
                    i += 1
                # triggera gli eventi per i timer che vanno da 0 a i-1    
                for t in self._timers[:i]:
                    t.trigger()
                #rimuove i primi 'i' timers (che sono scaduti)                        
                self._timers = self._timers[i:]
            #va in sleep per i prossimi 'next' secondi, ovvero l'intervallo di tempo al termine del quale scadra'
            # il prossimo timer. Se non ci sono timer va in sleep a per un tempo indefinito
            # NB: wait rilascia il lock permettendo ad altri thread di impostare altri timer
            self._cond.wait(next)
    
    # imposta un timer     
    def set(self, timer, timeout):
        #ottiene l'accesso esclusivo alla lista dei timer
        self._cond.acquire()
        try:
            # imposta il tempo al quale scadrà il timer
            timer.reset(timeout)
            
            # se il timer è già in lista significa che è stato reimpostato prima che scadesse, 
            # quindi lo rimuovo e lo reimposto
            if timer in self._timers:
                self._timers.remove(timer)
            i = 0    
            for t in self._timers:
                if t.expire > timer.expire:
                    # il timer all'indice 'i' scade dopo il timer che sto impostando, pertanto
                    # inserisco il nuovo timer in questa posizione 'i' e interrompo il ciclo
                    break
                i += 1
            self._timers.insert(i, timer)
            if i == 0:
                # CASO SPECIALE: se 'i'  == 0 significa che ho inserito in testa il nuovo timer oppure l'ho inserito
                # in una lista vuota; nel primo caso devo svegliare il thread perche' il nuovo timer scadra' prima 
                # del suo prossimo risveglio (impostato su quello che ora è il secondo timer in lista), nel secondo
                # caso il thread sta dormendo per un tempo indefinito, quindi lo devo svegliare affinche reimposti 
                # un tempo di sleep corretto
                self._cond.notify()
            #rilascia il lock
        except Exception, e:
            print e        
        finally:
            self._cond.release()
    
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
        self.pval = None
        self._flgRising = False
        self._flgFalling = False
    
    def attach(self, obj):
        self._attached.add(obj)
    
    #callback connessione    
    def concb(self, **args):
        self.lock()
        self._lock()
        self.conn = args.get('conn', False)
        self.trigger(reason="connectionCallback")
        self._unlock()        
        self.unlock()
    
    #callback aggiornamento
    def chgcb(self, **args):
        self.lock()
        self._lock()
        self.data = args
        self.pval = self.val
        self._flgRising = True
        self._flgFalling = True
        self.val=args.get('value', None)
        self.trigger(reason="changeCallback")
        self._unlock()        
        self.unlock()
    
    #put callback
    def putcb(self, **args):
        self.lock()
        self._lock()
        self.trigger(reason="putCallback")
        self._unlock()
        self.unlock()
    	pass

    # "sveglia" le macchine a stati connesse a questo ingresso    
    def trigger(self, **args):
        for o in self._attached:
            o.trigger(inputname=self._name, reason=args['reason'])

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

    def putComplete(self):
    	return self._pv.put_complete
        
    def rising(self):
       	if self._flgRising and self.pval < self.val:
       		self._flgRising = False
        	return True
    	else: 
    		return False

    def falling(self):
        if self._flgFalling and self.pval > self.val:
        	self._flgFalling = False
        	return True
    	else:
    		return False

#rappresenta una lista di oggetti input
class fsmIOs(object):

    def __init__(self):
        self._ios = {}
    
    # connette (crea se non esistono) gli ingressi names all'oggetto obj
    def link(self, names, obj):
        if names is None:
            return None
        ret = {}
        for name in names:
            if name not in self._ios:
                self._ios[name] = fsmIO(name)
            self._ios[name].attach(obj)
            ret[name] = self._ios[name]
        return ret

    def get(self, name):
        return self._ios[name]
    
    def getFsmIO(self, fsm):
    	ret = {}
    	for io in self._ios.values():
    		if fsm in io._attached:
    			ret[io._name] = io
    	return ret
    




# classe base per la macchina a stati
class fsmBase(object):
    def __init__(self, name, stateDefs, **args):
        
        # stateDefs e un dizionario in cui la chiave e il nome dello stato e
        # il valore un array di ingressi utilizzati dallo stato

        self._name = name
        if not 'tmgr' in args:
            self._tmgr = fsmTimers()
            self._tmgr.start()
        else:
            self._tmgr = args['tmgr']
                
        self._timers = {}
        self._ios = args.get('ios', fsmIOs())
        self._logger = args.get('logger', fsmLogger())
        self._states = {}
        for stateDef in stateDefs:
            self._states[stateDef] = self._ios.link(stateDefs[stateDef], self)
        self._curstatename = 'undefined'
        self._nextstatename = 'undefined'
        self._prevstatename = 'undefined'
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
        if (self._nextstate != self._curstate):
            self.logI('gotoState() called twice, ignoring subsequent calls')
            return
        if self._curstatename == state:
            return
        self._nextstatename = state
        #metodo eval del prossimo stato
        self._nextstate = getattr(self, '%s_eval' % state)
        #metodo entry del prossimo stato 
        self._nextentry = getattr(self, '%s_entry' % state, None)
        #metodo exit del prossimo stato
        self._nextexit = getattr(self, '%s_exit' % state, None)

    def gotoPrevState(self):
        if self._prevstatename:
            self.gotoState(self._prevstatename)

    def log(self, lev, msg):
        whites = len(max(self._states, key=len)) - len(self._curstatename)
        self._logger.log(lev, '%s[%s] :%s %s' %(self._name, self._curstatename, " "*whites, msg))    

    def logE(self, msg):
        self.log(0, msg)

    def logW(self, msg):
        self.log(1, msg)

    def logI(self, msg):
        self.log(2, msg)

    def logD(self, msg):
        self.log(3, msg)

    def logTimeReset(self):
    	self._logger.resetTime()

    #valuta la macchina a stati nello stato corrente
    def eval(self):
        again = True
        while again: 
            if self._nextstate != self._curstate:
                self.logD('%s => %s' % (self._curstatename, self._nextstatename))
                self._prevstatename = self._curstatename
                self._curstatename = self._nextstatename    
                self._curstate = self._nextstate
                self._curexit = self._nextexit
                self._cursens = self._states.get(self._nextstatename, {})
                self.commonEntry()
                if self._nextentry:
                    self.logD('executing %s_entry()' %(self._curstatename))
                    self._nextentry()
            
            self.commonEval()                
            self.logD('executing %s_eval()' %(self._nextstatename))
            self._curstate()        
            if self._nextstate != self._curstate:
                # procede a valutare lo stato successivo, ma rilascia il lock per 100ms 
                # in modo da permettere la ricezione di eventi che possono modificare lo stato
                # degli ingressi
                again = True
                self._cond.wait(0.1) 
                if self._curexit:
                    self.logD('executing %s_exit()' %(self._curstatename))
                    self._curexit()
                self.commonExit()
            else:
                again = False        
    
    # valuta all'infinito la macchina a stati
    def eval_forever(self):
        self.lock()
        while(1):
            print ""
            self.logD('awoken')
            self.eval() # eval viene eseguito con l'accesso esclusivo su questa macchina
            self._cond.wait() # la macchina va in sleep in attesa di un evento (da un ingresso)

            
    def input(self, name):
        return self._ios.get(name)       

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, **args):
        if 'inputname' in args and (self._cursens is None or args['inputname'] in self._cursens):
            self.logD("input " + repr(args['inputname']) +" is triggering " + self._curstatename + " - " + args['reason'])
            self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente
        if 'timername' in args:
            self.logD("timer " + repr(args['timername']) +" is triggering " + self._curstatename)
            self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente
        	   

    def commonEval(self):
        pass

    def commonExit(self):
        pass

    def commonEntry(self):
        pass

    def tmrSet(self, name, timeout):
        print timeout
        if not name in self._timers:
            self._timers[name] = fsmTimer(self, name)
        t = self._timers[name]
        self._tmgr.set(t, timeout)
        self.logD("activating a timer: '%s', %.2fs" % (name, timeout))
    
    def tmrExp(self, name):
        return not name in self._timers or self._timers[name].expd() 

################################################################################

# ESEMPIO DI UTILIZZO

    
    
                
class fsmTest(fsmBase):
    def __init__(self, name, **args):
        fsmBase.__init__(self, name, {
            'uno' : ['A'],
            'due' : ['A','B']
            }, **args
            )
        self.gotoState('uno')
    
    def uno_entry(self):
        self.logI("uno entry")
        self.tmrSet('t1',5)
        self.tmrSet('t2',7)
        

    def due_entry(self):
        self.logI("due entry")
            
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
    
        
            
            
