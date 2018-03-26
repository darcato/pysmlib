# -*- coding: utf-8 -*-
'''
Input - Output objects for finite state machines.

@date: March 26, 2018
@authors: Davide Marcato, Damiamo Bortolato
@email: davide.marcato@lnl.infn.it - damiano.bortolato@lnl.infn.it
'''

import threading
import epics
import re
from collections import OrderedDict
import numpy as np

#classe che rappresenta un ingresso per le macchine a stati
class fsmIO(object):
    def __init__(self, name):
        self._name = name
        self._data = {}     #keep all infos arriving with change callback
        self._conn = False  #keeps all infos arriving with connection callback

        self._attached = set() # set che contiene le macchine a stati che utilizzano questo ingresso
        self._pv = epics.PV(name, callback=self.chgcb, connection_callback=self.concb, auto_monitor=True)
        self._cond = threading.Condition()

    def ioname(self):
        return self._name

    def attach(self, obj):
        self._attached.add(obj)
        
    def isAttached(self, obj):
        return obj in self._attached

    #obtain exclusive access on io
    def lock(self):
        self._cond.acquire()

    #release exclusive access on io
    def unlock(self):
        self._cond.release()
    
    #callback connessione - called on connections and disconnections
    def concb(self, **args):
        self.lock()
        self._conn = args.get('conn', False)
        self._data = {} #not to keep old values after disconnection
        self.trigger("conn", args)
        self.unlock()
    
    #callback aggiornamento - value has changed or initial value after connection has arrived
    def chgcb(self, **args):
        self.lock()
        self._data = args
        self.trigger("change", args)
        self.unlock()
    
    #put callback - pv processing has been completed after being triggered by a put
    def putcb(self, **args):
        if 'fsm' in args:
            args['fsm'].trigger(iobj=self, inputname=self._name, reason="putcomp")

    # "sveglia" le macchine a stati connesse a questo ingresso    
    def trigger(self, cbname, cbdata):
        for fsm in self._attached:
            fsm.trigger(iobj=self, inputname=self._name, reason=cbname, cbdata=cbdata)

    # caput and wait for pv processing to complete, then call putcb
    def put(self, value, caller_fsm):
        #cbdata contains the fsm obj to wake up when putCompleted 
        cbdata = { "fsm" : caller_fsm }
        try:
            self._pv.put(value, callback=self.putcb, use_complete=True, callback_data=cbdata)
        except Exception as e:
            caller_fsm.logE("FAILED putting to pv %s  -- exception: %s" % (self._name, str(e)))
            return False
        return True
            
    #whether the most recent put() has completed.
    def putComplete(self):
        return self._pv.put_complete

    #return pv data dictionary
    def data(self):
        return self._data

    # returns wheter the pv is connected or not
    def connected(self):
        return self._conn

#rappresenta una lista di oggetti input
class fsmIOs(object):

    def __init__(self):
        self._ios = {}
    
    def get(self, name, fsm, **args):
        #first time this input was requested: we create and attach it
        if name not in self._ios:
            self._ios[name] =  fsmIO(name)
            
        #input already created: if not already attached to the fsm, trigger some fake events to init fsm
        if not self._ios[name].isAttached(fsm):
            io = self._ios[name]
            io.lock()
            fsm.trigger(iobj=io, inputname=name, reason="conn", cbdata={'conn':io.connected(), 'pvname':name})
            if io.data():
                fsm.trigger(iobj=io, inputname=name, reason="change", cbdata=io.data())
            io.attach(fsm)
            io.unlock()
        
        fsm.logI("Connecting to PV: {:s}".format(name))
        return self._ios[name]
    
    def getFsmIO(self, fsm):
        ret = {}
        for io in self._ios.values():
            if io.isAttached(fsm):
                ret[io.ioname()] = io
        return ret
    
    def getAll(self):
        return self._ios.values()
        

