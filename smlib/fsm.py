# -*- coding: utf-8 -*-
'''
The base class of a fsm, which handles stream of execution and provides
user interface to access all the functionalities of io, timers, logger etc.

@date: September 15, 2016
@authors: Damiamo Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

import threading
from .timer import fsmTimers, fsmTimer
from .io import fsmIOs, fsmIO
from .logger import fsmLogger


class fsmBase(threading.Thread):
    '''
    Base class for a finite state machine running in a separate thread
    The user must implement FSM states as methods of the class.
    '''

    def __init__(self, name:str, **args) -> None:
        super(fsmBase, self).__init__(name=name)
        self._name = name
        if 'tmgr' not in args:
            self._tmgr = fsmTimers()
            self._tmgr.start()
        else:
            self._tmgr = args['tmgr']
            if not self._tmgr.is_alive():
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
        self._mirrors = {}  # a dict to keep the mirrorIOs of this fsm, with keys the fsmIO
        self._awaker = None  # WHAT FOR FIRST RUN??
        self._awakerType = ""
        self._awakerReason = ""
        self._watchdog = None

    # populate the sensityvity list for each state
    def setSensLists(self, statesWithIos: dict) -> None:
        # statesWithIos e un dizionario in cui la chiave e il nome dello stato e
        # il valore un array di ingressi utilizzati dallo stato
        for state, iolist in statesWithIos.items():
            iodict = {}
            for io in iolist:
                iodict[io.ioname()] = io
            self._senslists[state] = iodict

    def fsmname(self) -> str:
        '''Return the name of this fsm'''
        return self._name

    def lock(self) -> None:
        '''Get exclusive access to this object'''
        self._cond.acquire()

    def unlock(self) -> None:
        '''Release exclusive access to this object'''
        self._cond.release()

    def gotoState(self, state: str) -> None:
        '''Change state to be executed at the next event'''
        self.logD('going to state -> %s' % state)
        if self._nextstate != self._curstate:
            self.logI('gotoState() called twice, ignoring subsequent calls')
            return
        if self._curstatename == state:
            return
        self._nextstatename = state
        # metodo eval del prossimo stato
        self._nextstate = getattr(self, '%s_eval' % state)
        # metodo entry del prossimo stato
        self._nextentry = getattr(self, '%s_entry' % state, None)
        # metodo exit del prossimo stato
        self._nextexit = getattr(self, '%s_exit' % state, None)

    def gotoPrevState(self) -> None:
        '''Go back to the previous state'''
        if self._prevstatename:
            self.gotoState(self._prevstatename)

    def log(self, lev: int, msg: str) -> None:
        '''Base method to log a message to the default logger'''
        #whites = len(max(self._senslists.keys(), key=len)) - len(self._curstatename)
        self._logger.log(self._name, lev, '[%15s] : %s' % (self._curstatename, msg))

    def logE(self, msg: str) -> None:
        '''Log an error message'''
        self.log(0, msg)

    def logW(self, msg: str) -> None:
        '''Log a warning message'''
        self.log(1, msg)

    def logI(self, msg: str) -> None:
        '''Log an info message'''
        self.log(2, msg)

    def logD(self, msg: str) -> None:
        '''Log a debug message'''
        self.log(3, msg)

    def logTimeReset(self) -> None:
        self._logger.resetTime()

    def eval(self) -> bool:
        '''Execute the current state'''
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
                self.logD('executing %s_entry()' % (self._curstatename))
                self._nextentry()
        self.commonEval()
        self.logD('executing %s_eval()' % (self._curstatename))
        self._curstate()
        self.logD('end of %s_eval()' % (self._curstatename))
        if self._nextstate != self._curstate:
            changed = True
            if self._curexit:
                self.logD('executing %s_exit()' % (self._curstatename))
                self._curexit()
            self.commonExit()
        return changed

    def eval_forever(self) -> None:
        '''Main loop of the FSM'''
        while not self._stop_thread:
            changed = self.eval()  # eval viene eseguito senza lock
            self.lock()  # blocca la coda degli eventi
            if not changed and len(self._events) == 0:
                self.logD("No events to process going to sleep\n")
                self._cond.wait()  # la macchina va in sleep in attesa di un evento (da un IO, timer...)
                self.logD('awoken')
            self._process_one_event()  # PROCESS ONLY IF RETURN TRUE?
            self.unlock()

    def connect(self, name: str, **args) -> fsmIO:
        '''Create and connect to an fsmIO'''
        thisFsmIO = self._ios.get(name, self, **args)
        if not thisFsmIO in self._mirrors:
            self._mirrors[thisFsmIO] = fsmIO(self, thisFsmIO)

        return self._mirrors[thisFsmIO]

    def run(self) -> None:
        '''Execute the FSM thread'''
        self.eval_forever()

    def kill(self) -> None:
        '''Stop the FSM thread'''
        self._cond.acquire()
        self._stop_thread = True
        self._cond.notify()
        self._cond.release()
        self.join()

    def trigger(self, **args) -> None:
        '''Enqueue an event to be processed by the FSM'''
        self._cond.acquire()
#        self.logD("pushing event %s %d" %(repr(args), len(self._events)+1))
        self._events.append(args)  # append here also the shapshot of all ios
        if len(self._events) == 1:
            self._cond.notify()
        self._cond.release()

    def _process_one_event(self) -> bool:
        '''Process one event from the queue'''
        if self._awaker and self._awakerType == 'io':
            # reset io to catch changes only on the eval triggered by the same change
            self._awaker.reset()
        self.resetAwaker()
        if len(self._events):
            return self._process_event(**self._events.pop(0))
        return False

    def _process_event(self, **args) -> bool:
        '''Apply the updates carried by the event'''
        self.logD('Consuming event n° %d' % (len(self._events)))
        if 'inputname' in args:
            self.logD("input " + repr(args['inputname']) +
                      " is triggering " + self._curstatename +
                      " - " + args['reason'])
            fsmIOobj = args['iobj']
            mirrorIOobj = self._mirrors.get(fsmIOobj, None)
            if mirrorIOobj:
                mirrorIOobj.update(args.get('reason', ""), args.get('cbdata', None))
                self.setAwaker(mirrorIOobj, 'io', args.get('reason', "unknownInput"))
                return True
        elif 'timername' in args:
            self.logD("timer " + repr(args['timername']) + " is triggering " + self._curstatename)
            self.setAwaker(args['tmrobj'], 'tmr', args.get('reason', "unknownTimer"))
            return True
        return False

    def commonEval(self):
        pass

    def commonExit(self):
        pass

    def commonEntry(self):
        pass

    def tmrSet(self, name: str, timeout: float, reset=True) -> None:
        '''Set a timer with a given timeout in seconds'''
        if not name in self._timers:
            self._timers[name] = fsmTimer(self, name)
        t = self._timers[name]
        self._tmgr.set(t, timeout, reset)
        self.logD("activating a timer: '%s', %.2fs" % (name, timeout))

    def tmrExpired(self, name: str) -> bool:
        '''Check if a timer has expired or does not exist'''
        return not name in self._timers or self._timers[name].expd()

    def tmrExpiring(self, name: str) -> bool:
        '''The current event is caused by the expiration of a this timer'''
        return name in self._timers \
            and self._awakerType == 'tmr' \
            and self._awakerReason == "expired" \
            and self._awaker is self._timers[name]

    def isIoConnected(self) -> bool:
        '''Check if all the IOs are connected'''
        stateios = self._cursens if self._cursens is not None else self._mirrors.values()
        return self.allof(stateios.values(), "connected")

    def isIoInitialized(self) -> bool:
        '''Check if all the IOs are initialized'''
        stateios = self._cursens if self._cursens is not None else self._mirrors.values()
        return self.allof(stateios.values(), "initialized")

    def anyof(self, objs: list, method: str) -> bool:
        '''Check if any of the IOs is in a given state'''
        return any(getattr(io, method)() for io in objs)

    def allof(self, objs: list, method: str) -> bool:
        '''Check if all the IOs are in a given state'''
        return all(getattr(io, method)() for io in objs)

    def whoWokeMe(self) -> tuple:
        '''Return the object that woke up the FSM'''
        return (self._awaker, self._awakerType)

    def whyWokeMe(self) -> str:
        '''Return the reason that woke up the FSM'''
        return self._awakerReason

    def setAwaker(self, obj: object, objType: str, reason: str) -> None:
        '''Set the object that woke up the FSM'''
        self._awaker = obj
        self._awakerType = str(objType)
        self._awakerReason = str(reason)

    def resetAwaker(self) -> None:
        '''Reset the object that woke up the FSM'''
        self._awaker = None
        self._awakerType = ""
        self._awakerReason = ""

    def setWatchdogInput(self, inp: fsmIO, mode="on-off", interval=1) -> None:
        if isinstance(inp, fsmIO) and mode in ["off", "on", "on-off"]:
            self._watchdog = (inp, mode, interval)
        else:
            raise ValueError("Unrecognized input type or mode")

    def getWatchdogInput(self) -> fsmIO:
        return self._watchdog
