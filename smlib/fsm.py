# -*- coding: utf-8 -*-
'''
The base class of a fsm, which handles stream of execution and provides
user interface to access all the functionalities of io, timers, logger etc.

@date: September 15, 2016
@authors: Damiamo Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

from .timer import fsmTimers, fsmTimer
from .io import fsmIOs, mirrorIO
from .logger import fsmLogger
import threading

# base class for a finite state machine running in a separate thread
class fsmBase(threading.Thread):
    def __init__(self, name, **args):
        super(fsmBase, self).__init__(name=name)
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
        self._mirrors = {} #a dict to keep the mirrorIOs of this fsm, with keys the fsmIO
        self._awaker = None                #WHAT FOR FIRST RUN??
        self._awakerType = ""
        self._awakerReason = ""
        self._watchdog = None

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
        self.logD('going to state -> %s' % state)
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
            self._process_one_event()   #PROCESS ONLY IF RETURN TRUE?
            self.unlock()

            
    def input(self, name, **args):
        thisFsmIO = self._ios.get(name, self, **args)
        if not thisFsmIO in self._mirrors:
            self._mirrors[thisFsmIO]= mirrorIO(self, thisFsmIO)
        
        return self._mirrors[thisFsmIO]

    def run(self):
        #self._killRequested = False
        #while not self._killRequested:
        #try:
        self.eval_forever()
        #except Exception, e:
        #    print(repr(e))
        #    print("\nERROR: fsm %s crashed unexpectedly.\n" % self.fsm.fsmname())
            #sleep(5)    #should RESET fsm status before restarting.. or boot loop!

    def kill(self):
        self._cond.acquire()
        self._stop_thread = True
        self._cond.notify()
        self._cond.release()
        self.join()

    #chiamata dagli ingressi quando arrivano eventi
    def trigger(self, **args):
        self._cond.acquire()
#        self.logD("pushing event %s %d" %(repr(args), len(self._events)+1))
        self._events.append(args)  #append here also the shapshot of all ios
        if len(self._events) == 1:
            self._cond.notify()
        self._cond.release()

    def _process_one_event(self):
        if self._awaker and self._awakerType == 'io':
            self._awaker.reset()   #reset io to catch changements only on the eval triggered by the same changement
        self.resetAwaker()
        if len(self._events):
            return self._process_event(**self._events.pop(0))
        return False

    def _process_event(self, **args):
        self.logD('Consuming event n° %d' % (len(self._events)))
        if 'inputname' in args:
            self.logD("input " + repr(args['inputname']) +" is triggering " + self._curstatename + " - " + args['reason'])
            fsmIOobj = args['iobj']
            mirrorIOobj = self._mirrors.get(fsmIOobj, None)
            if mirrorIOobj:
                mirrorIOobj.update(args.get('reason', ""), args.get('cbdata', None))
                self.setAwaker(mirrorIOobj, 'io', args.get('reason', "unknownInput"))
                return True
        elif 'timername' in args:
            self.logD("timer " + repr(args['timername']) +" is triggering " + self._curstatename)
            self.setAwaker(args['tmrobj'], 'tmr', args.get('reason', "unknownTimer"))
            return True
        return False

    def commonEval(self):
        pass

    def commonExit(self):
        pass

    def commonEntry(self):
        pass

    def tmrSet(self, name, timeout, reset=True):
        if not name in self._timers:
            self._timers[name] = fsmTimer(self, name)
        t = self._timers[name]
        self._tmgr.set(t, timeout, reset)
        self.logD("activating a timer: '%s', %.2fs" % (name, timeout))
    
    def tmrExp(self, name):
        return not name in self._timers or self._timers[name].expd()

    def is_io_connected(self):
        stateios = self._cursens if self._cursens is not None else self._mirrors.itervalues()
        return self.allof(stateios.values(), "connected")

    def anyof(self, objs, method):
        return any(getattr(io, method)() for io in objs)

    def allof(self, objs, method):
        return all(getattr(io, method)() for io in objs)

    def whoWokeMe(self):
        return (self._awaker, self._awakerType)
    
    def whyWokeMe(self):
        return self._awakerReason
    
    def setAwaker(self, obj, type, reason):
        self._awaker = obj
        self._awakerType = str(type)
        self._awakerReason = str(reason)
        
    def resetAwaker(self):
        self._awaker = None
        self._awakerType = ""
        self._awakerReason = ""

    def setWatchdogInput(self, inp, mode="on-off", interval=1):
        if isinstance(inp, mirrorIO) and mode in ["off", "on", "on-off"]:
            self._watchdog = (inp, mode, interval)
        else:
            raise ValueError("Unrecognized input type or mode")

    def getWatchdogInput(self):
        return self._watchdog

