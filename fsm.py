# -*- coding: utf-8 -*-
'''
Created on 15 set 2016

@author: damiano
'''


import epics
import threading
import time
from datetime import datetime

class fsmLogger(object):
    levstr = ['E','W','I','D']
    def __init__(self, lev=3):
        self._level = lev
        self.startime = time.time()
        
    def log(self, fsmname, lev, msg):
    	tm = time.time() - self.startime
        if lev <= self._level:
            self.pushMsg('%8.2fs: %s - %s%s' %(tm, fsmLogger.levstr[lev], fsmname, msg))
            
    def pushMsg(self, msg):
        print msg

    def resetTime(self):
        self.startime = time.time()

class fsmLoggerToFile(fsmLogger):
    def __init__(self, lev=3, directory="logs/"):
        super(fsmLoggerToFile, self).__init__(lev)
        self.files = {}
        self.dir = directory
    
    def log(self, fsmname, lev, msg):
        if lev <= self._level:
            if fsmname not in self.files.iterkeys():
                self.files[fsmname] = open(self.dir+fsmname+".log", 'a')
            tm = datetime.now()
            self.pushMsg(self.files[fsmname], '%s: %s - %s\n' %(str(tm), fsmLogger.levstr[lev], msg))

    def pushMsg(self, f, msg):
        f.write(msg)
        
    def __exit__(self, exc_type, exc_value, traceback):
        for f in self.files.iteritems():
            f.close()


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
        self._fsm.trigger(timername=self._name)
        
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
        self._stop_thread = False
        
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
        while not self._stop_thread:
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
            # se il timer è già in lista significa che è stato reimpostato prima che scadesse, 
            # quindi lo rimuovo e lo reimposto
            if timer in self._timers:
                self._timers.remove(timer)
            
            # imposta il tempo al quale scadrà il timer
            timer.reset(timeout)

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
            self.logE(repr(e))        
        finally:
            self._cond.release()

    def kill(self):
        self._cond.acquire()
        self._stop_thread = True
        self._cond.notify()
        self._cond.release()
        self.join()

    
#classe che rappresenta un ingresso per le macchine a stati
class fsmIO(object):
    def __init__(self, name):
        self._name = name
        self._conn = False #pv connessa
        self._value = None
        self._data = {}    # pv data
        self._attached = set() # set che contiene le macchine a stati che utilizzano questo ingresso
        self._pv = epics.PV(name, callback=self.chgcb, connection_callback=self.concb, auto_monitor=True)
        self._pval = None
        self._flgRising = False
        self._flgFalling = False
        self._flgChanged = False
    
    def ioname(self):
        return self._name

    def attach(self, obj):
        self._attached.add(obj)
    
    #callback connessione - called on connections and disconnections
    def concb(self, **args):
        self._conn = args.get('conn', False)
        self.trigger(reason="connectionCallback")
        #on connection or disconnection reset all previous values of the input
        #in order not to access old values after disconnections
        self._flgRising = False
        self._flgFalling = False
        self._flgChanged = False
        self._pval = None
        self._value = None
        self._data = {}
    
    #callback aggiornamento - value has changed or initial value after connection has arrived
    def chgcb(self, **args):
        self._data = args
        self._pval = self._value
        self._flgRising = True
        self._flgFalling = True
        self._flgChanged = True
        self._value=args.get('value', None)
        self.trigger(reason="changeCallback")
    
    #put callback - pv processing has been completed after being triggered by a put
    def putcb(self, **args):
        self.trigger(reason="putCallback")

    # "sveglia" le macchine a stati connesse a questo ingresso    
    def trigger(self, **args):
        for o in self._attached:
            o.trigger(inputname=self._name, reason=args['reason'])

    # caput and wait for pv processing to complete, then call putcb
    def put(self, value):
    	self._pv.put(value, callback=self.putcb, use_complete=True)

    #returns wheter the pv processing after a put has been completed
    def putComplete(self):
    	return self._pv.put_complete
        
    # returns wheter the input is connected and rising since last asked
    def rising(self):
       	if self._flgRising and self._pval < self._value and self._pval!=None:
       		self._flgRising = False
        	return True
    	else: 
    		return False

    # returns wheter the input is connected and falling since last asked
    def falling(self):
        if self._flgFalling and self._pval > self._value:
        	self._flgFalling = False
        	return True
    	else:
    		return False

    # returns wheter the input is connected and has changed its value since last asked
    def hasChanged(self):
        if self._flgChanged:
            self._flgChanged = False
            return True
        else:
            return False

    # return whether the pv is connected and has received the initial value
    def initialized(self):
        return self._conn and self._value!=None

    # returns wheter the pv is connected or not
    def connected(self):
        return self._conn

    # return the pv value
    def val(self):
        return self._value

    # return one element from pv data, choosen by key
    def data(self, key):
        if key in self._data.keys():
            return self._data[key]
        else:
            return None