#performs the conversion from procedure internal namings of the inputs
#and real pv names, base on naming convention and a map
class lnlPVs(fsmIOs):
    
    def __init__(self, mapFile):
        super(lnlPVs, self).__init__()
        #converts the internal name to the ending of the pv name
        
        file = open(mapFile, "r")
        lines = file.readlines()
        file.close()

        self._map = {}
        replaces = {} #a dict with macro substitutions
        pattern = OrderedDict()
        strgen = ""
        for line in lines:
            if not line.startswith("#"):
                line_uncomment = line.split("#")[0].strip()
                if line_uncomment.startswith(">"):
                    el = line_uncomment[1:].split("=")
                    if len(el)==2:
                        cmd = el[0].strip().replace("\"", "")
                        expression = el[1].strip().replace("\"", "")
                        if cmd == "pattern":  #keywords of the config file
                            pattern = OrderedDict()  #will contain the naming convention elements, with each its format
                            strgen = ""   #will contain the whole string formats
                            m = re.match(" *\((.*)\) *\((.*)\) *", expression)
                            if m:
                                strgen = m.group(1).strip().replace(" ","").replace("\"", "") #first part between {} = string definition
                                strelm = re.findall("[^{}]*{([^{}]*)}[^{}]*", strgen) #parse all the single parts
                                patterns = m.group(2).split(",") #second part between {} = naming convention elements
                                if not strelm or len(strelm)!=len(patterns):
                                    raise ValueError("inputMap ERROR, line {}: Failed to parse pattern elements".format(lines.index(line)))
                                for k in range(len(patterns)): 
                                    p = patterns[k].strip().replace(" ","").replace("\"", "")
                                    if p!="":
                                        if p not in pattern:
                                            pattern[p]=strelm[k]  #populate pattern
                                        else:
                                            raise ValueError("inputMap ERROR, line {}: Redeclaration of pattern element".format(lines.index(line)))
                                if len(pattern)==0:
                                    raise ValueError("inputMap ERROR, line {}: Pattern empty")
                            else:
                                raise ValueError("inputMap ERROR, line {}: Pattern syntax error".format(lines.index(line)))
                        else:  #macro definitions
                            replaces[el[0].strip().replace("\"", "").upper()] = el[1].strip().replace("\"", "")
                    elif len(el)>2:
                        raise ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                elif len(line_uncomment)>3:  #input definition
                    if len(pattern)!=0 and len(strgen)!=0:  #if a pattern has already been defined
                        el = line_uncomment.split("=")
                        if len(el)==2:  #if there is an assignation
                            key = el[0].strip().replace("\"", "")   #input name inside fsm
                            values = el[1].split(",")   #info to create pv name elements
                            if len(values)!=len(pattern):  #must respect the pattern
                                raise ValueError("inputMap ERROR, line {}: Pattern lenght differs from input declaration".format(lines.index(line)))
                            cmap = OrderedDict() #map of this input: for each element of pattern there is a value
                            for k in range(len(pattern)):
                                candidate = values[k].strip().replace("\"", "") #parse from file
                                m = re.match(" *\$\((.*)\) *", candidate)  #$(MACRO)
                                if m:  #if this is a macro to be replaced
                                    candidate = m.group(1)  #get the macro name
                                    if candidate.upper() in replaces: #if there is a replacement for the macro in replaces
                                        candidate = replaces[candidate.upper()]  #use the replacement
                                    else:
                                        raise ValueError("inputMap ERROR, line {}: Cannot find macro substitutions for: {}".format(lines.index(line), candidate))
                                cmap[pattern.items()[k]]=candidate   #the map of this input has a tuple as key (pattern, strelm) and the parsed candidate as value
                            self._map[key] = (cmap, strgen) #add the current map (of this input) and the whole strgen to the general map (all inputs)
                        else:
                            ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                    else:
                        raise ValueError("inputMap ERROR, line {}: Declaring an input without first defining a pattern!".format(lines.index(line)))
            
        #inverse map, to perform back naming transformation
        #self.inv_map = {v: k for k, v in self._map.iteritems()}

    #call parent method to connect pvs with complete names
    #reads from calling fsm the targets and creates base pv name with those infos
    def get(self, name, fsm, **args):
        cmap, strgen = self._map[name]

        substitutions = ()  # a tuple containing the parts of pv name in order
        cstrgen = strgen # copy the string containing the format of each part
        for pattern, v in cmap.iteritems():
            m = re.match(" *<(.*)> *", v)   #these are parameters to be passed runtime
            if m:
                v = m.group(1)
                if v in args and args[v]!=None:
                    v = args[v] #get the value from args
                else:
                    raise ValueError("Cannot find the arg: %s in the input creation, as required by input map" % v)
            key, keydef = pattern
            if keydef.endswith("d"):  #if we are dealing with an int value, let's format it now and then use it as a string
                if v!="":             #this is done so that if we get a number as string doesn't crash
                    v = ("{"+keydef+"}").format(int(v))  #now the number is a string with the correct format
                cstrgen = cstrgen.replace(keydef, ":s", 1)  #so we change the expected format to %s (replace the first occurence, going from first to last)
            elif keydef==":c":          #this is a char, let's convert it to a string of lenght 1
                v = ("{:.1s}").format(str(v))
                cstrgen = cstrgen.replace(keydef, ":s", 1)
            substitutions+= (v,)   #add the updated v to the tuple pv name parts 

        pvname = cstrgen.format(*substitutions)  #actually compose pv name
        return super(lnlPVs, self).get(pvname, fsm, **args)

    ##return a dictionary with the orinal (before mapping) names of the ios and ios objs of one fsm
    #def getFsmIO(self, fsm):
    #    iosDict = super(lnlPVs, self).getFsmIO(fsm)
    #    pvsDict = {}
    #    for key, value in iosDict.iteritems():
    #        pvsDict[self.inv_map[key]] = value
    #    return iosDict


