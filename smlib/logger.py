# -*- coding: utf-8 -*-
'''
Providing a way to easily log the behaviour of a fsm.

@date: March 26, 2018
@authors: Damiamo Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

import time
from datetime import datetime


class fsmLogger():
    '''Base class for fsm loggers.'''
    
    levstr = ['E', 'W', 'I', 'D']

    def __init__(self, lev=3) -> None:
        self._level = lev
        self.startime = time.time()

    def log(self, fsmname: str, lev: int, msg: str) -> None:
        tm = time.time() - self.startime
        if lev <= self._level:
            self.pushMsg('%8.2fs: %s - %s%s' % (tm, fsmLogger.levstr[lev], fsmname, msg))

    def pushMsg(self, msg: str) -> None:
        print(msg)

    def resetTime(self) -> None:
        self.startime = time.time()

    def changeLevel(self, newlevel: int) -> None:
        self._level = newlevel


class fsmFileLogger(fsmLogger):
    '''A class to log to file.'''

    def __init__(self, lev=3, directory="logs/", prefix="") -> None:
        super(fsmFileLogger, self).__init__(lev)
        self.files = {}
        self.dir = directory
        self.prefix = prefix

    def log(self, fsmname: str, lev: int, msg: str) -> None:
        '''Log a message to file.'''
        if lev <= self._level:
            if fsmname not in self.files.keys():
                self.files[fsmname] = open(self.dir+"/"+self.prefix+"."+fsmname+".log", 'a')
            tm = datetime.now()
            self.pushMsg(self.files[fsmname], '%s: %s - %s\n' % (str(tm), fsmLogger.levstr[lev], msg))

    def pushMsg(self, f, msg: str):
        '''Write a message to file.'''
        f.write(msg)
        f.flush()  # to empty buffer after every message!

    def __del__(self):
        '''Close all the open files.'''
        for name, f in self.files.items():
            if not f.closed:
                print("Closing "+name+"\n")
                f.close()

# TODO: add fsmSysLogger class