#rappresenta una lista di oggetti input
class fsmIOs(object):

    def __init__(self):
        self._ios = {}
    
    def get(self, name, fsm, **args):
        if name not in self._ios:
            self._ios[name] =  fsmIO(name)
        self._ios[name].attach(fsm)
        return self._ios[name]
    
    def getFsmIO(self, fsm):
    	ret = {}
    	for io in self._ios.values():
    		if fsm in io._attached:
    			ret[io.ioname()] = io
    	return ret

#performs the conversion from procedure internal namings of the inputs
#and real pv names, base on naming convention and a map
class cavityPVs(fsmIOs):
    
    def __init__(self):
        super(cavityPVs, self).__init__()
        #converts the internal name to the ending of the pv name
        obj = "Qwrs"
        subapp = "Cryo"
        self._map = {
            "zeroEn"         : [subapp, obj, ":", "zeroEn"],         #enable zeroFreq fsm
            "caraterizeEn"   : [subapp, obj, ":", "crtzEn"],         #enable caraterize fsm
            "waveEn"         : [subapp, obj, ":", "waveEn"],         #enable wave fsm
            "pulseEn"        : [subapp, obj, ":", "pulsEn"],         #enable pulse fsm
            "softTunerEn"    : [subapp, obj, ":", "swtuEn"],         #enable softTuner fsm
            "freqErr"        : [subapp, obj, ":", "freqEr"],         #freq err reading
            "freqMode"       : [subapp, obj, ":", "fesc"],           #choose to read Hz or kHz
            "freqTrgFast"    : [subapp, obj, "_", "fscn.PROC"],      #trigger a fast freqErr reading
            "freqTrgSlow"    : [subapp, obj, "_", "sscn.PROC"],      #trigger a slow freqErr reading
            "freqScanFast"   : [subapp, obj, "_", "fscn.SCAN"],      #the scan field of the fast freq reading
            "freqScanSlow"   : [subapp, obj, "_", "sscn.SCAN"],      #the scan field of the slow freq reading
#
            "tuneDMOV"       : [subapp, "Tune", ":", "motr.DMOV"],   #done moving flag
            "tuneRBV"        : [subapp, "Tune", ":", "motr.RBV"],    #current motor position
            "tuneMoveRel"    : [subapp, "Tune", ":", "mrel"],        #move relative with backlash correction
            "tuneHLS"        : [subapp, "Tune", ":", "motr.HLS"],    #high limit switch
            "tuneLLS"        : [subapp, "Tune", ":", "motr.LLS"],    #low limit switch
            "tuneStepFast"   : [subapp, "Tune", ":", "stfaSt"],      #how many steps when fast mode
            "tuneStepSlow"   : [subapp, "Tune", ":", "stslSt"],      #how many steps when slow mode
            "tuneStepMedium" : [subapp, "Tune", ":", "stmdSt"],      #how many steps when medium mode
            "tuneVelo"       : [subapp, "Tune", ":", "motr.VELO"],   #motor velocity
            "tuneAccl"       : [subapp, "Tune", ":", "motr.ACCL"],   #motor acceleration
            "tuneBacl"       : [subapp, "Tune", ":", "motr.BACL"],   #motor backlash acceleration
            "tuneTWF"        : [subapp, "Tune", ":", "motr.TWF"],    #move a step forward
            "tuneTWR"        : [subapp, "Tune", ":", "motr.TWR"],    #move a step back
            "tuneTWV"        : [subapp, "Tune", ":", "motr.TWV"],    #current step value inside record motor
            "tuneStepMode"   : [subapp, "Tune", ":", "fstmSt"],      #select fast, medium or slow step mode
            "tuneMaxVelo"    : [subapp, "Tune", ":", "motr.VMAX"],   #motor maximum velocity
            "tuneBaseVelo"   : [subapp, "Tune", ":", "motr.VBAS"],   #motor minimum velocity 
            "tuneHomeVelo"   : [subapp, "Tune", ":", "motr.HVEL"],   #motor homing velocity 
            "tuneDir"        : [subapp, "Tune", ":", "motr.DIR"],    #motor direction bit
#
            "coupDMOV"       : [subapp, "Coup", ":", "motr.DMOV"],   #done moving flag
            "coupRBV"        : [subapp, "Coup", ":", "motr.RBV"],    #current motor position
            "coupMoveRel"    : [subapp, "Coup", ":", "mrel"],        #move relative with backlash correction
            "coupHLS"        : [subapp, "Coup", ":", "motr.HLS"],    #high limit switch
            "coupLLS"        : [subapp, "Coup", ":", "motr.LLS"],    #low limit switch
            "coupStepFast"   : [subapp, "Coup", ":", "stfaSt"],      #how many steps when fast mode
            "coupStepSlow"   : [subapp, "Coup", ":", "stslSt"],      #how many steps when slow mode
            "coupStepMedium" : [subapp, "Coup", ":", "stmdSt"],      #how many steps when medium mode
            "coupVelo"       : [subapp, "Coup", ":", "motr.VELO"],   #motor velocity
            "coupAccl"       : [subapp, "Coup", ":", "motr.ACCL"],   #motor acceleration
            "coupBacl"       : [subapp, "Coup", ":", "motr.BACL"],   #motor backlash acceleration
            "coupTWF"        : [subapp, "Coup", ":", "motr.TWF"],    #move a step forward
            "coupTWR"        : [subapp, "Coup", ":", "motr.TWR"],    #move a step back
            "coupTWV"        : [subapp, "Coup", ":", "motr.TWV"],    #current step value inside record motor
            "coupStepMode"   : [subapp, "Coup", ":", "fstmSt"],      #select fast, medium or slow step mode
            "coupMaxVelo"    : [subapp, "Coup", ":", "motr.VMAX"],   #motor maximum velocity
            "coupBaseVelo"   : [subapp, "Coup", ":", "motr.VBAS"],   #motor minimum velocity 
            "coupHomeVelo"   : [subapp, "Coup", ":", "motr.HVEL"],   #motor homing velocity 
            "coupDir"        : [subapp, "Coup", ":", "motr.DIR"],    #motor direction bit
#
            "pressure"       : [subapp, obj, ":", "presRd"],         #cryostate pressure readings
            "steps"          : [subapp, obj, ":", "clst"],           #an array for live position visualization
            "freqs"          : [subapp, obj, ":", "clfr"],           #an array for live freqErr visualization
            "press"          : [subapp, obj, ":", "clpr"],           #an array for live pressure visualization
            "fit_steps"      : [subapp, obj, ":", "cfst"],           #an array to show the position linear fit
            "fit_freqs"      : [subapp, obj, ":", "cffr"],           #an array to show the freqErr linear fit
            "fit_press"      : [subapp, obj, ":", "cfpr"],           #an array to show the pressure linear fit
            "quip"           : [subapp, obj, ":", "quipSt"],         #quiescent power settings
            "lopwEn"         : [subapp, obj, ":", "pwenSt"],         #loop power enable
            "period"         : [subapp, obj, ":", "wprdSt"],         #period for the periodic fsms
            "dutyCycle"      : [subapp, obj, ":", "wdtcSt"],         #dutycycle for the period fsms
            "maxPower"       : [subapp, obj, ":", "wmxpSt"],         #max accepted average power in cavity
            "minPower"       : [subapp, obj, ":", "wmnpSt"],         #minimun power to start self-excited loop
            "shape"          : [subapp, obj, ":", "wshpSt"],         #to choose the kind of wave to do
            "timeResolution" : [subapp, obj, ":", "wtirSt"],         #how much to approssimate waves steps
            "powers"         : [subapp, obj, ":", "wlpo"],           #an array to show choosen wave (y)
            "powers.NELM"    : [subapp, obj, ":", "wlpo.NELM"],      #full array lenght of powers and times
            "times"          : [subapp, obj, ":", "wlti"],           #an array to show choosen wave (x)
            "phasErr"        : [subapp, obj, ":", "phasEr"],         #phase error readings
            "stGain"         : [subapp, obj, ":", "stgaSt"],         #soft tuner gain
            "stThreshold"    : [subapp, obj, ":", "stthSt"],         #soft tuner threshold
            "tuningPolarity" : [subapp, obj, ":", "tupoSt"],         #tuning polarity (sign)
            "cavityStatus"   : [subapp, obj, ":", "stat"],           #cavity status
            "waveAvgPow"     : [subapp, obj, ":", "wavg"],           #to report average wave power
            "carAvgSmpl"     : [subapp, obj, ":", "cavgSt"],         #samples to be averaged each step
            "carTop"         : [subapp, obj, ":", "ctopSt"],         #max Hz, then come back
            "cConnWatchdog"  : [subapp, obj, ":", "cconWd"],         #to set caraterize watchdog         
            "pConnWatchdog"  : [subapp, obj, ":", "pconWd"],         #to set pulse watchdog
            "sConnWatchdog"  : [subapp, obj, ":", "sconWd"],         #to set softTuner watchdog
            "zConnWatchdog"  : [subapp, obj, ":", "zconWd"],         #to set zeroFreq watchdog
            "wConnWatchdog"  : [subapp, obj, ":", "wconWd"]          #to set wave watchdog
        }
        #inverse map, to perform back naming transformation
        #self.inv_map = {v: k for k, v in self._map.iteritems()}

    #call parent method to connect pvs with complete names
    #reads from calling fsm the targets and creates base pv name with those infos
    def get(self, name, fsm, **args):
        pvname = "PaLlrf%.4s%02d_%.4s%02d%c%s" % (self._map[name][0], args['cry'], self._map[name][1], args['cav'], self._map[name][2], self._map[name][3])
        return super(cavityPVs, self).get(pvname, fsm, **args)

    ##return a dictionary with the orinal (before mapping) names of the ios and ios objs of one fsm
    #def getFsmIO(self, fsm):
    #    iosDict = super(cavityPVs, self).getFsmIO(fsm)
    #    pvsDict = {}
    #    for key, value in iosDict.iteritems():
    #        pvsDict[self.inv_map[key]] = value
    #    return iosDict