#an io which changes only between evaluation of the fsm, due to progressive effect of the event queque
#it reflects the changes of an fsmIO, one change per cycle
#it implements flags to detect changes, edges, connections and disconnections
#there should be a mirror of the same fsmIO for each fsm, in order to use flags indipendently 
class mirrorIO(object):
    def __init__(self, fsm, io):
        self._fsm = fsm
        
        self._name = None
        self._value = None  #pv value
        self._pval = None   #pv previous value
        self._currcb = None #current callback
        self._putComplete = True  #keep track of put completement

        self._reflectedIO = io    #the io to mirror here
        self._name = io.ioname()
        self._conn = False  #pv connected or not
        self._data = {}  #whole pv data
        self.setBufSize(0)

    def setBufSize(self, s):
        if s == 0:
             self._avbuf = None        
        else:
            self._avbuf = np.array([0.0]*s)

    def update(self, reason, cbdata):
        if reason=='change':
            self._currcb = reason
            self._data = cbdata
            self._pval = self._value
            self._value = self._data.get('value', None)
            if self._value is not None and self._avbuf is not None:
                self._avbuf = np.roll(self._avbuf,1)
                self._avbuf[0] = self._value

        elif reason=='conn':
            self._currcb = reason
            self._conn = cbdata.get('conn', False)
            #on connection or disconnection reset all previous values of the input
            #in order not to access old values after disconnections
            self._pval = None
            self._value = None
            self._data = {}

        #if a put complete callback arrives, the flag must be set true only if
        #the callback was called due to a put made by this object
        elif reason=='putcomp':
            self._currcb = reason
            self._putComplete = True
        else:
            self._currcb = ""  #a callback which does not modify this input (eg: putcb for other io)
            
    def reset(self):
        self._currcb = ""

    def ioname(self):
        return self._name
    
    #make a put, specifying the object making the put
    def put(self, value):
        self._putComplete = False
        return self._reflectedIO.put(value, self._fsm)
    
    #----- METHODS THAT CATCH CHANGEMENT ONLY if CHECKED WHEN TRIGGERED BY THE SAME CHANGEMENT ------
    #----- They return True if the fsm was woken up by this changement in this cycle
    
    # hasPutCompleted: current awakening callback is a put callback
    def hasPutCompleted(self):
        return self._currcb == 'putcomp'       
    
    # Rising = connected and received at least 2 values, with the last > precedent
    def rising(self):
        return self._currcb == 'change' and self._pval!=None and self._value > self._pval

    # Falling = connected and received at least 2 values, with the last < precedent
    def falling(self):
        return self._currcb == 'change' and self._pval!=None and self._value < self._pval

    # hasChanged = last callback was a change callback
    def hasChanged(self):
        return self._currcb == 'change'

    # hasDisconnected = last callback was a connection callback due to disconnection
    def hasDisconnected(self):
        return self._currcb == 'conn' and not self._conn
    
    # hasConnected = last callback was a connection callback due to connection
    def hasConnected(self):
        return self._currcb == 'conn' and self._conn
    
    # hasFirstValue: the input has changed and this is the first value it got
    def hasFirstValue(self):
        return self._currcb == 'change' and self._pval==None
    
    #------METHODS THAT KEEP VAlUE BETWEEN TRIGGERS------
    
    #returns wheter the pv processing after the last put has been completed
    def putComplete(self):
        return self._putComplete
    
    # return whether the pv is connected and has received the initial value
    def initialized(self):
        return self._conn and self._value!=None

    # returns wheter the pv is connected or not
    def connected(self):
        return self._conn

    # return the pv value
    def val(self):
        return self._value

    def valAvg(self):
        return self._value if self._avbuf is None else self._avbuf.mean()

    def valStd(self):
        return self._value if self._avbuf is None else self._avbuf.std()

    def valTrend(self):
        if self._avbuf is None:
            return 0
        s = self._avbuf.std()
        d = self._avbuf[0] - self._avbuf[-1] 
        if d > s:
            return 1
        if d < -s:
            return -1
        return 0

    # return the pv previuos value
    def pval(self):
        return self._pval

    # return one element from pv data, choosen by key
    def data(self, key):
        return self._data.get(key, None)