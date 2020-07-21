# -*- coding: utf-8 -*-
'''
Input - Output objects for finite state machines.

@date: March 26, 2018
@authors: Damiano Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

import re
from collections import OrderedDict, deque
from statistics import mean, stdev
from math import sqrt
from datetime import datetime
import threading
import epics


# class representing an IO with epics support for a finite state machine
class epicsIO(object):
    def __init__(self, name):
        self._name = name
        self._data = {}  # keep all infos arriving with change callback
        self._conn = False  # keeps all infos arriving with connection callback

        self._attached = set()  # set of finite state machines using this IO
        self._pv = epics.PV(name, callback=self.chgcb, connection_callback=self.concb, auto_monitor=True)
        self._cond = threading.Condition()

    def ioname(self):
        return self._name

    def attach(self, obj):
        self._attached.add(obj)

    def isAttached(self, obj):
        return obj in self._attached

    # obtain exclusive access on io
    def lock(self):
        self._cond.acquire()

    # release exclusive access on io
    def unlock(self):
        self._cond.release()

    # callback connessione - called on connections and disconnections
    def concb(self, **args):
        self.lock()
        self._conn = args.get('conn', False)
        self._data = {}  # not to keep old values after disconnection
        self.trigger("conn", args)
        self.unlock()

    # callback aggiornamento - value has changed or initial value after connection has arrived
    def chgcb(self, **args):
        self.lock()
        self._data = args
        self.trigger("change", args)
        self.unlock()

    # put callback - pv processing has been completed after being triggered by a put
    def putcb(self, **args):
        if 'fsm' in args:
            args['fsm'].trigger(iobj=self, inputname=self._name, reason="putcomp")

    # "sveglia" le macchine a stati connesse a questo ingresso
    def trigger(self, cbname, cbdata):
        for fsm in self._attached:
            fsm.trigger(iobj=self, inputname=self._name, reason=cbname, cbdata=cbdata)

    # caput and wait for pv processing to complete, then call putcb
    def put(self, value, caller_fsm):
        # cbdata contains the fsm obj to wake up when putCompleted
        cbdata = {"fsm": caller_fsm}
        try:
            self._pv.put(value, callback=self.putcb, use_complete=True, callback_data=cbdata)
        except Exception as e:
            caller_fsm.logE("FAILED putting to pv %s  -- exception: %s" % (self._name, str(e)))
            return False
        return True

    # whether the most recent put() has completed.
    def putComplete(self):
        return self._pv.put_complete

    # return pv data dictionary
    def data(self):
        return self._data

    # returns wheter the pv is connected or not
    def connected(self):
        return self._conn


# rappresenta una lista di oggetti input
class fsmIOs(object):
    def __init__(self):
        self._ios = {}

    def get(self, name, fsm, **args):
        # first time this input was requested: we create and attach it
        if name not in self._ios:
            self._ios[name] = epicsIO(name)

        # input already created: if not already attached to the fsm, trigger some fake events to init fsm
        if not self._ios[name].isAttached(fsm):
            io = self._ios[name]
            io.lock()
            fsm.trigger(iobj=io, inputname=name, reason="conn", cbdata={'conn': io.connected(), 'pvname': name})
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


# performs the conversion from procedure internal namings of the inputs
# and real pv names, base on naming convention and a map
class mappedIOs(fsmIOs):
    def __init__(self, mapFile):
        super(mappedIOs, self).__init__()
        # converts the internal name to the ending of the pv name

        file = open(mapFile, "r")
        lines = file.readlines()
        file.close()

        self._map = {}
        replaces = {}  # a dict with macro substitutions
        pattern = OrderedDict()
        strgen = ""
        for line in lines:
            if not line.startswith("#"):
                line_uncomment = line.split("#")[0].strip()
                if line_uncomment.startswith(">"):
                    el = line_uncomment[1:].split("=")
                    if len(el) == 2:
                        cmd = el[0].strip().replace("\"", "")
                        expression = el[1].strip().replace("\"", "")
                        if cmd == "pattern":  # keywords of the config file
                            pattern = OrderedDict()  # will contain the naming convention elements, with each its format
                            strgen = ""  # will contain the whole string formats
                            m = re.match(r" *\((.*)\) *\((.*)\) *", expression)
                            if m:
                                strgen = m.group(1).strip().replace(" ", "").replace("\"", "")  # first part between {} = string definition
                                strelm = re.findall(r"[^{}]*{([^{}]*)}[^{}]*", strgen)  # parse all the single parts
                                patterns = m.group(2).split(",")  # second part between {} = naming convention elements
                                if not strelm or len(strelm) != len(patterns):
                                    raise ValueError("inputMap ERROR, line {}: Failed to parse pattern elements".format(lines.index(line)))
                                for k, kpattern in enumerate(patterns):
                                    p = kpattern.strip().replace(" ", "").replace("\"", "")
                                    if p != "":
                                        if p not in pattern:
                                            pattern[p] = strelm[k]  # populate pattern
                                        else:
                                            raise ValueError("inputMap ERROR, line {}: Redeclaration of pattern element".format(lines.index(line)))
                                if len(pattern) == 0:
                                    raise ValueError("inputMap ERROR, line {}: Pattern empty")
                            else:
                                raise ValueError("inputMap ERROR, line {}: Pattern syntax error".format(lines.index(line)))
                        else:  # macro definitions
                            replaces[el[0].strip().replace("\"", "").upper()] = el[1].strip().replace("\"", "")
                    elif len(el) > 2:
                        raise ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                elif len(line_uncomment) > 3:  # input definition
                    if len(pattern) != 0 and len(strgen) != 0:  # if a pattern has already been defined
                        el = line_uncomment.split("=")
                        if len(el) == 2:  # if there is an assignation
                            key = el[0].strip().replace("\"", "")  # input name inside fsm
                            values = el[1].split(",")  # info to create pv name elements
                            if len(values) != len(pattern):  # must respect the pattern
                                raise ValueError("inputMap ERROR, line {}: Pattern lenght differs from input declaration".format(lines.index(line)))
                            cmap = OrderedDict()  # map of this input: for each element of pattern there is a value
                            for k in range(len(pattern)):
                                candidate = values[k].strip().replace("\"", "")  # parse from file
                                m = re.match(r" *\$\((.*)\) *", candidate)  # $(MACRO)
                                if m:  # if this is a macro to be replaced
                                    candidate = m.group(1)  # get the macro name
                                    if candidate.upper() in replaces:  # if there is a replacement for the macro in replaces
                                        candidate = replaces[candidate.upper()]  # use the replacement
                                    else:
                                        raise ValueError("inputMap ERROR, line {}: Cannot find macro substitutions for: {}".format(lines.index(line), candidate))
                                cmap[pattern.items()[k]] = candidate  # the map of this input has a tuple as key (pattern, strelm) and the parsed candidate as value
                            self._map[key] = (cmap, strgen)  # add the current map (of this input) and the whole strgen to the general map (all inputs)
                        else:
                            ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                    else:
                        raise ValueError("inputMap ERROR, line {}: Declaring an input without first defining a pattern!".format(lines.index(line)))

        # inverse map, to perform back naming transformation
        #self.inv_map = {v: k for k, v in self._map.items()}

    # call parent method to connect pvs with complete names
    # reads from calling fsm the targets and creates base pv name with those infos
    def get(self, name, fsm, **args):
        cmap, strgen = self._map[name]

        substitutions = ()  # a tuple containing the parts of pv name in order
        cstrgen = strgen  # copy the string containing the format of each part
        for pattern, v in cmap.items():
            m = re.match(r" *<(.*)> *", v)  # these are parameters to be passed runtime
            if m:
                v = m.group(1)
                if v in args and args[v] is not None:
                    v = args[v]  # get the value from args
                else:
                    raise ValueError("Cannot find the arg: %s in the input creation, as required by input map" % v)
            keydef = pattern[1]
            if keydef.endswith("d"):  # if we are dealing with an int value, let's format it now and then use it as a string
                if v != "":  # this is done so that if we get a number as string doesn't crash
                    v = ("{"+keydef+"}").format(int(v))  # now the number is a string with the correct format
                cstrgen = cstrgen.replace(keydef, ":s", 1)  # so we change the expected format to %s (replace the first occurence, going from first to last)
            elif keydef == ":c":  # this is a char, let's convert it to a string of lenght 1
                v = ("{:.1s}").format(str(v))
                cstrgen = cstrgen.replace(keydef, ":s", 1)
            substitutions += (v,)  # add the updated v to the tuple pv name parts

        pvname = cstrgen.format(*substitutions)  # actually compose pv name
        return super(mappedIOs, self).get(pvname, fsm, **args)

    # return a dictionary with the orinal (before mapping) names of the ios and ios objs of one fsm
    # def getFsmIO(self, fsm):
    #    iosDict = super(lnlPVs, self).getFsmIO(fsm)
    #    pvsDict = {}
    #    for key, value in iosDict.iteritems():
    #        pvsDict[self.inv_map[key]] = value
    #    return iosDict


# an io which changes only between evaluation of the fsm, due to progressive effect of the event queque
# it reflects the changes of an fsmIO, one change per cycle
# it implements flags to detect changes, edges, connections and disconnections
# there should be a mirror of the same fsmIO for each fsm, in order to use flags indipendently
class fsmIO(object):
    def __init__(self, fsm, io):
        self._fsm = fsm

        self._name = None
        self._value = None  # pv value
        self._sevr = None
        self._pval = None  # pv previous value
        self._psevr = None
        self._timestamp = 0  # value timestamp
        self._currcb = None  # current callback
        self._putComplete = True  # keep track of put completement

        self._reflectedIO = io  # the io to mirror here
        self._name = io.ioname()
        self._conn = False  # pv connected or not
        self._data = {}  # whole pv data
        self.setBufSize(0)

    def setBufSize(self, s):
        if s == 0:
            self._cbufVal = None
            self._cbufTime = None
        elif self._cbufVal is not None:
            # new buffer with old data and new maxlen
            self._cbufVal = deque(self._cbufVal, maxlen=s)
            self._cbufTime = deque(self._cbufTime, maxlen=s)
        else:
            self._cbufVal = deque(maxlen=s)
            self._cbufTime = deque(maxlen=s)

    def update(self, reason, cbdata):
        if reason == 'change':
            self._currcb = reason
            self._data = cbdata
            self._pval = self._value
            self._psevr = self._sevr
            ptime = self._timestamp
            self._value = self._data.get('value', None)
            self._sevr = self._data.get('severity', None)
            self._timestamp = self._data.get('timestamp', 0)
            if self._value is not None and self._cbufVal is not None:
                self._cbufVal.append(self._value)
                # delta in seconds [float] -> microsecond precision
                # how much previous value lasted
                self._cbufTime.append(self._timestamp-ptime)

        elif reason == 'conn':
            self._currcb = reason
            self._conn = cbdata.get('conn', False)
            # on connection or disconnection reset all previous values of the input
            # in order not to access old values after disconnections
            self._pval = None
            self._psevr = None
            self._value = None
            self._sevr = None
            self._data = {}

        # if a put complete callback arrives, the flag must be set true only if
        # the callback was called due to a put made by this object
        elif reason == 'putcomp':
            self._currcb = reason
            self._putComplete = True
        else:
            self._currcb = ""  # a callback which does not modify this input (eg: putcb for other io)

    def reset(self):
        self._currcb = ""

    def ioname(self):
        return self._name

    # make a put, specifying the object making the put
    def put(self, value):
        self._putComplete = False
        return self._reflectedIO.put(value, self._fsm)

    # ----- METHODS THAT CATCH CHANGE ONLY if CHECKED WHEN TRIGGERED BY THE SAME CHANGE ------
    # ----- They return True if the fsm was woken up by this change in this cycle

    # putCompleting: current awakening callback is a put callback
    def putCompleting(self):
        return self._currcb == 'putcomp'

    # Rising = connected and received at least 2 values, with the last > precedent
    def rising(self):
        return self._currcb == 'change' and self._pval is not None and self._value > self._pval

    # Falling = connected and received at least 2 values, with the last < precedent
    def falling(self):
        return self._currcb == 'change' and self._pval is not None and self._value < self._pval

    # Alarm Increasing = last alarm > precedent (in absolute value)
    def alarm_increasing(self):
        return self._currcb == 'change' and self._psevr is not None and abs(self._sevr) > abs(self._psevr)

    # Alarm Decreasing = last alarm < precedent (in absolute value)
    def alarm_decreasing(self):
        return self._currcb == 'change' and self._psevr is not None and abs(self._sevr) < abs(self._psevr)

    # Alarm changing = change callback and the alarm status != precedent
    def alarm_changing(self):
        return self._currcb == 'change' and self._psevr is not None and self._sevr != self._psevr

    # changing = last callback was a change callback
    def changing(self):
        return self._currcb == 'change'

    # disconnecting = last callback was a connection callback due to disconnection
    def disconnecting(self):
        return self._currcb == 'conn' and not self._conn

    # connecting = last callback was a connection callback due to connection
    def connecting(self):
        return self._currcb == 'conn' and self._conn

    # initializing: the input has changed and this is the first value it got
    def initializing(self):
        return self._currcb == 'change' and self._pval is None

    # ------METHODS THAT KEEP VAlUE BETWEEN TRIGGERS------

    # returns whether the pv processing after the last put has been completed
    def putComplete(self):
        return self._putComplete

    # return whether the pv is connected and has received the initial value
    def initialized(self):
        return self._conn and self._value is not None

    # returns whether the pv is connected or not
    def connected(self):
        return self._conn

    # returns whether the pv is in alarm or not
    def alarm(self):
        return self._sevr
    
    # returns whether the pv is in alarm or not
    def alarm_name(self, short=False):
        alarm_levels = {-2: "UNDER THRESHOLD MAJOR ALARM", 
                        -1: "UNDER THRESHOLD MINOR ALARM", 
                         0: "NO ALARM",
                         1: "OVER THRESHOLD MINOR ALARM", 
                         2: "OVER THRESHOLD MAJOR ALARM"}
        if short:
            alarm_levels = {k: " ".join(v.split(' ')[-2:]) for k, v in alarm_levels.items()}
        return alarm_levels[self._sevr]

    # return the pv value
    def val(self):
        return self._value

    # return the average values in the circular buffer
    def valAvg(self, timeWeight=False):
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return self._value

        if timeWeight:
            times = list(self._cbufTime)[1:].append(datetime.now().timestamp()-self._timestamp)
            vt = [v * t for v, t in zip(self._cbufVal, times)]
            return sum(vt)/sum(times)

        return mean(self._cbufVal)

    # return the sample standard deviation of the circular buffer
    def valStd(self, timeWeight=False):
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return 0

        # https://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Weighted_sample_variance
        # https://www.itl.nist.gov/div898/software/dataplot/refman2/ch2/weightsd.pdf
        if timeWeight:
            m = self.valAvg(timeWeight=True)
            times = list(self._cbufTime)[1:].append(datetime.now().timestamp()-self._timestamp)
            wdiff = [t*((v-m)*(v-m)) for v, t in zip(self._cbufVal, times)]
            n = len(times)
            return sqrt(sum(wdiff)/((n-1)*sum(times)/n))

        return stdev(self._cbufVal)

    # return the trend [0 = flat, 1 = increasing, -1 = decreasing]
    def valTrend(self, k=1):
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return 0
        s = stdev(self._cbufVal)
        d = self._cbufVal[-1] - self._cbufVal[0]
        if d > k*s:
            return 1
        if d < -k*s:
            return -1
        return 0

    # return the pv previuos value
    def pval(self):
        return self._pval

    # return the last timestamp
    def time(self):
        return datetime.fromtimestamp(self._timestamp)

    # return one element from pv data, choosen by key
    def data(self, key):
        return self._data.get(key, None)
