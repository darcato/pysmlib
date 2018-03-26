# -*- coding: utf-8 -*-
'''
Providing a way to easily log the behaviour of a fsm.

@date: March 26, 2018
@authors: Damiamo Bortolato, Davide Marcato 
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

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

    def changeLevel(self, newlevel):
        self._level = newlevel

class fsmFileLogger(fsmLogger):
    def __init__(self, lev=3, directory="logs/", prefix=""):
        super(fsmFileLogger, self).__init__(lev)
        self.files = {}
        self.dir = directory
        self.prefix = prefix
    
    def log(self, fsmname, lev, msg):
        if lev <= self._level:
            if fsmname not in self.files.iterkeys():
                self.files[fsmname] = open(self.dir+"/"+self.prefix+"."+fsmname+".log", 'a')
            tm = datetime.now()
            self.pushMsg(self.files[fsmname], '%s: %s - %s\n' %(str(tm), fsmLogger.levstr[lev], msg))

    def pushMsg(self, f, msg):
        f.write(msg)
        f.flush()  #to empty buffer after every message!
        
    def __del__(self):
        for name, f in self.files.iteritems():
            if not f.closed:
                print("Closing "+name+"\n")
                f.close()

#TODO: add fsmSysLogger class