# classe base per la macchina a stati
class fsmBase(object):
    def __init__(self, name, **args):
        self._name = name
        if not 'tmgr' in args:
            self._tmgr = fsmTimers()
            self._tmgr.start()
        else:
            self._tmgr = args['tmgr']
            if not self._tmgr.isAlive():
                self._tmgr.start()
                
        self._timers = {}
        self._ios = args.get('ios', fsmIOs())
        self._logger = args.get('logger', fsmLogger())
        self._curstatename = 'undefined'
        self._nextstatename = 'undefined'
        self._prevstatename = 'undefined'
        self._curstate = None
        self._curexit = None
        self._nextstate = None
        self._nextentry = None
        self._nextexit = None
        self._senslists = {}
        self._cursens = {}
        self._cond = threading.Condition()
    	self._myios = self._ios.getFsmIO(self)
        self._stop_thread = False
        self._events = []

    #populate the sensityvity list for each state
    def setSensLists(self, statesWithIos):
        # statesWithIos e un dizionario in cui la chiave e il nome dello stato e
        # il valore un array di ingressi utilizzati dallo stato
        for state, iolist in statesWithIos.iteritems():
            iodict = {}
            for io in iolist:
                iodict[io.ioname()] = io
            self._senslists[state] = iodict

    #return the name of the class
    def fsmname(self):
        return self._name

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
        #whites = len(max(self._senslists.keys(), key=len)) - len(self._curstatename)
        self._logger.log(self._name, lev, '[%15s] : %s' %(self._curstatename, msg))    

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
        changed = False
        if self._nextstate != self._curstate:
            self.logD('%s => %s' % (self._curstatename, self._nextstatename))
            self._prevstatename = self._curstatename
            self._curstatename = self._nextstatename
            self._curstate = self._nextstate
            self._curexit = self._nextexit
            self._cursens = self._senslists.get(self._nextstatename, {})
            self.commonEntry()
            if self._nextentry:
                self.logD('executing %s_entry()' %(self._curstatename))
                self._nextentry()
        self.commonEval()
        self.logD('executing %s_eval()' %(self._curstatename))
        self._curstate()
        self.logD('end of %s_eval()' %(self._curstatename))
        if self._nextstate != self._curstate:
            changed = True
            if self._curexit:
                self.logD('executing %s_exit()' %(self._curstatename))
                self._curexit()
            self.commonExit()
        return changed
    
    # valuta all'infinito la macchina a stati
    def eval_forever(self):
        while(not self._stop_thread):
            changed = self.eval() # eval viene eseguito senza lock
            self.lock() # blocca la coda degli eventi
            if not changed and len(self._events) == 0:
                self.logD("No events to process going to sleep\n")
                self._cond.wait() # la macchina va in sleep in attesa di un evento (da un IO, timer...)
                self.logD('awoken')
            self._process_one_event()
            self.unlock()

            
    def input(self, name, **args):
        return self._ios.get(name, self, **args)

    def kill(self):
        self._cond.acquire()
        self._stop_thread = True
        self._cond.notify()
        self._cond.release()

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, **args):
        self._cond.acquire()
        self.logD("pushing event %s %d" %(repr(args), len(self._events)+1))
        self._events.append(args)
        if len(self._events) == 1:
            self._cond.notify()
        self._cond.release()

    def _process_one_event(self):
        if len(self._events):
            return self._process_event(**self._events.pop(0))
        return False

    def _process_event(self, **args):
        self.logD('Consuming event %s %d' % (repr(args), len(self._events)))
        if 'inputname' in args and (self._cursens is None or args['inputname'] in self._cursens):
            self.logD("input " + repr(args['inputname']) +" is triggering " + self._curstatename + " - " + args['reason'])
            #self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente
            return True
        if 'timername' in args:
            self.logD("timer " + repr(args['timername']) +" is triggering " + self._curstatename)
            #self._cond.notify() #sveglia la macchina solo se quell'ingresso e' nella sensitivity list dello stato corrente
            return True
        return False

    def commonEval(self):
        pass

    def commonExit(self):
        pass

    def commonEntry(self):
        pass

    def tmrSet(self, name, timeout):
        if not name in self._timers:
            self._timers[name] = fsmTimer(self, name)
        t = self._timers[name]
        self._tmgr.set(t, timeout)
        self.logD("activating a timer: '%s', %.2fs" % (name, timeout))
    
    def tmrExp(self, name):
        return not name in self._timers or self._timers[name].expd()

    def is_io_connected(self):
        stateios = self._cursens if self._cursens is not None else self._myios
        return self.allof(stateios.values(), "connected")

    def anyof(self, objs, method):
        return any(getattr(io, method)() for io in objs)     

    def allof(self, objs, method):
        return all(getattr(io, method)() for io in objs)     

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
    
        
            
            
